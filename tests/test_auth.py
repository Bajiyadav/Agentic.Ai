import pytest
import uuid
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()

from src.api import app
from src.db.session import engine, Base

@pytest.mark.asyncio
async def test_auth_and_tenancy_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
        test_password = "SecurePassword123!"
        test_name = "Sarah Jenkins"
        test_company = "Nexus AI Labs"

        # 1. Registration
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_email,
                "password": test_password,
                "full_name": test_name,
                "company_name": test_company
            }
        )
        assert reg_res.status_code == 201, reg_res.text
        reg_data = reg_res.json()
        assert "access_token" in reg_data
        token = reg_data["access_token"]
        user_info = reg_data["user"]
        assert user_info["email"] == test_email.lower()
        assert len(user_info["memberships"]) == 1
        membership = user_info["memberships"][0]
        assert membership["role"] == "owner"
        assert membership["organization_name"] == test_company
        org_id = membership["organization_id"]

        # 2. Duplicate registration rejection
        dup_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_email,
                "password": "anotherpassword",
                "full_name": "Duplicate"
            }
        )
        assert dup_res.status_code == 400

        # 3. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_email,
                "password": test_password
            }
        )
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        login_token = login_data["access_token"]

        # 4. Failed Login
        bad_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_email,
                "password": "WrongPassword!"
            }
        )
        assert bad_login.status_code == 401

        # 5. Access /api/v1/auth/me
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login_token}"}
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["email"] == test_email.lower()

        # 6. Access /api/v1/auth/context with X-Organization-Id
        ctx_res = await client.get(
            "/api/v1/auth/context",
            headers={
                "Authorization": f"Bearer {login_token}",
                "X-Organization-Id": org_id
            }
        )
        assert ctx_res.status_code == 200
        ctx_data = ctx_res.json()
        assert ctx_data["organization_id"] == org_id
        assert ctx_data["role"] == "owner"
        assert ctx_data["plan_tier"] == "starter"
