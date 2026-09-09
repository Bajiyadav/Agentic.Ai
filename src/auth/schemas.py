import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    full_name: str = Field(min_length=2, max_length=100)
    company_name: Optional[str] = Field(default=None, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan_tier: str
    monthly_resume_limit: int
    monthly_resumes_used: int


class MembershipInfo(BaseModel):
    organization_id: str
    organization_name: str
    organization_slug: str
    plan_tier: str
    role: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    is_verified: bool
    memberships: List[MembershipInfo] = []

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TenantContext(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    plan_tier: str
    monthly_resume_limit: int
    monthly_resumes_used: int
    user_id: uuid.UUID
    user_email: str
    role: str  # owner, admin, recruiter, hiring_manager, viewer
