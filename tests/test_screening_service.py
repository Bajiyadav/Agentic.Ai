import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.api import app
from src.db.session import async_session_factory
from src.db.models import (
    Organization, Candidate, Application, Resume, ResumeClaim,
    GitHubProfile, Audit, AuditFlag, ModelEvaluation, GeneratedReply, AuditLog
)
from src.services.screening_service import screen_candidate_core

@pytest.mark.asyncio
async def test_screening_persists_to_postgresql_and_tracks_quota():
    # 1. Setup a unique test tenant organization
    org_id = uuid.uuid4()
    org_slug = f"screen-test-{org_id.hex[:6]}"
    
    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Screening Test Corp",
            slug=org_slug,
            plan_tier="starter",
            monthly_resume_limit=2,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.commit()

    with open("sample_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    # 2. Execute screening service core
    async with async_session_factory() as db:
        result = await screen_candidate_core(
            db=db,
            organization_id=org_id,
            file_bytes=pdf_bytes,
            filename="sample_resume.pdf",
            candidate_name_override="Alice Engineer",
            github_user_override="octocat"
        )

    assert result["candidate_name"] == "Alice Engineer"
    assert result["github_username"] == "octocat"
    assert "overall_score" in result
    assert result["recommendation"] in ["SHORTLIST", "REVIEW", "REJECT"]
    assert "draft_reply" in result
    assert result["draft_reply"]["status"] == "draft"

    # 3. Verify all 10 relational tables in PostgreSQL
    async with async_session_factory() as db:
        # Check Candidate
        cand_stmt = select(Candidate).where(Candidate.organization_id == org_id)
        candidate = (await db.execute(cand_stmt)).scalar_one_or_none()
        assert candidate is not None
        assert candidate.name == "Alice Engineer"

        # Check Resume & Claims
        resume_stmt = select(Resume).where(Resume.candidate_id == candidate.id)
        resume = (await db.execute(resume_stmt)).scalar_one_or_none()
        assert resume is not None
        assert resume.filename == "sample_resume.pdf"
        assert resume.file_hash is not None

        claims_stmt = select(ResumeClaim).where(ResumeClaim.resume_id == resume.id)
        claims = (await db.execute(claims_stmt)).scalars().all()
        assert len(claims) > 0

        # Check GitHub Profile
        gh_stmt = select(GitHubProfile).where(GitHubProfile.candidate_id == candidate.id)
        gh = (await db.execute(gh_stmt)).scalar_one_or_none()
        assert gh is not None
        assert gh.username == "octocat"

        # Check Audit
        audit_stmt = select(Audit).where(Audit.organization_id == org_id)
        audit = (await db.execute(audit_stmt)).scalar_one_or_none()
        assert audit is not None
        assert audit.overall_score == result["overall_score"]
        assert audit.ai_recommendation == result["recommendation"]

        # Check Flags
        flags_stmt = select(AuditFlag).where(AuditFlag.audit_id == audit.id)
        flags = (await db.execute(flags_stmt)).scalars().all()
        assert len(flags) > 0

        # Check Model Evaluations
        evals_stmt = select(ModelEvaluation).where(ModelEvaluation.audit_id == audit.id)
        evals = (await db.execute(evals_stmt)).scalars().all()
        assert len(evals) > 0

        # Check Generated Reply Draft (human-in-the-loop)
        reply_stmt = select(GeneratedReply).where(GeneratedReply.audit_id == audit.id)
        reply = (await db.execute(reply_stmt)).scalar_one_or_none()
        assert reply is not None
        assert reply.status == "draft"
        assert reply.recipient_name == "Alice Engineer"

        # Check Quota Usage incremented
        org_check = await db.get(Organization, org_id)
        assert org_check.monthly_resumes_used == 1

        # Check Audit Log
        log_stmt = select(AuditLog).where(AuditLog.organization_id == org_id)
        log_entries = (await db.execute(log_stmt)).scalars().all()
        assert len(log_entries) >= 1
        assert log_entries[0].action == "screen_candidate"

@pytest.mark.asyncio
async def test_screening_quota_exhaustion_enforced():
    # Setup organization with quota limit reached
    org_id = uuid.uuid4()
    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Exhausted Corp",
            slug=f"exhausted-{org_id.hex[:6]}",
            plan_tier="starter",
            monthly_resume_limit=1,
            monthly_resumes_used=1, # Limit already reached
            is_active=True
        )
        db.add(org)
        await db.commit()

    with open("sample_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        async with async_session_factory() as db:
            await screen_candidate_core(
                db=db,
                organization_id=org_id,
                file_bytes=pdf_bytes,
                filename="sample_resume.pdf"
            )

    assert exc_info.value.status_code == 402
    assert "limit" in exc_info.value.detail.lower()

@pytest.mark.asyncio
async def test_file_security_and_magic_byte_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Non-PDF rejected
        res = await client.post(
            "/api/v1/screen",
            files={"file": ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")}
        )
        assert res.status_code == 400
        assert "PDF" in res.json()["detail"]

        # 2. Fake PDF with wrong magic signature rejected
        res_fake = await client.post(
            "/api/v1/screen",
            files={"file": ("fake.pdf", b"NOT_A_PDF_CONTENT_HERE", "application/pdf")}
        )
        assert res_fake.status_code == 400
        assert "magic" in res_fake.json()["detail"].lower()
