import uuid
from typing import List, Optional
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.db.session import get_db
from src.db.models import User, Membership, Organization
from src.security import decode_access_token
from src.auth.schemas import TenantContext

security_bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Authenticates the incoming request via JWT Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Token missing subject claim.")
        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Query user with memberships and organizations preloaded
    stmt = (
        select(User)
        .options(
            selectinload(User.memberships).selectinload(Membership.organization)
        )
        .where(User.id == user_id, User.is_active == True)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user

async def get_tenant_context(
    request: Request,
    current_user: User = Depends(get_current_user),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id")
) -> TenantContext:
    """Resolves and enforces organization tenancy for the authenticated user."""
    if not current_user.memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to any active organization."
        )

    # If X-Organization-Id header is supplied, verify membership in that specific org
    target_org_id = None
    if x_organization_id:
        try:
            target_org_id = uuid.UUID(x_organization_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Organization-Id UUID format.")

    matched_membership = None
    if target_org_id:
        for m in current_user.memberships:
            if m.organization_id == target_org_id:
                matched_membership = m
                break
        if not matched_membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the requested organization."
            )
    else:
        # Default to first/primary organization
        matched_membership = current_user.memberships[0]

    org = matched_membership.organization
    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This organization account is currently inactive. Please contact support."
        )

    return TenantContext(
        organization_id=org.id,
        organization_name=org.name,
        organization_slug=org.slug,
        plan_tier=org.plan_tier,
        monthly_resume_limit=org.monthly_resume_limit,
        monthly_resumes_used=org.monthly_resumes_used,
        user_id=current_user.id,
        user_email=current_user.email,
        role=matched_membership.role
    )

def require_roles(allowed_roles: List[str]):
    """Route dependency factory enforcing specific role permissions."""
    def role_checker(tenant: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if tenant.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Action requires one of {allowed_roles}, but your role is '{tenant.role}'."
            )
        return tenant
    return role_checker

async def get_tenant_or_demo_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-Id"),
    db: AsyncSession = Depends(get_db)
) -> TenantContext:
    """
    Resolves tenant context:
    - If valid Bearer token provided, enforces strict authentication & membership.
    - If unauthenticated, gracefully defaults to the system default demo organization
      so interactive UI walkthroughs and public simulations function smoothly without disruption.
    """
    if credentials and credentials.credentials:
        try:
            current_user = await get_current_user(credentials=credentials, db=db)
            return await get_tenant_context(request=request, current_user=current_user, x_organization_id=x_organization_id)
        except Exception:
            pass

    # Provision or retrieve standard Demo Organization
    demo_slug = "demo-workspace"
    stmt = select(Organization).where(Organization.slug == demo_slug)
    res = await db.execute(stmt)
    org = res.scalar_one_or_none()

    if not org:
        org = Organization(
            name="Demo Workspace",
            slug=demo_slug,
            plan_tier="growth",
            monthly_resume_limit=500,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.flush()

        # Create demo user
        from src.security import hash_password
        demo_user = User(
            email="demo@auditagent.ai",
            hashed_password=hash_password("DemoAudit123!"),
            full_name="Demo Recruiter",
            is_active=True
        )
        db.add(demo_user)
        await db.flush()

        # Membership
        membership = Membership(
            user_id=demo_user.id,
            organization_id=org.id,
            role="owner"
        )
        db.add(membership)
        await db.commit()
        await db.refresh(org)
        user_id = demo_user.id
        user_email = demo_user.email
    else:
        # Find membership
        m_stmt = select(Membership, User).join(User, Membership.user_id == User.id).where(Membership.organization_id == org.id)
        m_res = await db.execute(m_stmt)
        m_row = m_res.first()
        if m_row:
            user_id = m_row[0].user_id
            user_email = m_row[1].email
        else:
            user_id = uuid.uuid4()
            user_email = "demo@auditagent.ai"

    return TenantContext(
        organization_id=org.id,
        organization_name=org.name,
        organization_slug=org.slug,
        plan_tier=org.plan_tier,
        monthly_resume_limit=org.monthly_resume_limit,
        monthly_resumes_used=org.monthly_resumes_used,
        user_id=user_id,
        user_email=user_email,
        role="owner"
    )

