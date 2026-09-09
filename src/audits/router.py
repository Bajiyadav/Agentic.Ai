import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from ..db.session import get_db
from ..db.models import Audit, AuditFlag, Candidate, GeneratedReply, AuditLog, utc_now
from ..auth.dependencies import get_tenant_context, require_roles
from ..auth.schemas import TenantContext
from .schemas import (
    AuditListItem, AuditDetailResponse, RecruiterOverrideRequest,
    GeneratedReplyResponse, AuditFlagResponse, ModelEvaluationResponse
)

router = APIRouter(prefix="/api/v1", tags=["Audits & Recruiter Decisions"])

@router.get("/audits", response_model=List[AuditListItem])
async def list_tenant_audits(
    recommendation: Optional[str] = Query(None, description="Filter by AI recommendation (SHORTLIST, REVIEW, REJECT)"),
    decision: Optional[str] = Query(None, description="Filter by recruiter override decision"),
    search: Optional[str] = Query(None, description="Search candidate name or github username"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Lists candidate screening audits strictly isolated to the authenticated organization."""
    query = (
        select(Audit, Candidate)
        .join(Candidate, Audit.candidate_id == Candidate.id)
        .where(Audit.organization_id == tenant.organization_id)
    )

    if recommendation:
        query = query.where(Audit.ai_recommendation == recommendation.upper())
    if decision:
        query = query.where(Audit.recruiter_decision == decision.upper())
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Candidate.name.ilike(search_pattern)) | 
            (Candidate.github_username.ilike(search_pattern))
        )

    query = query.order_by(desc(Audit.created_at)).offset(offset).limit(limit)
    res = await db.execute(query)
    rows = res.all()

    items = []
    for audit, cand in rows:
        items.append(AuditListItem(
            id=audit.id,
            candidate_id=cand.id,
            candidate_name=cand.name,
            candidate_email=cand.email,
            github_username=cand.github_username,
            overall_score=audit.overall_score,
            skills_match_score=audit.skills_match_score,
            code_quality_score=audit.code_quality_score,
            consistency_score=audit.consistency_score,
            ai_recommendation=audit.ai_recommendation,
            confidence_level=audit.confidence_level,
            needs_manual_review=audit.needs_manual_review,
            recruiter_decision=audit.recruiter_decision,
            created_at=audit.created_at
        ))
    return items

@router.get("/audits/{audit_id}", response_model=AuditDetailResponse)
async def get_audit_detail(
    audit_id: uuid.UUID,
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full audit report including flags, multi-agent consensus evaluations, and draft replies."""
    query = (
        select(Audit)
        .options(
            selectinload(Audit.flags),
            selectinload(Audit.model_evaluations),
            selectinload(Audit.generated_replies)
        )
        .where(
            Audit.id == audit_id,
            Audit.organization_id == tenant.organization_id
        )
    )
    res = await db.execute(query)
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found for this organization.")

    # Fetch candidate details
    cand_stmt = select(Candidate).where(Candidate.id == audit.candidate_id)
    c_res = await db.execute(cand_stmt)
    cand = c_res.scalar_one_or_none()

    flags_data = [
        AuditFlagResponse(
            id=f.id, flag_type=f.flag_type, message=f.message, severity=f.severity
        ) for f in audit.flags
    ]

    evals_data = [
        ModelEvaluationResponse(
            model_name=e.model_name, score=e.score, raw_output_json=e.raw_output_json
        ) for e in audit.model_evaluations
    ]

    replies_data = [
        GeneratedReplyResponse(
            id=r.id,
            recipient_name=r.recipient_name,
            recipient_email=r.recipient_email,
            subject=r.subject,
            body_text=r.body_text,
            reply_type=r.reply_type,
            status=r.status,
            calendly_link=r.calendly_link,
            created_at=r.created_at,
            approved_at=r.approved_at,
            sent_at=r.sent_at
        ) for r in audit.generated_replies
    ]

    return AuditDetailResponse(
        id=audit.id,
        organization_id=audit.organization_id,
        candidate_id=audit.candidate_id,
        application_id=audit.application_id,
        candidate_name=cand.name if cand else "Unknown",
        candidate_email=cand.email if cand else None,
        github_username=cand.github_username if cand else None,
        years_experience=cand.years_experience if cand else None,
        overall_score=audit.overall_score,
        skills_match_score=audit.skills_match_score,
        code_quality_score=audit.code_quality_score,
        consistency_score=audit.consistency_score,
        ai_recommendation=audit.ai_recommendation,
        confidence_level=audit.confidence_level,
        needs_manual_review=audit.needs_manual_review,
        variance_points=audit.variance_points,
        executive_summary=audit.executive_summary,
        latency_seconds=audit.latency_seconds,
        recruiter_decision=audit.recruiter_decision,
        recruiter_decision_reason=audit.recruiter_decision_reason,
        recruiter_notes=audit.recruiter_notes,
        flags=flags_data,
        model_evaluations=evals_data,
        generated_replies=replies_data,
        created_at=audit.created_at,
        updated_at=audit.updated_at
    )

@router.post("/audits/{audit_id}/override", response_model=AuditDetailResponse)
async def override_audit_decision(
    audit_id: uuid.UUID,
    req: RecruiterOverrideRequest,
    tenant: TenantContext = Depends(require_roles(["owner", "admin", "recruiter"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Human-in-the-Loop decision override:
    Allows authorized recruiters to override an AI recommendation (SHORTLIST/REVIEW/REJECT)
    with a mandatory logged justification.
    """
    decision_clean = req.decision.strip().upper()
    if decision_clean not in ["SHORTLIST", "REVIEW", "REJECT"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be one of: SHORTLIST, REVIEW, REJECT"
        )

    query = select(Audit).where(
        Audit.id == audit_id,
        Audit.organization_id == tenant.organization_id
    )
    res = await db.execute(query)
    audit = res.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")

    old_decision = audit.recruiter_decision or audit.ai_recommendation
    audit.recruiter_decision = decision_clean
    audit.recruiter_decision_reason = req.reason.strip()
    audit.recruiter_notes = req.notes.strip() if req.notes else None
    audit.recruiter_decision_by = tenant.user_id
    audit.updated_at = utc_now()

    # Log action to tamper-evident audit logs
    db.add(AuditLog(
        organization_id=tenant.organization_id,
        actor_id=tenant.user_id,
        action="recruiter_override",
        target_type="audit",
        target_id=str(audit.id),
        details_json={
            "previous_verdict": old_decision,
            "new_verdict": decision_clean,
            "reason": req.reason.strip()
        }
    ))

    await db.commit()
    return await get_audit_detail(audit_id=audit.id, tenant=tenant, db=db)

# ================= RECRUITER-GATED AUTO-DRAFT REPLIES =================

@router.get("/replies", response_model=List[GeneratedReplyResponse])
async def list_draft_replies(
    status_filter: Optional[str] = Query(None, description="Filter: draft | approved | sent"),
    tenant: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db)
):
    """Lists auto-generated candidate communication drafts requiring recruiter review."""
    query = (
        select(GeneratedReply)
        .where(GeneratedReply.organization_id == tenant.organization_id)
    )
    if status_filter:
        query = query.where(GeneratedReply.status == status_filter.lower())

    query = query.order_by(desc(GeneratedReply.created_at))
    res = await db.execute(query)
    replies = res.scalars().all()

    return [
        GeneratedReplyResponse(
            id=r.id,
            recipient_name=r.recipient_name,
            recipient_email=r.recipient_email,
            subject=r.subject,
            body_text=r.body_text,
            reply_type=r.reply_type,
            status=r.status,
            calendly_link=r.calendly_link,
            created_at=r.created_at,
            approved_at=r.approved_at,
            sent_at=r.sent_at
        ) for r in replies
    ]

@router.post("/replies/{reply_id}/approve", response_model=GeneratedReplyResponse)
async def approve_draft_reply(
    reply_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles(["owner", "admin", "recruiter"])),
    db: AsyncSession = Depends(get_db)
):
    """Approves an auto-draft reply so it is staged for transmission."""
    query = select(GeneratedReply).where(
        GeneratedReply.id == reply_id,
        GeneratedReply.organization_id == tenant.organization_id
    )
    res = await db.execute(query)
    reply = res.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply draft not found.")

    reply.status = "approved"
    reply.approved_by = tenant.user_id
    reply.approved_at = utc_now()

    db.add(AuditLog(
        organization_id=tenant.organization_id,
        actor_id=tenant.user_id,
        action="approve_reply",
        target_type="generated_reply",
        target_id=str(reply.id),
        details_json={"recipient": reply.recipient_email, "type": reply.reply_type}
    ))

    await db.commit()
    await db.refresh(reply)

    return GeneratedReplyResponse(
        id=reply.id,
        recipient_name=reply.recipient_name,
        recipient_email=reply.recipient_email,
        subject=reply.subject,
        body_text=reply.body_text,
        reply_type=reply.reply_type,
        status=reply.status,
        calendly_link=reply.calendly_link,
        created_at=reply.created_at,
        approved_at=reply.approved_at,
        sent_at=reply.sent_at
    )

@router.post("/replies/{reply_id}/send")
async def send_draft_reply(
    reply_id: uuid.UUID,
    tenant: TenantContext = Depends(require_roles(["owner", "admin", "recruiter"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Sends an approved candidate communication email.
    Guarantees that NO email is ever transmitted without explicit recruiter authorization.
    """
    query = select(GeneratedReply).where(
        GeneratedReply.id == reply_id,
        GeneratedReply.organization_id == tenant.organization_id
    )
    res = await db.execute(query)
    reply = res.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply draft not found.")

    if reply.status not in ["approved", "draft"]:
        raise HTTPException(status_code=400, detail=f"Reply cannot be sent in status: {reply.status}")

    # Mark sent and log
    reply.status = "sent"
    reply.sent_at = utc_now()
    if not reply.approved_by:
        reply.approved_by = tenant.user_id
        reply.approved_at = utc_now()

    db.add(AuditLog(
        organization_id=tenant.organization_id,
        actor_id=tenant.user_id,
        action="send_candidate_email",
        target_type="generated_reply",
        target_id=str(reply.id),
        details_json={
            "recipient_email": reply.recipient_email,
            "subject": reply.subject,
            "reply_type": reply.reply_type
        }
    ))

    await db.commit()
    return {
        "status": "sent",
        "reply_id": str(reply.id),
        "recipient_email": reply.recipient_email,
        "sent_at": reply.sent_at.isoformat()
    }
