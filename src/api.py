import os
import uuid
import time
import tempfile
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Request, Depends
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
from sqlalchemy.ext.asyncio import AsyncSession
from .db.session import get_db, async_session_factory
from .auth.dependencies import get_tenant_or_demo_context
from .auth.schemas import TenantContext
from .services.screening_service import screen_candidate_core
from .security import encrypt_secret, decrypt_secret

app = FastAPI(
    title="Resume Screener SaaS API",
    description="Automated AI Resume & Code Evidence Verification Engine",
    version="1.0.0"
)

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

app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(platform_router)

# In-memory storage for tasks and history
tasks_db: Dict[str, Dict[str, Any]] = {}
history_db: List[Dict[str, Any]] = []

STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Resume Screener SaaS API active. Visit /docs for Swagger UI."}

async def _process_screening_task(
    task_id: str,
    organization_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    github_user_override: Optional[str],
    webhook_url: Optional[str],
    actor_id: Optional[uuid.UUID] = None
):
    start_time = time.time()
    try:
        tasks_db[task_id]["status"] = "processing"
        
        async with async_session_factory() as db:
            result_payload = await screen_candidate_core(
                db=db,
                organization_id=organization_id,
                file_bytes=file_bytes,
                filename=filename,
                github_user_override=github_user_override,
                actor_id=actor_id
            )
            result_payload["task_id"] = task_id
            
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
    webhook_url: Optional[str] = Form(None),
    tenant: TenantContext = Depends(get_tenant_or_demo_context)
):
    """Submits a candidate resume for asynchronous screening with PostgreSQL persistence and tenant isolation."""
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

    # Run processing within authenticated tenant organization
    background_tasks.add_task(
        _process_screening_task,
        task_id=task_id,
        organization_id=tenant.organization_id,
        file_bytes=file_bytes,
        filename=file.filename,
        github_user_override=github_username,
        webhook_url=webhook_url,
        actor_id=tenant.user_id
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "organization_id": str(tenant.organization_id),
        "poll_url": f"/api/v1/results/{task_id}"
    }

@app.get("/api/v1/results/{task_id}")
async def get_screening_result(task_id: str):
    """Retrieves screening task status and result."""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Screening task not found.")
    return task

@app.get("/api/v1/screenings")
async def list_recent_screenings(
    limit: int = 15,
    tenant: TenantContext = Depends(get_tenant_or_demo_context),
    db: AsyncSession = Depends(get_db)
):
    """Returns recent candidate evaluations for the active tenant organization."""
    from .db.models import Audit, Candidate
    from sqlalchemy import select, desc
    
    stmt = (
        select(Audit, Candidate)
        .join(Candidate, Audit.candidate_id == Candidate.id)
        .where(Audit.organization_id == tenant.organization_id)
        .order_by(desc(Audit.created_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = res.all()

    if rows:
        results = []
        for a, c in rows:
            results.append({
                "id": str(a.id),
                "audit_id": str(a.id),
                "candidate_name": c.name,
                "github_username": c.github_username,
                "overall_score": a.overall_score,
                "recommendation": a.recruiter_decision or a.ai_recommendation,
                "ai_recommendation": a.ai_recommendation,
                "recruiter_decision": a.recruiter_decision,
                "skills_match_score": a.skills_match_score,
                "code_quality_score": a.code_quality_score,
                "consistency_score": a.consistency_score,
                "confidence_level": a.confidence_level,
                "executive_summary": a.executive_summary,
                "screened_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return results

    return history_db[:limit]

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
    files: List[UploadFile] = File(...)
):
    """Batch screening endpoint for multiple resumes or forwarded .eml files."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

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
        "summary": None
    }

    async def _run_batch_task():
        try:
            summary = await run_batch_screening(batch_id, applications)
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
    return {"status": "updated", "config": current_email_config.model_dump(exclude={"password"})}

@app.post("/api/v1/email/sync")
async def sync_inbox_endpoint(background_tasks: BackgroundTasks):
    """Option A: Connects directly to recruiter inbox, pulls unread applications, and screens them."""
    syncer = EmailInboxSync(current_email_config)
    apps = syncer.fetch_unread_applications(limit=15)

    if not apps:
        return {"status": "no_new_emails", "message": "No unread applications found in inbox."}

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
        "summary": None
    }

    async def _run_sync_task():
        try:
            summary = await run_batch_screening(batch_id, batch_apps)
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
async def toggle_scheduler(active: bool = True):
    """Enables or disables automatic background email polling."""
    if active:
        email_scheduler.start(interval_seconds=900)
    else:
        email_scheduler.stop()
    return email_scheduler.get_status()
