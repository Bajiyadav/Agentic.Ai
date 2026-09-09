import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, ForeignKey,
    DateTime, Index, JSON, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .session import Base

def utc_now():
    return datetime.now(timezone.utc)

# 1. Organization & Tenancy
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan_tier = Column(String(50), default="starter", nullable=False)  # starter, growth, enterprise
    monthly_resume_limit = Column(Integer, default=50, nullable=False)
    monthly_resumes_used = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    memberships = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="organization", cascade="all, delete-orphan")
    email_connections = relationship("EmailConnection", back_populates="organization", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")

# 2. User & Authentication
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")

# 3. Membership & RBAC
class Membership(Base):
    __tablename__ = "memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="recruiter", nullable=False)  # owner, admin, recruiter, hiring_manager, viewer
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="memberships")
    organization = relationship("Organization", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )

# 4. Candidate & Profile
class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    github_username = Column(String(100), nullable=True, index=True)
    linkedin_url = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    years_experience = Column(Float, nullable=True)
    tags = Column(JSON, default=list)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="candidates")
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    github_profile = relationship("GitHubProfile", back_populates="candidate", uselist=False, cascade="all, delete-orphan")

# 5. Application & Screening
class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = Column(String(255), default="Software Engineer", nullable=False)
    source = Column(String(50), default="upload", nullable=False)  # upload, email, webhook, batch
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, screened, shortlisted, review, rejected
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    audits = relationship("Audit", back_populates="application", cascade="all, delete-orphan")

# 6. Resume & Claims
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), default="application/pdf", nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_path = Column(String(500), nullable=True)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    candidate = relationship("Candidate", back_populates="resumes")
    claims = relationship("ResumeClaim", back_populates="resume", cascade="all, delete-orphan")

class ResumeClaim(Base):
    __tablename__ = "resume_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_type = Column(String(50), nullable=False)  # language, framework, tool, project_impact
    claim_text = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    resume = relationship("Resume", back_populates="claims")

# 7. GitHub Profiles & Evidence
class GitHubProfile(Base):
    __tablename__ = "github_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True)
    username = Column(String(100), nullable=False, index=True)
    profile_found = Column(Boolean, default=True, nullable=False)
    total_public_repos = Column(Integer, default=0, nullable=False)
    original_repos_count = Column(Integer, default=0, nullable=False)
    forked_repos_count = Column(Integer, default=0, nullable=False)
    total_stars = Column(Integer, default=0, nullable=False)
    documentation_ratio = Column(Float, default=0.0, nullable=False)
    recent_activity_count = Column(Integer, default=0, nullable=False)
    languages_json = Column(JSON, default=dict)
    raw_json = Column(JSON, default=dict)
    last_crawled_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    candidate = relationship("Candidate", back_populates="github_profile")

# 8. Audits, Scores & Consensus
class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # AI Verdicts
    overall_score = Column(Integer, nullable=False)
    skills_match_score = Column(Integer, nullable=False)
    code_quality_score = Column(Integer, nullable=False)
    consistency_score = Column(Integer, nullable=False)
    ai_recommendation = Column(String(50), nullable=False)  # SHORTLIST, REVIEW, REJECT
    confidence_level = Column(String(50), default="HIGH", nullable=False)
    needs_manual_review = Column(Boolean, default=False, nullable=False)
    variance_points = Column(Integer, default=0)
    executive_summary = Column(Text, nullable=False)
    latency_seconds = Column(Float, default=0.0)

    # Human-in-the-loop overrides
    recruiter_decision = Column(String(50), nullable=True)  # SHORTLIST, REVIEW, REJECT
    recruiter_decision_reason = Column(Text, nullable=True)
    recruiter_decision_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recruiter_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    application = relationship("Application", back_populates="audits")
    flags = relationship("AuditFlag", back_populates="audit", cascade="all, delete-orphan")
    model_evaluations = relationship("ModelEvaluation", back_populates="audit", cascade="all, delete-orphan")
    generated_replies = relationship("GeneratedReply", back_populates="audit", cascade="all, delete-orphan")

class AuditFlag(Base):
    __tablename__ = "audit_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    flag_type = Column(String(50), nullable=False)  # red, green
    message = Column(Text, nullable=False)
    severity = Column(String(50), default="normal")  # low, normal, critical
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    audit = relationship("Audit", back_populates="flags")

class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=True)
    input_hash = Column(String(64), nullable=True)
    score = Column(Integer, nullable=False)
    raw_output_json = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    audit = relationship("Audit", back_populates="model_evaluations")

# 9. Email Integration & Auto-Drafts
class EmailConnection(Base):
    __tablename__ = "email_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), default="gmail", nullable=False)  # gmail, outlook, custom_imap
    imap_server = Column(String(255), default="imap.gmail.com")
    imap_port = Column(Integer, default=993)
    username = Column(String(255), nullable=False)
    encrypted_credentials = Column(Text, nullable=True)  # Fernet encrypted
    forwarding_alias = Column(String(255), nullable=False, index=True)
    company_name = Column(String(255), default="TechCorp Solutions")
    calendly_link = Column(String(500), default="https://calendly.com/techcorp-hiring/30min")
    auto_draft_replies = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="email_connections")

class GeneratedReply(Base):
    __tablename__ = "generated_replies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    reply_type = Column(String(50), nullable=False)  # interview_invite, rejection, info_request
    status = Column(String(50), default="draft", nullable=False)  # draft, approved, sent, cancelled
    calendly_link = Column(String(500), nullable=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    audit = relationship("Audit", back_populates="generated_replies")

# 10. Persistent Background Job Queue
class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(100), nullable=False, index=True)  # screen_candidate, batch_screen, email_sync, send_digest
    payload_json = Column(JSON, default=dict, nullable=False)
    status = Column(String(50), default="queued", nullable=False, index=True)  # queued, processing, completed, failed
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="jobs")

# 11. Audit Logging
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=False)
    target_id = Column(String(100), nullable=True)
    details_json = Column(JSON, default=dict)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization = relationship("Organization", back_populates="audit_logs")

# 12. Job Description Intelligence & Catalogs
class JobOpening(Base):
    __tablename__ = "job_openings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(100), default="Engineering", nullable=False)
    location = Column(String(100), default="Remote", nullable=False)
    work_model = Column(String(50), default="remote", nullable=False)  # remote, hybrid, onsite
    seniority = Column(String(50), default="Senior", nullable=False)  # Junior, Mid, Senior, Lead, Staff, Principal
    experience_min_years = Column(Float, default=3.0, nullable=False)
    experience_max_years = Column(Float, nullable=True)
    raw_jd_text = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list, nullable=False)
    preferred_skills = Column(JSON, default=list, nullable=False)
    responsibilities = Column(JSON, default=list, nullable=False)
    salary_range = Column(String(100), nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, paused, closed, draft
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    organization = relationship("Organization")
    matches = relationship("JobMatchScore", back_populates="job_opening", cascade="all, delete-orphan")
    assessments = relationship("CandidateAssessment", back_populates="job_opening", cascade="all, delete-orphan")
    interviews = relationship("TechnicalInterview", back_populates="job_opening", cascade="all, delete-orphan")

# 13. Job-Specific Candidate Match Matrix
class JobMatchScore(Base):
    __tablename__ = "job_match_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=True, index=True)
    
    overall_match_pct = Column(Integer, nullable=False)
    required_skills_match_pct = Column(Integer, nullable=False)
    preferred_skills_match_pct = Column(Integer, nullable=False)
    experience_match_pct = Column(Integer, nullable=False)
    matched_required_skills = Column(JSON, default=list)
    missing_required_skills = Column(JSON, default=list)
    matched_preferred_skills = Column(JSON, default=list)
    contradictions = Column(JSON, default=list)
    job_fit_recommendation = Column(String(50), nullable=False)  # STRONG_MATCH, POTENTIAL_MATCH, POOR_MATCH
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    job_opening = relationship("JobOpening", back_populates="matches")
    candidate = relationship("Candidate")
    audit = relationship("Audit")

# 14. Automatic Technical Assessments
class CandidateAssessment(Base):
    __tablename__ = "candidate_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=True, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    duration_minutes = Column(Integer, default=30, nullable=False)  # 10, 20, 30, 60
    status = Column(String(50), default="pending", nullable=False)  # pending, in_progress, completed, expired
    questions_json = Column(JSON, default=list, nullable=False)
    answers_json = Column(JSON, default=dict, nullable=False)
    score = Column(Integer, nullable=True)  # 0-100
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    job_opening = relationship("JobOpening", back_populates="assessments")
    candidate = relationship("Candidate")

# 15. AI Technical Interviewer
class TechnicalInterview(Base):
    __tablename__ = "technical_interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_openings.id", ondelete="CASCADE"), nullable=True, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="scheduled", nullable=False)  # scheduled, in_progress, completed
    current_turn = Column(Integer, default=0, nullable=False)
    turns_json = Column(JSON, default=list, nullable=False)  # List of {question, candidate_answer, ai_followup, score}
    technical_score = Column(Integer, nullable=True)  # 0-100
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    areas_for_human_review = Column(JSON, default=list)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    job_opening = relationship("JobOpening", back_populates="interviews")
    candidate = relationship("Candidate")

# 16. Recruitment Pipeline Stages (Kanban)
class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    stage = Column(String(50), default="applied", nullable=False, index=True)
    # stages: applied, ai_screened, review, shortlist, assessment, tech_interview, final_interview, offer, hired, rejected
    notes = Column(Text, nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    candidate = relationship("Candidate")
    application = relationship("Application")

# 17. ATS Integrations Layer
class AtsIntegration(Base):
    __tablename__ = "ats_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # greenhouse, lever, workday, custom_webhook
    api_key_encrypted = Column(Text, nullable=True)
    webhook_secret_encrypted = Column(Text, nullable=True)
    target_job_id_mapping = Column(JSON, default=dict)
    sync_status = Column(String(50), default="idle", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    organization = relationship("Organization")

# 18. Candidate Evidence Graph Nodes
class EvidenceNode(Base):
    __tablename__ = "evidence_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)  # claim, skill, project, repo, code_evidence, verdict
    label = Column(String(255), nullable=False)
    parent_node_id = Column(UUID(as_uuid=True), ForeignKey("evidence_nodes.id", ondelete="CASCADE"), nullable=True)
    verification_status = Column(String(50), default="Verified", nullable=False)
    # Verified, Partially Verified, Unverified, Contradictory Evidence, Insufficient Public Evidence
    confidence = Column(Float, default=1.0)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    candidate = relationship("Candidate")
    audit = relationship("Audit")

