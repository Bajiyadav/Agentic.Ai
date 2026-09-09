import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class RecruiterOverrideRequest(BaseModel):
    decision: str = Field(..., description="Verdict: SHORTLIST | REVIEW | REJECT")
    reason: str = Field(..., min_length=3, description="Mandatory reason explaining why AI recommendation was overridden")
    notes: Optional[str] = Field(None, description="Optional internal recruiter notes")

class AuditFlagResponse(BaseModel):
    id: uuid.UUID
    flag_type: str
    message: str
    severity: str

    model_config = ConfigDict(from_attributes=True)

class ModelEvaluationResponse(BaseModel):
    model_name: str
    score: int
    raw_output_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class GeneratedReplyResponse(BaseModel):
    id: uuid.UUID
    recipient_name: str
    recipient_email: str
    subject: str
    body_text: str
    reply_type: str
    status: str
    calendly_link: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AuditListItem(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: Optional[str] = None
    github_username: Optional[str] = None
    overall_score: int
    skills_match_score: int
    code_quality_score: int
    consistency_score: int
    ai_recommendation: str
    confidence_level: str
    needs_manual_review: bool
    recruiter_decision: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuditDetailResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    candidate_id: uuid.UUID
    application_id: uuid.UUID
    candidate_name: str
    candidate_email: Optional[str] = None
    github_username: Optional[str] = None
    years_experience: Optional[float] = None
    overall_score: int
    skills_match_score: int
    code_quality_score: int
    consistency_score: int
    ai_recommendation: str
    confidence_level: str
    needs_manual_review: bool
    variance_points: int
    executive_summary: str
    latency_seconds: float
    recruiter_decision: Optional[str] = None
    recruiter_decision_reason: Optional[str] = None
    recruiter_notes: Optional[str] = None
    flags: List[AuditFlagResponse] = []
    model_evaluations: List[ModelEvaluationResponse] = []
    generated_replies: List[GeneratedReplyResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
