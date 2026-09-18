import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()

from src.api import app

@pytest.mark.asyncio
async def test_cross_tenant_isolation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User & Org A
        res_a = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"alice_{uuid.uuid4().hex[:6]}@alpha.com",
                "password": "PasswordAlpha123!",
                "full_name": "Alice Alpha",
                "company_name": "Alpha Corp"
            }
        )
        assert res_a.status_code == 201
        data_a = res_a.json()
        token_a = data_a["access_token"]
        org_a_id = data_a["user"]["memberships"][0]["organization_id"]

        # 2. Register User & Org B
        res_b = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"bob_{uuid.uuid4().hex[:6]}@beta.com",
                "password": "PasswordBeta123!",
                "full_name": "Bob Beta",
                "company_name": "Beta Corp"
            }
        )
        assert res_b.status_code == 201
        data_b = res_b.json()
        token_b = data_b["access_token"]
        org_b_id = data_b["user"]["memberships"][0]["organization_id"]

        # 3. User A accessing Org A should succeed
        ok_a = await client.get(
            "/api/v1/auth/context",
            headers={
                "Authorization": f"Bearer {token_a}",
                "X-Organization-Id": org_a_id
            }
        )
        assert ok_a.status_code == 200
        assert ok_a.json()["organization_id"] == org_a_id

        # 4. User A attempting to access Org B MUST BE REJECTED WITH 403 FORBIDDEN
        breach_attempt = await client.get(
            "/api/v1/auth/context",
            headers={
                "Authorization": f"Bearer {token_a}",
                "X-Organization-Id": org_b_id
            }
        )
        assert breach_attempt.status_code == 403
        assert "Access denied" in breach_attempt.json()["detail"]

        # 5. User B attempting to access Org A MUST BE REJECTED WITH 403 FORBIDDEN
        breach_attempt_b = await client.get(
            "/api/v1/auth/context",
            headers={
                "Authorization": f"Bearer {token_b}",
                "X-Organization-Id": org_a_id
            }
        )
        assert breach_attempt_b.status_code == 403
        assert "Access denied" in breach_attempt_b.json()["detail"]

@pytest.mark.asyncio
async def test_postgresql_rls_query_isolation():
    """
    Verifies that PostgreSQL Row-Level Security (RLS) physically prevents
    Tenant B from querying Tenant A's candidates and jobs, even with unfiltered SELECT *.
    """
    from sqlalchemy import text
    from src.db.session import AsyncSessionLocal, get_tenant_db

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    cand_a = uuid.uuid4()
    job_a = uuid.uuid4()

    # 1. Admin/Setup transaction (no tenant set) creates orgs, job, and candidate
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO organizations (id, name, slug, plan_tier, monthly_resume_limit, monthly_resumes_used, is_active, created_at, updated_at) VALUES (:id, 'Tenant Alpha', :slug, 'starter', 50, 0, true, NOW(), NOW())"),
            {"id": org_a, "slug": f"rls-alpha-{org_a.hex[:6]}"}
        )
        await session.execute(
            text("INSERT INTO organizations (id, name, slug, plan_tier, monthly_resume_limit, monthly_resumes_used, is_active, created_at, updated_at) VALUES (:id, 'Tenant Beta', :slug, 'starter', 50, 0, true, NOW(), NOW())"),
            {"id": org_b, "slug": f"rls-beta-{org_b.hex[:6]}"}
        )
        await session.execute(
            text("INSERT INTO job_openings (id, organization_id, title, department, location, work_model, seniority, experience_min_years, status, raw_jd_text, required_skills, preferred_skills, responsibilities, created_at, updated_at) VALUES (:id, :org_id, 'Alpha Engineer', 'Engineering', 'Remote', 'remote', 'Senior', 3.0, 'active', 'Requirements', '[]', '[]', '[]', NOW(), NOW())"),
            {"id": job_a, "org_id": org_a}
        )
        await session.execute(
            text("INSERT INTO candidates (id, organization_id, job_id, name, email, is_deleted, created_at, updated_at) VALUES (:id, :org_id, :job_id, 'Alpha Candidate', 'alpha.cand@example.com', false, NOW(), NOW())"),
            {"id": cand_a, "org_id": org_a, "job_id": job_a}
        )
        await session.commit()

    # 2. Query as Tenant B with RLS active -> MUST RETURN 0 ROWS
    async for session_b in get_tenant_db(org_b):
        cand_res = await session_b.execute(text("SELECT id, name FROM candidates WHERE id = :id"), {"id": cand_a})
        assert cand_res.fetchone() is None, "Tenant B must not see Tenant A candidate!"

        job_res = await session_b.execute(text("SELECT id, title FROM job_openings WHERE id = :id"), {"id": job_a})
        assert job_res.fetchone() is None, "Tenant B must not see Tenant A job opening!"

        # Unfiltered full table scan by Tenant B
        all_cands = await session_b.execute(text("SELECT id, name, organization_id FROM candidates"))
        b_cands = all_cands.fetchall()
        for c in b_cands:
            assert c[2] == org_b, f"Tenant B session returned candidate from non-B tenant: {c[2]}"

    # 3. Query as Tenant A with RLS active -> MUST RETURN TENANT A ROWS
    async for session_a in get_tenant_db(org_a):
        cand_res = await session_a.execute(text("SELECT id, name FROM candidates WHERE id = :id"), {"id": cand_a})
        row = cand_res.fetchone()
        assert row is not None, "Tenant A must see its own candidate"
        assert row[1] == "Alpha Candidate"

        job_res = await session_a.execute(text("SELECT id, title FROM job_openings WHERE id = :id"), {"id": job_a})
        job_row = job_res.fetchone()
        assert job_row is not None, "Tenant A must see its own job"
        assert job_row[1] == "Alpha Engineer"

@pytest.mark.asyncio
async def test_postgresql_rls_insert_restriction():
    """
    Verifies that PostgreSQL Row-Level Security WITH CHECK clause raises
    an InsufficientPrivilegeError / check violation if a session attempts
    to insert a record with another tenant's organization_id.
    """
    from sqlalchemy import text
    from src.db.session import AsyncSessionLocal, get_tenant_db

    org_a = uuid.uuid4()
    org_b = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO organizations (id, name, slug, plan_tier, monthly_resume_limit, monthly_resumes_used, is_active, created_at, updated_at) VALUES (:id, 'Tenant A2', :slug, 'starter', 50, 0, true, NOW(), NOW())"),
            {"id": org_a, "slug": f"rls-a2-{org_a.hex[:6]}"}
        )
        await session.execute(
            text("INSERT INTO organizations (id, name, slug, plan_tier, monthly_resume_limit, monthly_resumes_used, is_active, created_at, updated_at) VALUES (:id, 'Tenant B2', :slug, 'starter', 50, 0, true, NOW(), NOW())"),
            {"id": org_b, "slug": f"rls-b2-{org_b.hex[:6]}"}
        )
        await session.commit()

    # Attempt cross-tenant insert within Tenant B session
    async for session_b in get_tenant_db(org_b):
        try:
            await session_b.execute(
                text("INSERT INTO candidates (id, organization_id, name, email, is_deleted, created_at, updated_at) VALUES (:id, :org_id, 'Malicious Insert', 'hack@example.com', false, NOW(), NOW())"),
                {"id": uuid.uuid4(), "org_id": org_a}
            )
            await session_b.commit()
            pytest.fail("Cross-tenant insert should have been rejected by PostgreSQL RLS!")
        except Exception as exc:
            err_str = str(exc).lower()
            assert "row-level security" in err_str or "privilege" in err_str or "violates" in err_str

