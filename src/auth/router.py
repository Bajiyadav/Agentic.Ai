import re
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.db.session import get_db
from src.db.models import User, Organization, Membership, AuditLog
from src.security import hash_password, verify_password, create_access_token
from src.auth.schemas import (
    UserRegister, UserLogin, TokenResponse, UserResponse,
    MembershipInfo, OrganizationResponse, TenantContext
)
from src.auth.dependencies import get_current_user, get_tenant_context

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Organizations"])

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:50] or "org"

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(req: UserRegister, db: AsyncSession = Depends(get_db)):
    """Registers a new user, provisions their company organization, and returns an access token."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == req.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 1. Create Organization
    company_name = req.company_name or f"{req.full_name.split()[0]}'s Team"
    base_slug = slugify(company_name)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(
        name=company_name,
        slug=slug,
        plan_tier="starter",
        monthly_resume_limit=50,
        monthly_resumes_used=0
    )
    db.add(org)
    await db.flush()

    # 2. Create User
    user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.flush()

    # 3. Assign Owner Membership
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role="owner"
    )
    db.add(membership)

    # 4. Log Audit Event
    audit_log = AuditLog(
        organization_id=org.id,
        actor_id=user.id,
        action="user_registered",
        target_type="organization",
        target_id=str(org.id),
        details_json={"email": user.email, "company": org.name}
    )
    db.add(audit_log)
    await db.commit()

    # Generate Token
    token = create_access_token({"sub": str(user.id), "email": user.email, "org_id": str(org.id)})

    user_resp = UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        memberships=[
            MembershipInfo(
                organization_id=str(org.id),
                organization_name=org.name,
                organization_slug=org.slug,
                plan_tier=org.plan_tier,
                role=membership.role
            )
        ]
    )

    return TokenResponse(
        access_token=token,
        expires_in=86400,
        user=user_resp
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(req: UserLogin, db: AsyncSession = Depends(get_db)):
    """Verifies credentials and returns a signed JWT access token."""
    stmt = (
        select(User)
        .options(selectinload(User.memberships).selectinload(Membership.organization))
        .where(User.email == req.email.lower(), User.is_active == True)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    primary_org_id = str(user.memberships[0].organization_id) if user.memberships else None
    token = create_access_token({"sub": str(user.id), "email": user.email, "org_id": primary_org_id})

    memberships_info = [
        MembershipInfo(
            organization_id=str(m.organization_id),
            organization_name=m.organization.name,
            organization_slug=m.organization.slug,
            plan_tier=m.organization.plan_tier,
            role=m.role
        )
        for m in user.memberships
    ]

    return TokenResponse(
        access_token=token,
        expires_in=86400,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            memberships=memberships_info
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Returns profile and memberships for the authenticated user."""
    memberships_info = [
        MembershipInfo(
            organization_id=str(m.organization_id),
            organization_name=m.organization.name,
            organization_slug=m.organization.slug,
            plan_tier=m.organization.plan_tier,
            role=m.role
        )
        for m in current_user.memberships
    ]
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        memberships=memberships_info
    )

@router.get("/context", response_model=TenantContext)
async def get_active_tenant_context(tenant: TenantContext = Depends(get_tenant_context)):
    """Returns active organization tenancy details and user's role for the current request."""
    return tenant
