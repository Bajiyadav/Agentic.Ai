import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.api import app
from src.db.session import async_session_factory
from src.db.models import Organization, User, Membership, AuditLog
from src.security import hash_password, create_access_token
from src.services.screening_service import screen_candidate_core

@pytest.mark.asyncio
async def test_audit_lifecycle_overrides_and_reply_approval():
    # 1. Create Organization and Recruiter User
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    org_slug = f"audit-test-{org_id.hex[:6]}"

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Lifecycle Test Corp",
            slug=org_slug,
            plan_tier="growth",
            monthly_resume_limit=100,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)

        user = User(
            id=user_id,
            email=f"recruiter-{user_id.hex[:6]}@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Lead Recruiter",
            is_active=True
        )
        db.add(user)

        membership = Membership(
            user_id=user.id,
            organization_id=org.id,
            role="recruiter"
        )
        db.add(membership)
        await db.commit()

    # 2. Screen a candidate for this org to generate an audit & draft reply
    with open("sample_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    async with async_session_factory() as db:
        screen_res = await screen_candidate_core(
            db=db,
            organization_id=org_id,
            file_bytes=pdf_bytes,
            filename="sample_resume.pdf",
            candidate_name_override="Bob Coder",
            github_user_override="octocat",
            actor_id=user_id
        )

    audit_id = screen_res["audit_id"]
    reply_id = screen_res["draft_reply"]["id"]
    token = create_access_token(data={"sub": str(user_id), "email": user.email})
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org_id)
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 3. List Audits for Tenant
        res = await client.get("/api/v1/audits", headers=auth_headers)
        assert res.status_code == 200
        audits = res.json()
        assert len(audits) >= 1
        assert audits[0]["id"] == audit_id
        assert audits[0]["candidate_name"] == "Bob Coder"

        # 4. Get Audit Detail
        res_detail = await client.get(f"/api/v1/audits/{audit_id}", headers=auth_headers)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["id"] == audit_id
        assert len(detail["flags"]) > 0
        assert len(detail["model_evaluations"]) > 0
        assert len(detail["generated_replies"]) > 0

        # 5. Recruiter Decision Override (e.g., changing verdict to SHORTLIST with logged reason)
        res_override = await client.post(
            f"/api/v1/audits/{audit_id}/override",
            json={
                "decision": "SHORTLIST",
                "reason": "Exceptional private portfolio reviewed during technical interview.",
                "notes": "Fast-track to onsite final round."
            },
            headers=auth_headers
        )
        assert res_override.status_code == 200
        overridden = res_override.json()
        assert overridden["recruiter_decision"] == "SHORTLIST"
        assert "Exceptional private portfolio" in overridden["recruiter_decision_reason"]
        assert overridden["recruiter_notes"] == "Fast-track to onsite final round."

        # 6. Verify Tamper-Evident AuditLog in PostgreSQL
        async with async_session_factory() as db:
            log_stmt = select(AuditLog).where(
                AuditLog.organization_id == org_id,
                AuditLog.action == "recruiter_override"
            )
            log_entry = (await db.execute(log_stmt)).scalar_one_or_none()
            assert log_entry is not None
            assert log_entry.target_id == audit_id
            assert log_entry.actor_id == user_id

        # 7. List Auto-Draft Replies
        res_replies = await client.get("/api/v1/replies", headers=auth_headers)
        assert res_replies.status_code == 200
        replies = res_replies.json()
        assert len(replies) >= 1
        assert replies[0]["status"] == "draft"

        # 8. Approve Auto-Draft Reply
        res_approve = await client.post(f"/api/v1/replies/{reply_id}/approve", headers=auth_headers)
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "approved"

        # 9. Send Approved Reply
        res_send = await client.post(f"/api/v1/replies/{reply_id}/send", headers=auth_headers)
        assert res_send.status_code == 200
        assert res_send.json()["status"] == "sent"

@pytest.mark.asyncio
async def test_rbac_viewer_cannot_override_audit():
    # Setup Viewer User
    org_id = uuid.uuid4()
    viewer_id = uuid.uuid4()

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="RBAC Test Corp",
            slug=f"rbac-test-{org_id.hex[:6]}",
            plan_tier="starter",
            monthly_resume_limit=50,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)

        viewer = User(
            id=viewer_id,
            email=f"viewer-{viewer_id.hex[:6]}@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Read Only Viewer",
            is_active=True
        )
        db.add(viewer)

        membership = Membership(
            user_id=viewer.id,
            organization_id=org.id,
            role="viewer"  # Read-only role
        )
        db.add(membership)
        await db.commit()

    token = create_access_token(data={"sub": str(viewer_id), "email": viewer.email})
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-Id": str(org_id)
    }

    dummy_audit_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Viewer attempting override must receive 403 Forbidden
        res = await client.post(
            f"/api/v1/audits/{dummy_audit_id}/override",
            json={"decision": "SHORTLIST", "reason": "Unauthorized attempt"},
            headers=headers
        )
        assert res.status_code == 403
        assert "Permission denied" in res.json()["detail"]
