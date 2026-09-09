import uuid
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
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
from src.services.evidence_graph_service import CandidateEvidenceGraphService
from src.services.assessment_service import AssessmentService
from src.services.interview_service import TechnicalInterviewService
from src.services.copilot_service import RecruiterCopilotService
from src.services.comparison_service import CandidateComparisonService
from src.services.pipeline_service import PipelineService, ALLOWED_STAGES
from src.services.analytics_service import RecruitmentAnalyticsEngine

logger = logging.getLogger("auditagent.platform_router")

router = APIRouter(prefix="/api/v1", tags=["Enterprise Platform"])

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

class AssessmentSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(..., examples=[{"q1": "We use SELECT FOR UPDATE...", "q2": "CREATE INDEX CONCURRENTLY..."}])

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

@router.post("/assessments/generate")
async def generate_assessment(
    req: AssessmentGenerateRequest,
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
        return {
            "id": str(assessment.id),
            "candidate_id": str(assessment.candidate_id),
            "duration_minutes": assessment.duration_minutes,
            "status": assessment.status,
            "questions": assessment.questions_json,
            "problem_set": assessment.questions_json,
            "created_at": assessment.created_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/assessments/{assessment_id}/submit")
async def submit_assessment(
    assessment_id: uuid.UUID,
    req: AssessmentSubmitRequest,
    db: AsyncSession = Depends(get_db),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Grades submitted assessment answers with automated technical rubric."""
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
        "strengths": ass.strengths,
        "weaknesses": ass.weaknesses,
        "feedback": ass.feedback
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

