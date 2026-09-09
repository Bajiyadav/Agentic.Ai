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
