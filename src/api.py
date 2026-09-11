import os
import uuid
import time
import tempfile
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Request, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from .agent_1_resume_parser import parse_resume
from .agent_2_code_auditor import audit_github
from .consensus_evaluator import run_consensus_evaluation
from .smart_cache import smart_cache
from .email_parser import parse_eml_file, extract_links_from_text, extract_name_from_subject
from .batch_screener import run_batch_screening, generate_batch_csv, BatchScreeningSummary

from .auth.router import router as auth_router
from .audits.router import router as audit_router
from .routes.platform_router import router as platform_router
from .routes.integrations_router import router as integrations_router
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from .db.session import get_db, async_session_factory
from .auth.dependencies import get_tenant_or_demo_context
from .auth.schemas import TenantContext
from .services.screening_service import screen_candidate_core
from .security import encrypt_secret, decrypt_secret
from fastapi.responses import Response

app = FastAPI(
    title="Resume Screener SaaS API",
    description="Automated AI Resume & Code Evidence Verification Engine",
    version="1.0.0"
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# Secure CORS configuration
allowed_origins_env = os.getenv("CORS_ORIGINS", '["http://localhost:8000","http://127.0.0.1:8000"]')
try:
    import json
    allowed_origins = json.loads(allowed_origins_env)
except Exception:
    allowed_origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import traceback
import logging
logger = logging.getLogger("auditagent.api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc)
    trace = traceback.format_exc()
    logger.error(f"❌ [Unhandled Error] {request.method} {request.url.path}: {error_msg}\n{trace}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{exc.__class__.__name__}: {error_msg}",
            "type": exc.__class__.__name__,
            "path": request.url.path
        }
    )

app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(platform_router)
app.include_router(integrations_router)

# In-memory storage for tasks and history with resilient demo seeds
tasks_db: Dict[str, Dict[str, Any]] = {}
DEFAULT_DEMO_SCREENINGS: List[Dict[str, Any]] = [
    {
        "id": "demo-001",
        "audit_id": "demo-001",
        "candidate_name": "Aarav Sharma",
        "github_username": "aaravsharma-dev",
        "overall_score": 88,
        "recommendation": "STRONG_CANDIDATE",
        "status_label": "Strong Candidate",
        "recruiter_recommendation": "STRONG_CANDIDATE",
        "ai_recommendation": "STRONG_CANDIDATE",
        "recruiter_decision": "SHORTLIST",
        "skills_match_score": 92,
        "code_quality_score": 85,
        "consistency_score": 87,
        "confidence_level": "HIGH",
        "executive_summary": "Top-tier Full-Stack candidate with verified production contributions, clean async patterns, and active open-source activity.",
        "is_valid_resume": True,
        "document_type": "RESUME",
        "next_action": "SCHEDULE_INTERVIEW",
        "next_action_label": "Proceed to technical interview",
        "screened_at": "Today 10:30"
    },
    {
        "id": "demo-002",
        "audit_id": "demo-002",
        "candidate_name": "Elena Rostova",
        "github_username": "elena-ml-research",
        "overall_score": 74,
        "recommendation": "REVIEW",
        "status_label": "Review",
        "recruiter_recommendation": "REVIEW",
        "ai_recommendation": "REVIEW",
        "recruiter_decision": "REVIEW",
        "skills_match_score": 80,
        "code_quality_score": 68,
        "consistency_score": 75,
        "confidence_level": "MEDIUM",
        "executive_summary": "Solid ML engineering background with PyTorch repositories. Recommend recruiter review on backend distributed systems.",
        "is_valid_resume": True,
        "document_type": "RESUME",
        "next_action": "REVIEW_RECOMMENDED",
        "next_action_label": "Recruiter review recommended",
        "screened_at": "Today 09:15"
    },
    {
        "id": "demo-003",
        "audit_id": "demo-003",
        "candidate_name": "Kevin Miller",
        "github_username": "kmiller-coder",
        "overall_score": 28,
        "recommendation": "REJECT",
        "status_label": "Rejected",
        "recruiter_recommendation": "REJECT",
        "ai_recommendation": "REJECT",
        "recruiter_decision": "REJECT",
        "skills_match_score": 30,
        "code_quality_score": 25,
        "consistency_score": 30,
        "confidence_level": "HIGH",
        "executive_summary": "Claims 5+ years in Go & Kubernetes, but public profile shows zero relevant commit history and non-functional forks.",
        "is_valid_resume": True,
        "document_type": "RESUME",
        "next_action": "DO_NOT_PROCEED",
        "next_action_label": "Do not proceed",
        "screened_at": "Yesterday 16:45"
    },
    {
        "id": "demo-004",
        "audit_id": "demo-004",
        "candidate_name": "Non-Resume Academic Exercise",
        "github_username": "student101",
        "overall_score": 0,
        "recommendation": "INVALID_DOCUMENT",
        "status_label": "Invalid Document",
        "recruiter_recommendation": "INVALID_DOCUMENT",
        "ai_recommendation": "INVALID_DOCUMENT",
        "recruiter_decision": "REJECT",
        "skills_match_score": 0,
        "code_quality_score": 0,
        "consistency_score": 0,
        "confidence_level": "HIGH",
        "executive_summary": "Uploaded file is a homework assignment sheet / lab instructions, not a professional resume. Screening halted.",
        "is_valid_resume": False,
        "document_type": "ACADEMIC_LAB_OR_EXERCISE",
        "next_action": "REQUEST_RESUME",
        "next_action_label": "Request a valid resume",
        "screened_at": "Yesterday 14:20"
    }
]
history_db: List[Dict[str, Any]] = list(DEFAULT_DEMO_SCREENINGS)

# In-memory storage for jobs with resilient demo seeds
DEFAULT_JOBS: List[Dict[str, Any]] = [
    {
        "id": "job-001",
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "Remote",
        "work_model": "remote",
        "seniority": "Senior",
        "experience_min_years": 5.0,
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "AWS"],
        "preferred_skills": ["Kubernetes", "Kafka", "CI/CD", "GraphQL"],
        "responsibilities": [
            "Architect and build high-throughput backend services and microservices.",
            "Design, optimize, and maintain PostgreSQL database schemas and Redis caching.",
            "Ensure system reliability, low-latency API response times, and automated CI/CD testing."
        ],
        "qualifications": ["5+ years professional backend engineering experience in Python."],
        "raw_jd_text": "We are looking for a Senior Backend Engineer to architect and scale our core services using Python, FastAPI, PostgreSQL, Redis, and Docker in AWS.",
        "status": "active",
        "candidates_count": 24,
        "created_at": "2026-09-01T10:00:00Z"
    },
    {
        "id": "job-002",
        "title": "Full-Stack Engineer",
        "department": "Product Engineering",
        "location": "Remote / Hybrid",
        "work_model": "hybrid",
        "seniority": "Mid-Senior",
        "experience_min_years": 3.0,
        "required_skills": ["React", "TypeScript", "Node.js", "Next.js", "TailwindCSS"],
        "preferred_skills": ["GraphQL", "PostgreSQL", "Docker", "Jest"],
        "responsibilities": [
            "Develop modern, responsive web applications using React, Next.js, and TypeScript.",
            "Collaborate with product designers to implement pixel-perfect user interfaces.",
            "Build robust Node.js backend endpoints and integrate third-party APIs."
        ],
        "qualifications": ["3+ years building full-stack web applications with React and TypeScript."],
        "raw_jd_text": "We are seeking a talented Full-Stack Engineer skilled in React, TypeScript, Next.js, and Node.js to build delightful user experiences.",
        "status": "active",
        "candidates_count": 41,
        "created_at": "2026-09-03T11:30:00Z"
    },
    {
        "id": "job-003",
        "title": "AI/ML Platform Engineer",
        "department": "AI Research & Platform",
        "location": "Remote",
        "work_model": "remote",
        "seniority": "Senior",
        "experience_min_years": 4.0,
        "required_skills": ["Python", "PyTorch", "LLMs", "Kubernetes", "Docker", "FastAPI"],
        "preferred_skills": ["MLflow", "Triton", "vLLM", "Ray", "AWS"],
        "responsibilities": [
            "Deploy, optimize, and serve large language models (LLMs) in production with low latency.",
            "Build robust inference pipelines and automated model evaluation benchmarks.",
            "Scale Kubernetes clusters for GPU-accelerated workloads."
        ],
        "qualifications": ["4+ years in machine learning engineering, model deployment, and Python systems."],
        "raw_jd_text": "Looking for an AI/ML Platform Engineer with strong PyTorch, LLM serving, and Kubernetes infrastructure skills.",
        "status": "active",
        "candidates_count": 18,
        "created_at": "2026-09-05T09:15:00Z"
    }
]
jobs_db: Dict[str, Dict[str, Any]] = {j["id"]: dict(j) for j in DEFAULT_JOBS}

class JobCreateRequest(BaseModel):
    title: str
    department: Optional[str] = "Engineering"
    location: Optional[str] = "Remote"
    work_model: Optional[str] = "remote"
    seniority: Optional[str] = "Senior"
    experience_min_years: Optional[float] = 3.0
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    qualifications: List[str] = Field(default_factory=list)
    raw_jd_text: Optional[str] = ""
    status: Optional[str] = "active"

class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    work_model: Optional[str] = None
    seniority: Optional[str] = None
    experience_min_years: Optional[float] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    qualifications: Optional[List[str]] = None
    raw_jd_text: Optional[str] = None
    status: Optional[str] = None

STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Resume Screener SaaS API active. Visit /docs for Swagger UI."}

@app.get("/assessment.html")
async def serve_assessment_page():
    ass_path = STATIC_DIR / "assessment.html"
    if ass_path.exists():
        return FileResponse(str(ass_path))
    raise HTTPException(status_code=404, detail="Assessment portal page not found.")

@app.get("/assessment.js")
async def serve_assessment_js():
    js_path = STATIC_DIR / "assessment.js"
    if js_path.exists():
        return FileResponse(str(js_path), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="Assessment JS not found.")

@app.get("/assessment/{assessment_id}")
async def serve_assessment_direct(assessment_id: str):
    ass_path = STATIC_DIR / "assessment.html"
    if ass_path.exists():
        return FileResponse(str(ass_path))
    raise HTTPException(status_code=404, detail="Assessment portal page not found.")

# ============================================================================
# JOB DESCRIPTION INTELLIGENCE & JOB MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/v1/jobs/parse")
async def parse_job_description_endpoint(
    raw_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Parses a complete Job Description text or uploaded file (.pdf, .docx, .txt) into structured intelligence."""
    from .services.jd_service import process_job_description_input
    file_bytes = None
    filename = None
    if file:
        file_bytes = await file.read()
        filename = file.filename

    if not raw_text and not file_bytes:
        raise HTTPException(status_code=400, detail="Must provide either raw text or an uploaded file (.pdf, .docx, .txt).")

    try:
        parsed = process_job_description_input(raw_text=raw_text, file_bytes=file_bytes, filename=filename)
        return {"status": "success", "data": parsed.model_dump()}
    except Exception as e:
        logger.error(f"Error parsing job description: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse job description: {str(e)}")

@app.get("/api/v1/jobs")
async def list_jobs_endpoint():
    """Lists all active and archived job openings."""
    return {"jobs": list(jobs_db.values())}

@app.post("/api/v1/jobs")
async def create_job_endpoint(payload: JobCreateRequest):
    """Creates a new job profile."""
    job_id = f"job-{uuid.uuid4().hex[:8]}"
    job_data = {
        "id": job_id,
        "title": payload.title,
        "department": payload.department or "Engineering",
        "location": payload.location or "Remote",
        "work_model": payload.work_model or "remote",
        "seniority": payload.seniority or "Senior",
        "experience_min_years": float(payload.experience_min_years or 3.0),
        "required_skills": payload.required_skills or [],
        "preferred_skills": payload.preferred_skills or [],
        "responsibilities": payload.responsibilities or [],
        "qualifications": payload.qualifications or [],
        "raw_jd_text": payload.raw_jd_text or "",
        "status": payload.status or "active",
        "candidates_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    jobs_db[job_id] = job_data
    return {"status": "created", "job": job_data}

@app.get("/api/v1/jobs/{job_id}")
async def get_job_endpoint(job_id: str):
    """Retrieves a specific job profile."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job opening not found.")
    return jobs_db[job_id]

@app.put("/api/v1/jobs/{job_id}")
async def update_job_endpoint(job_id: str, payload: JobUpdateRequest):
    """Updates an existing job profile."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job opening not found.")
    current = jobs_db[job_id]
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        if v is not None:
            current[k] = v
    jobs_db[job_id] = current
    return {"status": "updated", "job": current}

@app.delete("/api/v1/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    """Deletes a job profile."""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job opening not found.")
    jobs_db.pop(job_id)
    return {"status": "deleted", "job_id": job_id}

async def _process_screening_task(
    task_id: str,
    organization_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    github_user_override: Optional[str],
    webhook_url: Optional[str],
    actor_id: Optional[uuid.UUID] = None,
    target_role: Optional[str] = None,
    required_skills: Optional[List[str]] = None,
    min_experience: Optional[float] = None,
    linkedin_url: Optional[str] = None,
    job_description: Optional[str] = None,
    job_id: Optional[str] = None
):
    start_time = time.time()
    try:
        tasks_db[task_id]["status"] = "processing"
        
        # Merge job profile data if job_id was specified
        if job_id and job_id in jobs_db:
            j = jobs_db[job_id]
            target_role = target_role or j.get("title")
            job_description = job_description or j.get("raw_jd_text")
            if min_experience is None:
                min_experience = j.get("experience_min_years")
            j_req = j.get("required_skills", [])
            if required_skills:
                seen_sk = {s.lower() for s in required_skills}
                required_skills = required_skills + [s for s in j_req if s.lower() not in seen_sk]
            else:
                required_skills = list(j_req)

        result_payload = None
        try:
            async with async_session_factory() as db:
                result_payload = await screen_candidate_core(
                    db=db,
                    organization_id=organization_id,
                    file_bytes=file_bytes,
                    filename=filename,
                    github_user_override=github_user_override,
                    linkedin_url_override=linkedin_url,
                    job_title=target_role or "Software Engineer",
                    required_skills=required_skills,
                    min_experience=min_experience,
                    job_description=job_description,
                    actor_id=actor_id
                )
        except Exception as db_err:
            from .services.screening_service import execute_screening_pipeline_core
            result_payload = execute_screening_pipeline_core(
                file_bytes=file_bytes,
                filename=filename,
                github_user_override=github_user_override,
                linkedin_url_override=linkedin_url,
                job_title=target_role or "Software Engineer",
                required_skills=required_skills,
                min_experience=min_experience,
                job_description=job_description
            )
        result_payload["task_id"] = task_id

        # Attach Job Profile & Detailed Evidence Match
        try:
            from .services.jd_service import StructuredJobDescription, evaluate_candidate_job_fit
            from .agent_1_resume_parser import CandidateClaims
            from .agent_2_code_auditor import GitHubEvidence

            active_jd = None
            if job_id and job_id in jobs_db:
                j = jobs_db[job_id]
                active_jd = StructuredJobDescription(
                    title=j.get("title", target_role or "Software Engineer"),
                    department=j.get("department", "Engineering"),
                    location=j.get("location", "Remote"),
                    work_model=j.get("work_model", "remote"),
                    seniority=j.get("seniority", "Senior"),
                    experience_min_years=float(j.get("experience_min_years", min_experience or 3.0)),
                    required_skills=j.get("required_skills", required_skills or []),
                    preferred_skills=j.get("preferred_skills", []),
                    responsibilities=j.get("responsibilities", []),
                    raw_jd_text=j.get("raw_jd_text", "")
                )
                jobs_db[job_id]["candidates_count"] = jobs_db[job_id].get("candidates_count", 0) + 1
            elif target_role or required_skills or job_description:
                active_jd = StructuredJobDescription(
                    title=target_role or "Software Engineer",
                    experience_min_years=float(min_experience or 3.0),
                    required_skills=required_skills or [],
                    preferred_skills=[],
                    raw_jd_text=job_description or ""
                )

            if active_jd and "claims_obj" in result_payload and "evidence_obj" in result_payload:
                c_obj = result_payload["claims_obj"]
                e_obj = result_payload["evidence_obj"]
                claims_model = CandidateClaims(**c_obj) if isinstance(c_obj, dict) else c_obj
                evidence_model = GitHubEvidence(**e_obj) if isinstance(e_obj, dict) else e_obj
                
                is_valid = getattr(claims_model, "is_valid_resume", True)
                if is_valid:
                    fit = evaluate_candidate_job_fit(claims_model, evidence_model, active_jd)
                    result_payload["job_match_score"] = fit.overall_match_pct
                    result_payload["job_match_result"] = fit.model_dump()
                    result_payload["job_id"] = job_id
                    result_payload["job_title"] = active_jd.title
                else:
                    result_payload["job_match_score"] = 0
                    result_payload["job_id"] = job_id
                    result_payload["job_title"] = active_jd.title
        except Exception as fit_err:
            logger.warning(f"Could not compute job-specific evidence match: {fit_err}")
            
        tasks_db[task_id] = {
            "task_id": task_id,
            "status": "completed",
            "result": result_payload,
            "created_at": time.time()
        }
        history_db.insert(0, result_payload)

        # Webhook callback if requested
        if webhook_url and webhook_url.startswith("http"):
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(webhook_url, json={"task_id": task_id, "result": result_payload}, timeout=5)
            except Exception:
                pass

    except Exception as e:
        tasks_db[task_id] = {
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
            "created_at": time.time()
        }

@app.post("/api/v1/screen")
async def screen_resume_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    github_username: Optional[str] = Form(None),
    target_role: Optional[str] = Form(None),
    job_description: Optional[str] = Form(None),
    required_skills: Optional[str] = Form(None),
    min_experience: Optional[float] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    webhook_url: Optional[str] = Form(None),
    job_id: Optional[str] = Form(None),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Submits a candidate resume for asynchronous screening with PostgreSQL persistence, company skills audit, and tenant isolation."""
    # 1. Validate file extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()

    # 2. Prevent memory exhaustion: 10MB limit
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds maximum allowed size of 10MB.")

    # 3. Security magic byte verification
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file: Missing %PDF- magic signature.")

    task_id = str(uuid.uuid4())
    tasks_db[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "created_at": time.time()
    }

    parsed_skills = [s.strip() for s in required_skills.split(",") if s.strip()] if required_skills else None

    # If Job Description paragraph is provided, extract requirements
    if job_description and job_description.strip():
        from src.services.jd_service import parse_job_description
        parsed_jd = parse_job_description(job_description.strip())
        if not target_role and parsed_jd.title:
            target_role = parsed_jd.title
        if min_experience is None and parsed_jd.experience_min_years:
            min_experience = parsed_jd.experience_min_years

        extracted_skills = parsed_jd.required_skills or []
        if parsed_skills:
            existing_lower = {s.lower() for s in parsed_skills}
            for s in extracted_skills:
                if s.lower() not in existing_lower:
                    parsed_skills.append(s)
        else:
            parsed_skills = extracted_skills

    # Dispatch to background task worker
    background_tasks.add_task(
        _process_screening_task,
        task_id=task_id,
        organization_id=tenant.organization_id,
        file_bytes=file_bytes,
        filename=file.filename,
        github_user_override=github_username,
        webhook_url=webhook_url,
        actor_id=tenant.user_id,
        target_role=target_role,
        required_skills=parsed_skills,
        min_experience=min_experience,
        linkedin_url=linkedin_url,
        job_description=job_description.strip() if job_description else None,
        job_id=job_id
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "organization_id": str(tenant.organization_id),
        "poll_url": f"/api/v1/results/{task_id}"
    }

@app.get("/api/v1/results/{task_id}")
@app.get("/api/v1/screen/{task_id}")
async def get_screening_result(task_id: str):
    """Retrieves screening task status and result."""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Screening task not found.")
    return task

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats(
    tenant: TenantContext = Depends(get_tenant_or_demo_context),
    db: AsyncSession = Depends(get_db)
):
    """Returns aggregated recruiter metrics: screened today, strong, review, rejected, invalid, and credits."""
    from .db.models import Audit, Candidate, Organization
    from sqlalchemy import select, desc
    from datetime import date

    credits_limit = 250
    credits_used = 0
    credits_avail = 250
    rows = []

    try:
        org_stmt = select(Organization).where(Organization.id == tenant.organization_id)
        org_res = await db.execute(org_stmt)
        org = org_res.scalar_one_or_none()

        if org:
            credits_limit = org.monthly_resume_limit
            credits_used = org.monthly_resumes_used
            credits_avail = max(0, credits_limit - credits_used)

        stmt = (
            select(Audit, Candidate)
            .join(Candidate, Audit.candidate_id == Candidate.id)
            .where(Audit.organization_id == tenant.organization_id)
            .order_by(desc(Audit.created_at))
            .limit(100)
        )
        res = await db.execute(stmt)
        rows = res.all()
    except Exception as db_err:
        logger.warning(f"Database query error in dashboard stats ({db_err}). Using in-memory stats.")
        rows = []

    today = date.today()
    screened_today = 0
    strong_count = 0
    review_count = 0
    rejected_count = 0
    invalid_count = 0
    recent_screenings = []

    if rows:
        for a, c in rows:
            if a.created_at and a.created_at.date() == today:
                screened_today += 1

            is_invalid_doc = bool(
                "non-resume" in (c.name or "").lower()
                or "corrupt" in (c.name or "").lower()
                or "not appear to be a professional resume" in (a.executive_summary or "").lower()
                or "not a valid professional resume" in (a.executive_summary or "").lower()
                or "screening halted" in (a.executive_summary or "").lower()
            )
            is_valid = not is_invalid_doc
            rec = (a.recruiter_decision or a.ai_recommendation or "").upper()

            if not is_valid:
                invalid_count += 1
                status_label = "Invalid Document"
                rec_label = "INVALID_DOCUMENT"
            elif rec in ("SHORTLIST", "STRONG_CANDIDATE") or a.overall_score >= 80:
                strong_count += 1
                status_label = "Strong Candidate"
                rec_label = "STRONG_CANDIDATE"
            elif rec == "REVIEW" or a.overall_score >= 40:
                review_count += 1
                status_label = "Review"
                rec_label = "REVIEW"
            else:
                rejected_count += 1
                status_label = "Rejected"
                rec_label = "REJECT"

            if len(recent_screenings) < 10:
                recent_screenings.append({
                    "id": str(a.id),
                    "audit_id": str(a.id),
                    "candidate_name": c.name,
                    "overall_score": a.overall_score,
                    "recommendation": rec_label,
                    "status_label": status_label,
                    "is_valid_resume": is_valid,
                    "screened_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else "Today"
                })
    else:
        total_screened = len(history_db)
        screened_today = sum(1 for item in history_db if "Today" in (item.get("screened_at") or "")) or total_screened
        credits_used = len(history_db)
        credits_avail = max(0, credits_limit - credits_used)
        for item in history_db:
            is_valid = item.get("is_valid_resume")
            if is_valid is None:
                is_invalid_doc = bool(
                    "non-resume" in (item.get("candidate_name") or "").lower()
                    or item.get("recruiter_recommendation") == "INVALID_DOCUMENT"
                    or "invalid" in (item.get("document_type") or "").lower()
                    or "screening halted" in (item.get("executive_summary") or "").lower()
                )
                is_valid = not is_invalid_doc
            rec = (item.get("recommendation", "")).upper()
            score = item.get("overall_score", 0)
            if not is_valid:
                invalid_count += 1
                status_label = "Invalid Document"
                rec_label = "INVALID_DOCUMENT"
            elif rec in ("SHORTLIST", "STRONG_CANDIDATE") or score >= 80:
                strong_count += 1
                status_label = "Strong Candidate"
                rec_label = "STRONG_CANDIDATE"
            elif rec == "REVIEW" or score >= 40:
                review_count += 1
                status_label = "Review"
                rec_label = "REVIEW"
            else:
                rejected_count += 1
                status_label = "Rejected"
                rec_label = "REJECT"

            if len(recent_screenings) < 10:
                recent_screenings.append({
                    "id": item.get("id"),
                    "audit_id": item.get("audit_id", item.get("id")),
                    "candidate_name": item.get("candidate_name"),
                    "overall_score": score,
                    "recommendation": rec_label,
                    "status_label": item.get("status_label", status_label),
                    "is_valid_resume": is_valid,
                    "screened_at": item.get("screened_at", "Today")
                })

    total_screened = len(rows) or len(history_db)
    return {
        "screened_today": screened_today or total_screened,
        "total_screened": total_screened,
        "strong_count": strong_count,
        "review_count": review_count,
        "rejected_count": rejected_count,
        "invalid_count": invalid_count,
        "credits_available": credits_avail,
        "credits_limit": credits_limit,
        "credits_used": credits_used,
        "recent_screenings": recent_screenings
    }

@app.get("/api/v1/screenings")
async def list_recent_screenings(
    limit: int = 50,
    filter_status: Optional[str] = None,
    q: Optional[str] = None,
    tenant: TenantContext = Depends(get_tenant_or_demo_context),
    db: AsyncSession = Depends(get_db)
):
    """Returns recent candidate evaluations for the active tenant organization with filtering and search."""
    from .db.models import Audit, Candidate
    from sqlalchemy import select, desc
    
    rows = []
    try:
        stmt = (
            select(Audit, Candidate)
            .join(Candidate, Audit.candidate_id == Candidate.id)
            .where(Audit.organization_id == tenant.organization_id)
            .order_by(desc(Audit.created_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        rows = res.all()
    except Exception as db_err:
        logger.warning(f"Database query error in list_recent_screenings ({db_err}). Using in-memory history.")
        rows = []

    items = []
    if rows:
        for a, c in rows:
            is_invalid_doc = bool(
                "non-resume" in (c.name or "").lower()
                or "corrupt" in (c.name or "").lower()
                or "not appear to be a professional resume" in (a.executive_summary or "").lower()
                or "not a valid professional resume" in (a.executive_summary or "").lower()
                or "screening halted" in (a.executive_summary or "").lower()
            )
            is_valid = not is_invalid_doc
            doc_type = "RESUME" if is_valid else "ACADEMIC_LAB_OR_EXERCISE"
            raw_rec = (a.recruiter_decision or a.ai_recommendation or "").upper()
            if not is_valid:
                norm_rec = "INVALID_DOCUMENT"
                status_label = "Invalid Document"
                next_act = "REQUEST_RESUME"
                next_act_lbl = "Request a valid resume"
            elif raw_rec in ("SHORTLIST", "STRONG_CANDIDATE") or a.overall_score >= 80:
                norm_rec = "STRONG_CANDIDATE"
                status_label = "Strong Candidate"
                next_act = "SCHEDULE_INTERVIEW"
                next_act_lbl = "Proceed to technical interview"
            elif raw_rec == "REVIEW" or a.overall_score >= 40:
                norm_rec = "REVIEW"
                status_label = "Review"
                next_act = "REVIEW_RECOMMENDED"
                next_act_lbl = "Recruiter review recommended"
            else:
                norm_rec = "REJECT"
                status_label = "Rejected"
                next_act = "DO_NOT_PROCEED"
                next_act_lbl = "Do not proceed"

            items.append({
                "id": str(a.id),
                "audit_id": str(a.id),
                "candidate_name": c.name,
                "github_username": c.github_username,
                "overall_score": a.overall_score,
                "recommendation": a.recruiter_decision or a.ai_recommendation,
                "status_label": status_label,
                "recruiter_recommendation": norm_rec,
                "ai_recommendation": a.ai_recommendation,
                "recruiter_decision": a.recruiter_decision,
                "skills_match_score": a.skills_match_score,
                "code_quality_score": a.code_quality_score,
                "consistency_score": a.consistency_score,
                "confidence_level": a.confidence_level,
                "executive_summary": a.executive_summary,
                "is_valid_resume": is_valid,
                "document_type": doc_type,
                "next_action": next_act,
                "next_action_label": next_act_lbl,
                "screened_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S") if a.created_at else "Just now"
            })
    else:
        items = history_db[:limit]

    if q and q.strip():
        search_lower = q.strip().lower()
        items = [it for it in items if search_lower in (it.get("candidate_name") or "").lower() or search_lower in (it.get("github_username") or "").lower()]

    if filter_status and filter_status.upper() != "ALL":
        fs = filter_status.upper()
        if fs in ("STRONG", "STRONG_CANDIDATE", "SHORTLIST"):
            items = [it for it in items if it.get("overall_score", 0) >= 80 and it.get("is_valid_resume", True)]
        elif fs == "REVIEW":
            items = [it for it in items if 40 <= it.get("overall_score", 0) < 80 and it.get("is_valid_resume", True)]
        elif fs in ("REJECT", "REJECTED"):
            items = [it for it in items if it.get("overall_score", 0) < 40 and it.get("is_valid_resume", True)]
        elif fs in ("INVALID", "INVALID_DOCUMENT"):
            items = [it for it in items if not it.get("is_valid_resume", True) or it.get("overall_score", 0) == 0]

    return items

@app.get("/api/v1/health")
async def health_check():
    """System diagnostic and auto-monitoring endpoint."""
    cache_stats = smart_cache.get_stats()
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.time(),
        "total_screenings": len(history_db),
        "total_batches": len(batches_db),
        "cache": cache_stats,
        "environment": {
            "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
            "github_token_configured": bool(os.getenv("GITHUB_TOKEN")),
            "mock_fallback_active": os.getenv("USE_MOCK_FALLBACK", "true").lower() == "true"
        }
    }

# In-memory storage for batches
batches_db: Dict[str, Dict[str, Any]] = {}

@app.post("/api/v1/batch/screen")
async def screen_batch_endpoint(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    job_id: Optional[str] = Form(None)
):
    """Batch screening endpoint for multiple resumes or forwarded .eml files."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    target_role = None
    required_skills = None
    min_experience = None
    job_description = None
    if job_id and job_id in jobs_db:
        j = jobs_db[job_id]
        target_role = j.get("title")
        required_skills = j.get("required_skills")
        min_experience = j.get("experience_min_years")
        job_description = j.get("raw_jd_text")
        j["candidates_count"] = j.get("candidates_count", 0) + len(files)

    batch_id = str(uuid.uuid4())
    applications = []

    for f in files:
        content = await f.read()
        fname = f.filename.lower()
        if fname.endswith(".eml"):
            app = parse_eml_file(content)
            applications.append({
                "name": app.candidate_name,
                "email": app.email_sender,
                "github_username": app.github_username,
                "linkedin_url": app.linkedin_url,
                "pdf_bytes": app.pdf_bytes or b""
            })
        elif fname.endswith(".pdf"):
            # Plain PDF upload in batch
            applications.append({
                "name": f.filename.replace(".pdf", "").replace("_", " ").title(),
                "pdf_bytes": content,
                "github_username": None,
                "linkedin_url": None
            })

    batches_db[batch_id] = {
        "batch_id": batch_id,
        "status": "processing",
        "total_files": len(files),
        "created_at": time.time(),
        "summary": None,
        "job_id": job_id
    }

    async def _run_batch_task():
        try:
            summary = await run_batch_screening(
                batch_id,
                applications,
                target_role=target_role,
                required_skills=required_skills,
                min_experience=min_experience,
                job_description=job_description
            )
            batches_db[batch_id]["status"] = "completed"
            batches_db[batch_id]["summary"] = summary.model_dump()
        except Exception as e:
            batches_db[batch_id]["status"] = "failed"
            batches_db[batch_id]["error"] = str(e)

    background_tasks.add_task(_run_batch_task)

    return {
        "batch_id": batch_id,
        "status": "processing",
        "total_candidates": len(applications),
        "poll_url": f"/api/v1/batch/{batch_id}"
    }

@app.post("/api/v1/batch/simulate")
async def simulate_morning_batch(background_tasks: BackgroundTasks):
    """Simulates an inbound morning batch of 10 forwarded candidate emails."""
    from create_batch_mock_data import MOCK_CANDIDATES
    
    batch_id = str(uuid.uuid4())
    sample_pdf = b""
    if os.path.exists("sample_resume.pdf"):
        with open("sample_resume.pdf", "rb") as f:
            sample_pdf = f.read()

    applications = [
        {
            "name": c["name"],
            "email": c["email"],
            "github_username": c["github"],
            "linkedin_url": c["linkedin"],
            "pdf_bytes": sample_pdf
        }
        for c in MOCK_CANDIDATES
    ]

    batches_db[batch_id] = {
        "batch_id": batch_id,
        "status": "processing",
        "total_files": len(applications),
        "created_at": time.time(),
        "summary": None
    }

    async def _run_sim_task():
        try:
            summary = await run_batch_screening(batch_id, applications)
            batches_db[batch_id]["status"] = "completed"
            batches_db[batch_id]["summary"] = summary.model_dump()
        except Exception as e:
            batches_db[batch_id]["status"] = "failed"
            batches_db[batch_id]["error"] = str(e)

    background_tasks.add_task(_run_sim_task)

    return {
        "batch_id": batch_id,
        "status": "processing",
        "total_candidates": len(applications),
        "poll_url": f"/api/v1/batch/{batch_id}"
    }

@app.get("/api/v1/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Retrieves batch screening status and ranked leaderboard."""
    batch = batches_db.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch task not found.")
    return batch

@app.get("/api/v1/batch/{batch_id}/csv")
async def export_batch_csv(batch_id: str):
    """Exports ranked candidate leaderboard as downloadable CSV."""
    from fastapi.responses import Response
    batch = batches_db.get(batch_id)
    if not batch or not batch.get("summary"):
        raise HTTPException(status_code=404, detail="Batch summary not ready.")
    
    summary = BatchScreeningSummary(**batch["summary"])
    csv_data = generate_batch_csv(summary)
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=screening_batch_{batch_id[:8]}.csv"}
    )

# ================= EMAIL INTEGRATION ENDPOINTS =================
from .email_connector import EmailConfig, EmailInboxSync
from .db.models import EmailConnection, AuditLog

current_email_config = EmailConfig()

@app.get("/api/v1/email/config")
async def get_email_config(
    tenant: TenantContext = Depends(get_tenant_or_demo_context),
    db: AsyncSession = Depends(get_db)
):
    """Returns the organization's active email sync and forwarding settings with masked credentials."""
    try:
        stmt = select(EmailConnection).where(EmailConnection.organization_id == tenant.organization_id)
        res = await db.execute(stmt)
        conn = res.scalar_one_or_none()
        
        if conn:
            return {
                "provider": conn.provider,
                "imap_server": conn.imap_server,
                "imap_port": conn.imap_port,
                "username": conn.username,
                "password": "••••••••" if conn.encrypted_credentials else "",
                "forwarding_alias": conn.forwarding_alias,
                "company_name": conn.company_name,
                "calendly_link": conn.calendly_link,
                "auto_draft_replies": conn.auto_draft_replies,
                "is_active": conn.is_active,
                "last_synced_at": conn.last_synced_at.isoformat() if conn.last_synced_at else None
            }
    except Exception as db_err:
        logger.warning(f"Database query error in get_email_config ({db_err}). Using in-memory config.")

    cfg = current_email_config.model_dump()
    cfg["password"] = "••••••••" if current_email_config.password else ""
    return cfg

@app.post("/api/v1/email/config")
async def update_email_config(
    cfg: EmailConfig,
    tenant: TenantContext = Depends(get_tenant_or_demo_context),
    db: AsyncSession = Depends(get_db)
):
    """Updates organization email sync credentials and alias with AES-256 Fernet encrypted storage."""
    global current_email_config
    current_email_config = cfg

    try:
        stmt = select(EmailConnection).where(EmailConnection.organization_id == tenant.organization_id)
        res = await db.execute(stmt)
        conn = res.scalar_one_or_none()

        encrypted_pwd = None
        if cfg.password and "••" not in cfg.password:
            encrypted_pwd = encrypt_secret(cfg.password)

        if not conn:
            conn = EmailConnection(
                organization_id=tenant.organization_id,
                provider=cfg.provider,
                imap_server=cfg.imap_server,
                imap_port=cfg.imap_port,
                username=cfg.username,
                encrypted_credentials=encrypted_pwd,
                forwarding_alias=cfg.forwarding_alias,
                company_name=cfg.company_name,
                calendly_link=cfg.calendly_link,
                auto_draft_replies=cfg.auto_draft_replies,
                is_active=True
            )
            db.add(conn)
        else:
            conn.provider = cfg.provider
            conn.imap_server = cfg.imap_server
            conn.imap_port = cfg.imap_port
            conn.username = cfg.username
            if encrypted_pwd:
                conn.encrypted_credentials = encrypted_pwd
            conn.forwarding_alias = cfg.forwarding_alias
            conn.company_name = cfg.company_name
            conn.calendly_link = cfg.calendly_link
            conn.auto_draft_replies = cfg.auto_draft_replies

        db.add(AuditLog(
            organization_id=tenant.organization_id,
            actor_id=tenant.user_id,
            action="update_email_config",
            target_type="email_connection",
            target_id=str(conn.id),
            details_json={"provider": cfg.provider, "alias": cfg.forwarding_alias}
        ))

        await db.commit()
    except Exception as db_err:
        logger.warning(f"Database update error in update_email_config ({db_err}). Saved in-memory.")

    return {"status": "updated", "config": current_email_config.model_dump(exclude={"password"})}

@app.post("/api/v1/email/sync")
async def sync_inbox_endpoint(
    background_tasks: BackgroundTasks,
    job_id: Optional[str] = Query(None)
):
    """Option A: Connects directly to recruiter inbox, pulls unread applications, and screens them."""
    syncer = EmailInboxSync(current_email_config)
    apps = syncer.fetch_unread_applications(limit=15)

    if not apps:
        return {"status": "no_new_emails", "message": "No unread applications found in inbox."}

    target_role = None
    required_skills = None
    min_experience = None
    job_description = None
    if job_id and job_id in jobs_db:
        j = jobs_db[job_id]
        target_role = j.get("title")
        required_skills = j.get("required_skills")
        min_experience = j.get("experience_min_years")
        job_description = j.get("raw_jd_text")
        j["candidates_count"] = j.get("candidates_count", 0) + len(apps)

    batch_id = str(uuid.uuid4())
    sample_pdf = b""
    if os.path.exists("sample_resume.pdf"):
        with open("sample_resume.pdf", "rb") as f:
            sample_pdf = f.read()

    batch_apps = [
        {
            "name": app.candidate_name,
            "email": app.email_sender,
            "github_username": app.github_username,
            "linkedin_url": app.linkedin_url,
            "pdf_bytes": app.pdf_bytes or sample_pdf
        }
        for app in apps
    ]

    batches_db[batch_id] = {
        "batch_id": batch_id,
        "status": "processing",
        "total_files": len(batch_apps),
        "created_at": time.time(),
        "summary": None,
        "job_id": job_id
    }

    async def _run_sync_task():
        try:
            summary = await run_batch_screening(
                batch_id,
                batch_apps,
                target_role=target_role,
                required_skills=required_skills,
                min_experience=min_experience,
                job_description=job_description
            )
            batches_db[batch_id]["status"] = "completed"
            batches_db[batch_id]["summary"] = summary.model_dump()
        except Exception as e:
            batches_db[batch_id]["status"] = "failed"
            batches_db[batch_id]["error"] = str(e)

    background_tasks.add_task(_run_sync_task)

    return {
        "batch_id": batch_id,
        "status": "processing",
        "found_applications": len(apps),
        "poll_url": f"/api/v1/batch/{batch_id}"
    }

@app.post("/api/v1/email/webhook/{company_alias}")
async def receive_inbound_webhook(
    company_alias: str,
    background_tasks: BackgroundTasks,
    request: Request
):
    """Option B: Receives forwarded emails via webhook from SendGrid, SES, Mailgun, or Gmail filter."""
    body_bytes = await request.body()
    
    # Check if raw EML or multipart
    sample_pdf = b""
    if os.path.exists("sample_resume.pdf"):
        with open("sample_resume.pdf", "rb") as f:
            sample_pdf = f.read()

    try:
        app = parse_eml_file(body_bytes)
    except Exception:
        app = None

    cand_name = app.candidate_name if app else "Webhook Candidate"
    github = app.github_username if app else "tiangolo"
    pdf = (app.pdf_bytes if app and app.pdf_bytes else None) or sample_pdf

    batch_id = str(uuid.uuid4())
    batch_apps = [{
        "name": cand_name,
        "email": app.email_sender if app else "candidate@example.com",
        "github_username": github,
        "linkedin_url": app.linkedin_url if app else None,
        "pdf_bytes": pdf
    }]

    batches_db[batch_id] = {
        "batch_id": batch_id,
        "status": "processing",
        "total_files": 1,
        "created_at": time.time(),
        "summary": None
    }

    async def _run_webhook_task():
        try:
            summary = await run_batch_screening(batch_id, batch_apps)
            batches_db[batch_id]["status"] = "completed"
            batches_db[batch_id]["summary"] = summary.model_dump()
        except Exception as e:
            batches_db[batch_id]["status"] = "failed"
            batches_db[batch_id]["error"] = str(e)

    background_tasks.add_task(_run_webhook_task)

    return {
        "status": "received",
        "company_alias": company_alias,
        "batch_id": batch_id,
        "poll_url": f"/api/v1/batch/{batch_id}"
    }

# ================= PRICING, DIGEST & SCHEDULER ENDPOINTS =================
from .digest_notifier import DigestNotifier
from .email_scheduler import email_scheduler

PRICING_TIERS = [
    {
        "tier_id": "starter",
        "name": "Starter",
        "price_inr": "₹5,000",
        "cadence": "/ month",
        "badge": "Entry Point",
        "description": "Ideal for solo recruiters or early-stage startups hiring occasionally.",
        "features": [
            "Up to 50 resume screenings / month",
            "Resume PDF claim parsing",
            "Public GitHub code auditing",
            "Single candidate audit UI",
            "1 recruiter seat",
            "Standard email support"
        ],
        "is_popular": False,
        "cta_text": "Start Free Trial"
    },
    {
        "tier_id": "growth",
        "name": "Growth Batch",
        "price_inr": "₹15,000",
        "cadence": "/ month",
        "badge": "Most Popular",
        "description": "For high-volume tech recruitment teams screening daily applicants.",
        "features": [
            "Up to 500 screenings / month",
            "Dedicated Inbound Email Alias (@auditagent.ai)",
            "30-second Gmail auto-forwarding",
            "Parallel batch screening (10+ at once)",
            "Ranked Leaderboard & 1-Click CSV export",
            "Red-flag fluffer detection",
            "3 recruiter seats"
        ],
        "is_popular": True,
        "cta_text": "Upgrade to Growth"
    },
    {
        "tier_id": "enterprise",
        "name": "Enterprise God-Mode",
        "price_inr": "₹35,000",
        "cadence": "/ month",
        "badge": "Automated Suite",
        "description": "Zero-friction inbox sync with automated draft replies and daily Slack digests.",
        "features": [
            "Unlimited candidate screenings",
            "Direct Gmail / Outlook 1-Click Inbox Sync",
            "Automatic color-coded Gmail labeling",
            "Auto-drafted replies (Interview invite / Rejection)",
            "Morning 8:30 AM Slack & WhatsApp Briefing",
            "Automated 15-min background poller",
            "ATS Webhook integration",
            "Dedicated Slack channel support"
        ],
        "is_popular": False,
        "cta_text": "Contact Enterprise Sales"
    }
]

@app.get("/api/v1/pricing")
async def get_pricing_tiers():
    """Returns commercial B2B pricing tiers and feature entitlements."""
    return {"tiers": PRICING_TIERS}

class DigestRequest(BaseModel):
    batch_id: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    whatsapp_phone: Optional[str] = None

@app.post("/api/v1/digest/send")
async def send_morning_digest_endpoint(req: DigestRequest):
    """Dispatches 8:30 AM morning recruiter summary to Slack or WhatsApp."""
    # Find summary for batch or latest batch
    summary = None
    if req.batch_id and req.batch_id in batches_db:
        summary = batches_db[req.batch_id].get("summary")
    elif batches_db:
        latest = list(batches_db.values())[-1]
        summary = latest.get("summary")

    if not summary:
        # Generate representative sample summary for demonstration
        from .batch_screener import BatchScreeningSummary, BatchCandidateResult
        summary = {
            "batch_id": "demo_batch",
            "total_candidates": 10,
            "shortlisted_count": 7,
            "review_count": 0,
            "rejected_count": 3,
            "processing_time_seconds": 13.5,
            "candidates": [
                {"candidate_name": "Emily Davis", "overall_score": 92, "recommendation": "SHORTLIST", "github_username": "nonexistent_github_dev_999"},
                {"candidate_name": "Kevin Miller", "overall_score": 92, "recommendation": "SHORTLIST", "github_username": "none"},
                {"candidate_name": "Sarah Chen", "overall_score": 83, "recommendation": "SHORTLIST", "github_username": "tiangolo"}
            ]
        }

    slack_res = await DigestNotifier.send_slack_notification(req.slack_webhook_url or "", summary)
    wa_res = await DigestNotifier.send_whatsapp_notification(req.whatsapp_phone or "", summary)

    return {
        "status": "dispatched",
        "slack": slack_res,
        "whatsapp": wa_res
    }

@app.get("/api/v1/scheduler/status")
async def get_scheduler_status():
    """Checks the status of the background email polling worker."""
    return email_scheduler.get_status()

@app.post("/api/v1/scheduler/toggle")
async def toggle_scheduler(request: Request):
    """Enables or disables automatic background email polling."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    interval = int(body.get("interval_minutes", 15)) if isinstance(body, dict) else 15
    active = body.get("active") if isinstance(body, dict) else None

    if active is not None:
        target_active = bool(active)
    else:
        # Toggle current running state
        target_active = not email_scheduler.is_running

    if target_active:
        email_scheduler.start(interval_seconds=max(60, interval * 60))
    else:
        email_scheduler.stop()
    return email_scheduler.get_status()

