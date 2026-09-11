import os
import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.db.session import get_db
from src.auth.dependencies import get_tenant_or_demo_context
from src.auth.schemas import TenantContext
from src.db.models import (
    JobOpening, JobMatchScore, CandidateAssessment,
    TechnicalInterview, PipelineStage, Candidate, Audit
)
from src.services.jd_service import JobDescriptionService
from src.services.assessment_service import (
    AssessmentService, get_exam_tracks_meta, get_question_modalities, EXAM_TRACKS
)
from src.services.copilot_service import RecruiterCopilotService
from src.services.comparison_service import CandidateComparisonService
from src.services.pipeline_service import PipelineService, ALLOWED_STAGES
from src.services.analytics_service import RecruitmentAnalyticsEngine
from src.services.sandbox_service import SandboxService
from src.services.proctoring_service import ProctoringService, ProctorTelemetryPayload, ProctorCheckResult

logger = logging.getLogger("auditagent.platform_router")

router = APIRouter(prefix="/api/v1", tags=["Enterprise Platform"])

def build_assessment_invite_url(
    assessment_id: uuid.UUID,
    access_token: str,
    request: Optional[Request] = None,
    override_base: Optional[str] = None
) -> str:
    """Builds a fully-qualified link for the assessment using custom domain, APP_BASE_URL, or request origin."""
    base = (override_base or "").strip().rstrip("/")
    if not base:
        app_env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
        if app_env_base and "mycompany.com" not in app_env_base:
            base = app_env_base
        elif request:
            base = str(request.base_url).rstrip("/")
        else:
            base = app_env_base or "http://localhost:8000"
    path = f"/assessment.html?id={assessment_id}&token={access_token}"
    return f"{base}{path}" if base else path

# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------

class JobCreateRequest(BaseModel):
    title: str = Field(..., examples=["Senior Backend Engineer"])
    department: str = Field(default="Engineering", examples=["Platform"])
    raw_jd_text: str = Field(..., examples=["We are looking for a Senior Python engineer with 5+ years experience, FastAPI, PostgreSQL, Docker, and distributed systems."])
    min_years_experience: Optional[int] = 3

class AssessmentGenerateRequest(BaseModel):
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    duration_minutes: int = Field(default=30, examples=[30])  # 10, 20, 30, 60
    custom_domain: Optional[str] = Field(default=None, description="Optional custom public domain/base URL (e.g. https://careers.mycompany.com)")


class AssessmentSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(..., examples=[{"q1": "We use SELECT FOR UPDATE...", "q2": "CREATE INDEX CONCURRENTLY..."}])

class CandidateVerifyOtpRequest(BaseModel):
    otp_or_token: str = Field(..., examples=["123456"])

class ProctorHeartbeatRequest(BaseModel):
    snapshot_base64: Optional[str] = None
    audio_level_rms: Optional[float] = 0.0
    audio_peak_hz: Optional[float] = None
    token: Optional[str] = None

class ProctorViolationRequest(BaseModel):
    event_type: str = Field(..., examples=["copy_paste_attempt", "tab_blur", "fullscreen_exit"])
    details: Optional[str] = None
    snapshot_base64: Optional[str] = None
    token: Optional[str] = None

class SandboxRunRequest(BaseModel):
    question_id: str = Field(..., examples=["q1_algo"])
    language: str = Field(default="python", examples=["python", "javascript", "go", "java"])
    code: str = Field(..., examples=["def solution(requests, limit, window_size):\n    return 4"])
    token: Optional[str] = None

class CandidateSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(..., examples=[{"q1_algo": "def solution(...)"}])
    token: Optional[str] = None

class InterviewStartRequest(BaseModel):
    candidate_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None

class InterviewRespondRequest(BaseModel):
    candidate_answer: str = Field(..., examples=["In our caching layer, we implemented Write-Through caching with Redis Sentinel..."])

class CompareRequest(BaseModel):
    candidate_ids: List[uuid.UUID]
    job_id: Optional[uuid.UUID] = None

class CopilotChatRequest(BaseModel):
    query: str = Field(..., examples=["Who is our strongest Python engineer for the Platform team?"])
    history: Optional[List[Dict[str, str]]] = None

class PipelineTransitionRequest(BaseModel):
    candidate_id: uuid.UUID
    new_stage: str = Field(..., examples=["shortlist"])
    notes: Optional[str] = None


# -------------------------------------------------------------
# 1. Job Openings & Matching Endpoints
# -------------------------------------------------------------

@router.post("/jobs")
async def create_job_opening(
    req: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Creates a new job opening and extracts structured intelligence from the JD."""
    jd_svc = JobDescriptionService(db, tenant.organization_id)
    job = await jd_svc.create_job_from_text(
        title=req.title,
        department=req.department,
        raw_jd_text=req.raw_jd_text,
        min_years=req.min_years_experience
    )
    return {
        "id": str(job.id),
        "title": job.title,
        "department": job.department,
        "required_skills": job.required_skills,
        "preferred_skills": job.preferred_skills,
        "min_years_experience": job.experience_min_years,
        "status": job.status
    }

@router.get("/jobs")
async def list_job_openings(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Lists all active job openings for the organization."""
    stmt = (
        select(JobOpening)
        .where(JobOpening.organization_id == tenant.organization_id)
        .order_by(desc(JobOpening.created_at))
    )
    res = await db.execute(stmt)
    jobs = res.scalars().all()
    return [
        {
            "id": str(j.id),
            "title": j.title,
            "department": j.department,
            "required_skills": j.required_skills,
            "preferred_skills": j.preferred_skills,
            "min_years_experience": j.experience_min_years,
            "status": j.status,
            "created_at": j.created_at.isoformat()
        }
        for j in jobs
    ]

@router.get("/candidates")
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Lists candidates and their latest audit scores for the organization."""
    stmt = (
        select(Candidate)
        .where(Candidate.organization_id == tenant.organization_id)
        .order_by(desc(Candidate.created_at))
    )
    res = await db.execute(stmt)
    candidates = res.scalars().all()
    results = []
    for c in candidates:
        audit_stmt = (
            select(Audit)
            .where(Audit.candidate_id == c.id)
            .order_by(desc(Audit.created_at))
            .limit(1)
        )
        audit_res = await db.execute(audit_stmt)
        latest_audit = audit_res.scalar_one_or_none()
        results.append({
            "id": str(c.id),
            "name": c.name,
            "email": c.email,
            "github_username": c.github_username,
            "tags": c.tags or [],
            "latest_audit_id": str(latest_audit.id) if latest_audit else None,
            "overall_score": latest_audit.overall_score if latest_audit else None,
            "recommendation": latest_audit.ai_recommendation if latest_audit else None
        })
    return results

@router.post("/jobs/{job_id}/match/{candidate_id}")
async def match_candidate_to_job(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Evaluates candidate-to-job match matrix, calculating required/preferred/experience match percentages."""
    jd_svc = JobDescriptionService(db, tenant.organization_id)
    try:
        match_score = await jd_svc.match_candidate_to_job(job_id=job_id, candidate_id=candidate_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": str(match_score.id),
        "job_id": str(match_score.job_id),
        "candidate_id": str(match_score.candidate_id),
        "match_score": match_score.overall_match_pct,
        "overall_match_pct": match_score.overall_match_pct,
        "fit_category": match_score.job_fit_recommendation,
        "job_fit_recommendation": match_score.job_fit_recommendation,
        "required_skills_match_pct": match_score.required_skills_match_pct,
        "preferred_skills_match_pct": match_score.preferred_skills_match_pct,
        "experience_match_pct": match_score.experience_match_pct,
        "matched_required_skills": match_score.matched_required_skills,
        "missing_required_skills": match_score.missing_required_skills,
        "matched_preferred_skills": match_score.matched_preferred_skills,
        "contradictions": match_score.contradictions,
        "summary": match_score.summary
    }

@router.get("/jobs/{job_id}/matches")
async def get_job_matches(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Gets all evaluated candidate matches for a job, ranked by overall match percentage."""
    stmt = (
        select(JobMatchScore, Candidate)
        .join(Candidate, JobMatchScore.candidate_id == Candidate.id)
        .where(JobMatchScore.job_id == job_id)
        .order_by(desc(JobMatchScore.overall_match_pct))
    )
    res = await db.execute(stmt)
    results = []
    for match, candidate in res.all():
        results.append({
            "id": str(match.id),
            "candidate_id": str(candidate.id),
            "candidate_name": candidate.name,
            "candidate_email": candidate.email,
            "match_score": match.overall_match_pct,
            "overall_match_pct": match.overall_match_pct,
            "fit_category": match.job_fit_recommendation,
            "fit_recommendation": match.job_fit_recommendation,
            "missing_skills": match.missing_required_skills,
            "summary": match.summary
        })
    return results


# -------------------------------------------------------------
# 2. Candidate Evidence Graph (DAG)
# -------------------------------------------------------------

@router.get("/evidence-graph/{audit_id}")
async def get_candidate_evidence_graph(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Returns interactive DAG node/edge visualization graph connecting claims to public GitHub code proofs."""
    graph_svc = CandidateEvidenceGraphService(db, tenant.organization_id)
    try:
        graph = await graph_svc.build_or_load_graph(audit_id)
        return graph
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------------------------------------------
# 3. Technical Assessments (10, 20, 30, 60m)
# -------------------------------------------------------------

# -------------------------------------------------------------
# 3. Technical Assessments (AI Proctored with Multi-Language Sandbox)
# -------------------------------------------------------------

@router.post("/assessments/generate")
async def generate_assessment(
    req: AssessmentGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Generates a customized technical problem set based on candidate resume and target job."""
    ass_svc = AssessmentService(db, tenant.organization_id)
    try:
        assessment = await ass_svc.generate_assessment(
            candidate_id=req.candidate_id,
            job_id=req.job_id,
            duration_minutes=req.duration_minutes
        )
        invite_url = build_assessment_invite_url(
            assessment.id, assessment.access_token, request=request, override_base=req.custom_domain
        )
        return {
            "id": str(assessment.id),
            "candidate_id": str(assessment.candidate_id),
            "duration_minutes": assessment.duration_minutes,
            "status": assessment.status,
            "questions": assessment.questions_json,
            "problem_set": assessment.questions_json,
            "access_token": assessment.access_token,
            "otp_code": assessment.otp_code,
            "invite_url": invite_url,
            "strike_count": assessment.strike_count,
            "max_strikes": assessment.max_strikes,
            "integrity_score": assessment.integrity_score,
            "created_at": assessment.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/assessments/{assessment_id}/invite")
async def get_or_create_candidate_invite(
    assessment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Generates / retrieves secure magic link and 6-digit OTP for candidate."""
    stmt = select(CandidateAssessment).where(
        CandidateAssessment.id == assessment_id,
        CandidateAssessment.organization_id == tenant.organization_id
    )
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if not ass.access_token or not ass.otp_code:
        token, otp, expires_at = ProctoringService.generate_invite_credentials()
        ass.access_token = token
        ass.otp_code = otp
        ass.otp_expires_at = expires_at
        await db.commit()
        await db.refresh(ass)

    invite_url = build_assessment_invite_url(ass.id, ass.access_token, request=request)
    return {
        "assessment_id": str(ass.id),
        "candidate_id": str(ass.candidate_id),
        "invite_url": invite_url,
        "access_token": ass.access_token,
        "otp_code": ass.otp_code,
        "otp_expires_at": ass.otp_expires_at.isoformat() if ass.otp_expires_at else None,
        "status": ass.status
    }

@router.get("/assessments/demo/active-link")
async def get_active_demo_assessment_link(
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Returns the latest active assessment link or generates one for instant live testing."""
    stmt = select(CandidateAssessment).where(
        CandidateAssessment.organization_id == tenant.organization_id
    ).order_by(desc(CandidateAssessment.created_at)).limit(1)
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()

    if not ass or not ass.access_token:
        c_stmt = select(Candidate).where(Candidate.organization_id == tenant.organization_id).limit(1)
        c_res = await db.execute(c_stmt)
        cand = c_res.scalar_one_or_none()
        if not cand:
            cand = Candidate(
                organization_id=tenant.organization_id,
                name="Alice Engineer",
                email="alice.engineer@example.com",
                tags=["Python", "PostgreSQL", "Docker"]
            )
            db.add(cand)
            await db.commit()
            await db.refresh(cand)

        ass_svc = AssessmentService(db, tenant.organization_id)
        ass = await ass_svc.generate_assessment(candidate_id=cand.id, duration_minutes=30)

    invite_url = build_assessment_invite_url(ass.id, ass.access_token, request=request)
    return {
        "assessment_id": str(ass.id),
        "candidate_id": str(ass.candidate_id),
        "access_token": ass.access_token,
        "otp_code": ass.otp_code,
        "invite_url": invite_url
    }

@router.post("/assessments/{assessment_id}/verify-otp")
async def verify_candidate_otp(
    assessment_id: uuid.UUID,
    req: CandidateVerifyOtpRequest,
    db: AsyncSession = Depends(get_db)
):
    """Candidate portal authentication via 6-digit OTP or magic link token."""
    stmt = select(CandidateAssessment, Candidate).join(
        Candidate, CandidateAssessment.candidate_id == Candidate.id
    ).where(CandidateAssessment.id == assessment_id)
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    ass, cand = row

    if not ProctoringService.verify_credentials(ass, req.otp_or_token):
        raise HTTPException(status_code=401, detail="Invalid or expired OTP / Access Token.")

    # Activate assessment if pending
    if ass.status == "pending":
        ass.status = "in_progress"
        await db.commit()
        await db.refresh(ass)

    return {
        "verified": True,
        "assessment_id": str(ass.id),
        "candidate_name": cand.name,
        "candidate_email": cand.email,
        "duration_minutes": ass.duration_minutes,
        "status": ass.status,
        "strike_count": ass.strike_count,
        "max_strikes": ass.max_strikes,
        "token": ass.access_token
    }

@router.get("/assessments/tracks")
async def get_available_exam_tracks():
    """Returns metadata for all 20 role-specific exam tracks."""
    return {
        "tracks": get_exam_tracks_meta()
    }

@router.get("/assessments/modalities")
async def get_assessment_modalities():
    """Returns the 10 customizable question modalities available across exams."""
    return {
        "modalities": get_question_modalities()
    }

@router.get("/assessments/{assessment_id}/candidate-view")
async def get_candidate_assessment_view(
    assessment_id: uuid.UUID,
    token: Optional[str] = None,
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Candidate view for taking the assessment in the standalone portal."""
    stmt = select(CandidateAssessment, Candidate, JobOpening).join(
        Candidate, CandidateAssessment.candidate_id == Candidate.id
    ).outerjoin(
        JobOpening, CandidateAssessment.job_id == JobOpening.id
    ).where(CandidateAssessment.id == assessment_id)
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    ass, cand, job = row

    # Validate token if set
    if token and not ProctoringService.verify_credentials(ass, token):
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")

    # Select question source: role-specific override or saved assessment questions
    questions_source = ass.questions_json or []
    if role and role in EXAM_TRACKS:
        questions_source = [q.model_dump() for q in EXAM_TRACKS[role]["questions"]]
    elif not questions_source:
        questions_source = [q.model_dump() for q in EXAM_TRACKS["software_engineer"]["questions"]]

    # Filter out internal/hidden fields from questions
    sanitized_questions = []
    for q in questions_source:
        tc_sanitized = [
            {"input_data": tc.get("input_data"), "expected_output": tc.get("expected_output"), "description": tc.get("description"), "setup_sql": tc.get("setup_sql")}
            for tc in q.get("test_cases", [])
            if not tc.get("hidden", False)
        ]
        sanitized_questions.append({
            "id": q.get("id"),
            "type": q.get("type"),
            "section": q.get("section", "mcq"),
            "section_title": q.get("section_title", "Section 1: Multiple Choice Questions (MCQs)"),
            "title": q.get("title"),
            "prompt": q.get("prompt"),
            "options": q.get("options", []),
            "code_snippet": q.get("code_snippet"),
            "starter_code": q.get("starter_code", {}),
            "test_cases": tc_sanitized,
            "time_limit_minutes": q.get("time_limit_minutes", 10),
            "db_schema_setup": q.get("db_schema_setup")
        })

    job_title = job.title if job else "Technical Engineer"
    if role and role in EXAM_TRACKS:
        job_title = EXAM_TRACKS[role]["title"]

    return {
        "id": str(ass.id),
        "candidate_name": cand.name,
        "job_title": job_title,
        "role_track": role or "software_engineer",
        "duration_minutes": ass.duration_minutes,
        "status": ass.status,
        "strike_count": ass.strike_count,
        "max_strikes": ass.max_strikes,
        "integrity_score": ass.integrity_score,
        "disqualification_reason": ass.disqualification_reason,
        "questions": sanitized_questions,
        "sandbox_results": ass.sandbox_results or {}
    }

@router.post("/assessments/{assessment_id}/proctor/heartbeat")
async def proctor_heartbeat(
    assessment_id: uuid.UUID,
    req: ProctorHeartbeatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Processes candidate periodic webcam snapshot & audio volume telemetry."""
    stmt = select(CandidateAssessment).where(CandidateAssessment.id == assessment_id)
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if req.token and not ProctoringService.verify_credentials(ass, req.token):
        raise HTTPException(status_code=401, detail="Invalid access token.")

    payload = ProctorTelemetryPayload(
        snapshot_base64=req.snapshot_base64,
        audio_level_rms=req.audio_level_rms,
        audio_peak_hz=req.audio_peak_hz,
        event_type="periodic_heartbeat"
    )
    result = ProctoringService.evaluate_telemetry(ass, payload)
    await db.commit()
    await db.refresh(ass)
    return result.model_dump()

@router.post("/assessments/{assessment_id}/proctor/violation")
async def proctor_violation(
    assessment_id: uuid.UUID,
    req: ProctorViolationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Handles explicit client-side violations (copy/paste attempt, tab switch, fullscreen exit)."""
    stmt = select(CandidateAssessment).where(CandidateAssessment.id == assessment_id)
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if req.token and not ProctoringService.verify_credentials(ass, req.token):
        raise HTTPException(status_code=401, detail="Invalid access token.")

    payload = ProctorTelemetryPayload(
        snapshot_base64=req.snapshot_base64,
        event_type=req.event_type,
        details=req.details
    )
    result = ProctoringService.evaluate_telemetry(ass, payload)
    await db.commit()
    await db.refresh(ass)
    return result.model_dump()

@router.post("/assessments/{assessment_id}/sandbox/run")
async def run_sandbox_code(
    assessment_id: uuid.UUID,
    req: SandboxRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """Executes candidate code in isolated server-side sandbox against question test cases."""
    stmt = select(CandidateAssessment).where(CandidateAssessment.id == assessment_id)
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if req.token and not ProctoringService.verify_credentials(ass, req.token):
        raise HTTPException(status_code=401, detail="Invalid access token.")

    if ass.status == "integrity_disqualified":
        raise HTTPException(status_code=403, detail="Assessment has been terminated due to integrity violations.")

    # Find test cases for the target question
    test_cases = []
    for q in (ass.questions_json or []):
        if q.get("id") == req.question_id:
            test_cases = q.get("test_cases", [])
            break

    if not test_cases:
        for track_data in EXAM_TRACKS.values():
            for q_obj in track_data.get("questions", []):
                if q_obj.id == req.question_id:
                    test_cases = [tc if isinstance(tc, dict) else tc.model_dump() for tc in q_obj.test_cases]
                    break
            if test_cases:
                break

    run_res = SandboxService.execute_code(
        language=req.language,
        code=req.code,
        test_cases=test_cases
    )

    # Cache execution results
    results_map = dict(ass.sandbox_results or {})
    results_map[req.question_id] = run_res.model_dump()
    ass.sandbox_results = results_map
    await db.commit()

    return run_res.model_dump()

@router.post("/assessments/{assessment_id}/candidate-submit")
async def candidate_submit_assessment(
    assessment_id: uuid.UUID,
    req: CandidateSubmitRequest,
    db: AsyncSession = Depends(get_db)
):
    """Candidate finishes and submits all answers from the standalone portal."""
    stmt = select(CandidateAssessment).where(CandidateAssessment.id == assessment_id)
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found.")

    if req.token and not ProctoringService.verify_credentials(ass, req.token):
        raise HTTPException(status_code=401, detail="Invalid access token.")

    ass_svc = AssessmentService(db, ass.organization_id)
    graded = await ass_svc.evaluate_submission(ass.id, req.answers)
    return {
        "id": str(graded.id),
        "score": graded.score,
        "integrity_score": graded.integrity_score,
        "strike_count": graded.strike_count,
        "status": graded.status,
        "passed": (graded.score or 0) >= 70 and graded.status != "integrity_disqualified",
        "strengths": graded.strengths,
        "weaknesses": graded.weaknesses,
        "feedback": graded.feedback,
        "completed_at": graded.completed_at.isoformat() if graded.completed_at else None
    }

@router.post("/assessments/{assessment_id}/submit")
async def submit_assessment(
    assessment_id: uuid.UUID,
    req: AssessmentSubmitRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Grades submitted assessment answers with automated technical rubric (Recruiter API)."""
    ass_svc = AssessmentService(db, tenant.organization_id)
    try:
        graded = await ass_svc.evaluate_submission(assessment_id, req.answers)
        return {
            "id": str(graded.id),
            "score": graded.score,
            "status": graded.status,
            "passed": (graded.score or 0) >= 70,
            "strengths": graded.strengths,
            "weaknesses": graded.weaknesses,
            "feedback": graded.feedback,
            "feedback_summary": graded.feedback,
            "rubric_breakdown": graded.feedback,
            "completed_at": graded.completed_at.isoformat() if graded.completed_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/assessments/{assessment_id}")
async def get_assessment(
    assessment_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    stmt = select(CandidateAssessment).where(
        CandidateAssessment.id == assessment_id,
        CandidateAssessment.organization_id == tenant.organization_id
    )
    res = await db.execute(stmt)
    ass = res.scalar_one_or_none()
    if not ass:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    return {
        "id": str(ass.id),
        "candidate_id": str(ass.candidate_id),
        "job_id": str(ass.job_id) if ass.job_id else None,
        "duration_minutes": ass.duration_minutes,
        "status": ass.status,
        "questions": ass.questions_json,
        "answers": ass.answers_json,
        "score": ass.score,
        "strike_count": ass.strike_count,
        "max_strikes": ass.max_strikes,
        "integrity_score": ass.integrity_score,
        "disqualification_reason": ass.disqualification_reason,
        "access_token": ass.access_token,
        "otp_code": ass.otp_code,
        "invite_url": build_assessment_invite_url(ass.id, ass.access_token, request=request),
        "strengths": ass.strengths,
        "weaknesses": ass.weaknesses,
        "feedback": ass.feedback
    }

@router.get("/assessments/{assessment_id}/proctor/audit")
async def get_assessment_proctor_audit(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Recruiter audit report of proctoring violations, strikes, timeline, and snapshots."""
    stmt = select(CandidateAssessment, Candidate).join(
        Candidate, CandidateAssessment.candidate_id == Candidate.id
    ).where(
        CandidateAssessment.id == assessment_id,
        CandidateAssessment.organization_id == tenant.organization_id
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    ass, cand = row

    return {
        "assessment_id": str(ass.id),
        "candidate_id": str(cand.id),
        "candidate_name": cand.name,
        "candidate_email": cand.email,
        "status": ass.status,
        "technical_score": ass.score,
        "integrity_score": ass.integrity_score,
        "strike_count": ass.strike_count,
        "max_strikes": ass.max_strikes,
        "is_disqualified": ass.status == "integrity_disqualified",
        "disqualification_reason": ass.disqualification_reason,
        "proctoring_logs": ass.proctoring_logs or [],
        "snapshots": ass.snapshots_json or [],
        "sandbox_results": ass.sandbox_results or {},
        "created_at": ass.created_at.isoformat(),
        "completed_at": ass.completed_at.isoformat() if ass.completed_at else None
    }


# -------------------------------------------------------------
# 4. AI Technical Interviewer (Multi-Turn)
# -------------------------------------------------------------

@router.post("/interviews/start")
async def start_technical_interview(
    req: InterviewStartRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Starts multi-turn technical interview, formulating Turn 1 opening question grounded in candidate's code."""
    int_svc = TechnicalInterviewService(db, tenant.organization_id)
    try:
        interview = await int_svc.start_interview(candidate_id=req.candidate_id, job_id=req.job_id)
        current_q = interview.turns_json[0]["question"] if interview.turns_json else ""
        return {
            "id": str(interview.id),
            "candidate_id": str(interview.candidate_id),
            "status": interview.status,
            "current_turn": interview.current_turn,
            "question": current_q,
            "current_question": current_q,
            "turns": interview.turns_json
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/interviews/{interview_id}/respond")
async def respond_to_interview(
    interview_id: uuid.UUID,
    req: InterviewRespondRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Candidate submits response; AI evaluates and dynamically generates follow-up probe or conclusion."""
    int_svc = TechnicalInterviewService(db, tenant.organization_id)
    try:
        updated = await int_svc.submit_turn_answer(interview_id, req.candidate_answer)
        latest_turn = updated.turns_json[-1] if updated.turns_json else {}
        return {
            "id": str(updated.id),
            "status": updated.status,
            "current_turn": updated.current_turn,
            "feedback": latest_turn.get("feedback"),
            "next_followup": latest_turn.get("ai_followup"),
            "probing_question": latest_turn.get("ai_followup"),
            "next_question": latest_turn.get("ai_followup"),
            "technical_score": updated.technical_score,
            "strengths": updated.strengths,
            "weaknesses": updated.weaknesses,
            "areas_for_human_review": updated.areas_for_human_review,
            "summary": updated.summary
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/interviews/{interview_id}")
async def get_interview_transcript(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    stmt = select(TechnicalInterview).where(
        TechnicalInterview.id == interview_id,
        TechnicalInterview.organization_id == tenant.organization_id
    )
    res = await db.execute(stmt)
    inter = res.scalar_one_or_none()
    if not inter:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return {
        "id": str(inter.id),
        "candidate_id": str(inter.candidate_id),
        "status": inter.status,
        "current_turn": inter.current_turn,
        "technical_score": inter.technical_score,
        "turns": inter.turns_json,
        "strengths": inter.strengths,
        "weaknesses": inter.weaknesses,
        "areas_for_human_review": inter.areas_for_human_review,
        "summary": inter.summary
    }


# -------------------------------------------------------------
# 5. Candidate Comparison
# -------------------------------------------------------------

@router.post("/compare")
async def compare_candidates(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Side-by-side comparative radar and verdict recommendation for 2-5 candidates."""
    comp_svc = CandidateComparisonService(db, tenant.organization_id)
    try:
        res = await comp_svc.compare_candidates(req.candidate_ids, req.job_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------
# 6. Recruiter Copilot (Conversational Grounded RAG)
# -------------------------------------------------------------

@router.post("/copilot/chat")
async def copilot_chat(
    req: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Recruiter assistant answering queries grounded in candidate evidence and audit scores."""
    copilot_svc = RecruiterCopilotService(db, tenant.organization_id)
    res = await copilot_svc.chat(req.query, req.history)
    return res


# -------------------------------------------------------------
# 7. Recruitment Kanban Pipeline
# -------------------------------------------------------------

@router.get("/pipeline/board")
async def get_pipeline_board(
    job_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    pipe_svc = PipelineService(db, tenant.organization_id)
    board = await pipe_svc.get_pipeline_board(job_id)
    columns = [
        {"stage": k, "stage_name": k.replace("_", " ").title(), "candidate_count": len(v), "candidates": v}
        for k, v in board.items()
    ]
    return columns

@router.post("/pipeline/transition")
async def transition_candidate_stage(
    req: PipelineTransitionRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Moves a candidate to a new recruitment stage."""
    pipe_svc = PipelineService(db, tenant.organization_id)
    try:
        st = await pipe_svc.transition_stage(
            candidate_id=req.candidate_id,
            new_stage=req.new_stage,
            user_id=tenant.user_id,
            notes=req.notes
        )
        return {
            "status": "transitioned",
            "candidate_id": str(st.candidate_id),
            "new_stage": st.stage,
            "updated_at": st.updated_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------------------------------------
# 8. Recruitment Analytics Engine
# -------------------------------------------------------------

@router.get("/analytics")
async def get_recruitment_analytics(
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Returns funnel metrics, hours saved, cost savings, AI concordance, and verified skills."""
    analytics_svc = RecruitmentAnalyticsEngine(db, tenant.organization_id)
    res = await analytics_svc.get_dashboard_analytics()
    summary = res.get("summary", {})
    res["total_candidates_screened"] = summary.get("total_audited", 0)
    res["estimated_hours_saved"] = summary.get("hours_saved", 0.0)
    res["funnel_stages"] = res.get("stage_breakdown", {})
    return res

