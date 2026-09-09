import os
import time
import uuid
import hashlib
import tempfile
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import (
    Organization, Candidate, Application, Resume, ResumeClaim,
    GitHubProfile, Audit, AuditFlag, ModelEvaluation,
    GeneratedReply, AuditLog
)
from ..agent_1_resume_parser import parse_resume, CandidateClaims
from ..agent_2_code_auditor import audit_github, GitHubEvidence
from ..consensus_evaluator import run_consensus_evaluation
from ..smart_cache import smart_cache

async def screen_candidate_core(
    db: AsyncSession,
    organization_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
    github_user_override: Optional[str] = None,
    candidate_name_override: Optional[str] = None,
    candidate_email_override: Optional[str] = None,
    linkedin_url_override: Optional[str] = None,
    job_title: str = "Software Engineer",
    source: str = "upload",
    actor_id: Optional[uuid.UUID] = None,
    company_name: str = "TechCorp Solutions",
    calendly_link: str = "https://calendly.com/techcorp-hiring/30min"
) -> Dict[str, Any]:
    """
    Core screening service:
    1. Checks organization quota.
    2. Parses resume claims with anti-prompt-injection delimiters.
    3. Audits GitHub evidence.
    4. Evaluates consensus scoring (40/30/30 deterministic model + multi-agent).
    5. Persists Candidate, Resume, Claims, GitHubProfile, Application, Audit, Flags, ModelEvaluations, and Draft Reply.
    6. Records audit log and increments quota usage.
    """
    start_time = time.time()

    # 1. Enforce organization quota check
    org_stmt = select(Organization).where(Organization.id == organization_id)
    org_res = await db.execute(org_stmt)
    org = org_res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    
    if org.monthly_resumes_used >= org.monthly_resume_limit:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly resume screening limit ({org.monthly_resume_limit}) reached for plan '{org.plan_tier}'. Please upgrade your tier."
        )

    # 2. File hash and temp file creation
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # 3. Parse resume claims
        claims: CandidateClaims = parse_resume(tmp_path)
        if candidate_name_override:
            claims.name = candidate_name_override
        if candidate_email_override:
            claims.email = candidate_email_override
        if linkedin_url_override and not claims.key_claims:
            claims.key_claims.append(f"LinkedIn: {linkedin_url_override}")

        # Resolve GitHub target username
        target_github = github_user_override or claims.github_username or "octocat"

        # 4. Audit GitHub Evidence (with smart caching)
        github_cache = smart_cache.get("github", target_github)
        if github_cache:
            evidence = GitHubEvidence(**github_cache)
        else:
            evidence = audit_github(target_github)
            smart_cache.set("github", target_github, evidence.model_dump())

        # 5. Consensus Multi-Agent Evaluation
        consensus = run_consensus_evaluation(claims, evidence)
        elapsed = round(time.time() - start_time, 2)

        # 6. Database Persistence
        # 6a. Find or create candidate within tenant
        candidate = None
        if claims.email:
            cand_stmt = select(Candidate).where(
                Candidate.organization_id == organization_id,
                Candidate.email == claims.email
            )
            c_res = await db.execute(cand_stmt)
            candidate = c_res.scalar_one_or_none()

        if not candidate:
            candidate = Candidate(
                organization_id=organization_id,
                name=claims.name,
                email=claims.email or candidate_email_override,
                github_username=target_github,
                linkedin_url=linkedin_url_override or claims.github_url,
                years_experience=claims.years_experience or 1.0,
                tags=claims.claimed_languages[:5]
            )
            db.add(candidate)
            await db.flush()
        else:
            if not candidate.github_username:
                candidate.github_username = target_github

        # 6b. Persist Resume
        resume = Resume(
            organization_id=organization_id,
            candidate_id=candidate.id,
            filename=filename,
            file_size_bytes=len(file_bytes),
            mime_type="application/pdf",
            file_hash=file_hash,
            raw_text=f"Parsed {claims.raw_text_length} chars. Name: {claims.name}"
        )
        db.add(resume)
        await db.flush()

        # 6c. Persist Claims
        for lang in claims.claimed_languages:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="language", claim_text=lang))
        for fw in claims.claimed_frameworks:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="framework", claim_text=fw))
        for tool in claims.claimed_tools:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="tool", claim_text=tool))
        for claim in claims.key_claims:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="project_impact", claim_text=claim))

        # 6d. Persist GitHub Profile Evidence
        gh_stmt = select(GitHubProfile).where(GitHubProfile.candidate_id == candidate.id)
        gh_res = await db.execute(gh_stmt)
        gh_profile = gh_res.scalar_one_or_none()
        if not gh_profile:
            gh_profile = GitHubProfile(
                candidate_id=candidate.id,
                username=target_github,
                profile_found=evidence.profile_found,
                total_public_repos=evidence.total_public_repos,
                original_repos_count=evidence.original_repos_count,
                forked_repos_count=evidence.forked_repos_count,
                total_stars=evidence.total_stars,
                documentation_ratio=evidence.documentation_ratio,
                recent_activity_count=evidence.recent_activity_count,
                languages_json=evidence.languages_detected,
                raw_json=evidence.model_dump()
            )
            db.add(gh_profile)
        else:
            gh_profile.total_public_repos = evidence.total_public_repos
            gh_profile.original_repos_count = evidence.original_repos_count
            gh_profile.forked_repos_count = evidence.forked_repos_count
            gh_profile.total_stars = evidence.total_stars
            gh_profile.documentation_ratio = evidence.documentation_ratio
            gh_profile.recent_activity_count = evidence.recent_activity_count
            gh_profile.languages_json = evidence.languages_detected
            gh_profile.raw_json = evidence.model_dump()

        # 6e. Persist Application
        application = Application(
            organization_id=organization_id,
            candidate_id=candidate.id,
            job_title=job_title,
            source=source,
            status=consensus.scorecard.recommendation.lower()
        )
        db.add(application)
        await db.flush()

        # 6f. Persist Audit
        audit = Audit(
            organization_id=organization_id,
            application_id=application.id,
            candidate_id=candidate.id,
            overall_score=consensus.scorecard.overall_score,
            skills_match_score=consensus.scorecard.skills_match_score,
            code_quality_score=consensus.scorecard.code_quality_score,
            consistency_score=consensus.scorecard.consistency_score,
            ai_recommendation=consensus.scorecard.recommendation,
            confidence_level=consensus.confidence_level,
            needs_manual_review=consensus.needs_manual_review,
            variance_points=consensus.variance_points,
            executive_summary=consensus.scorecard.executive_summary,
            latency_seconds=elapsed
        )
        db.add(audit)
        await db.flush()

        # 6g. Persist Flags
        for red_flag in consensus.scorecard.red_flags:
            severity = "critical" if ("0 public" in red_flag or "could not be verified" in red_flag) else "normal"
            db.add(AuditFlag(audit_id=audit.id, flag_type="red", message=red_flag, severity=severity))
        for green_flag in consensus.scorecard.green_flags:
            db.add(AuditFlag(audit_id=audit.id, flag_type="green", message=green_flag, severity="normal"))

        # 6h. Persist Model Evaluations
        for m_name, vote in consensus.model_votes.items():
            score_val = vote if isinstance(vote, int) else (vote.get("score", consensus.scorecard.overall_score) if isinstance(vote, dict) else consensus.scorecard.overall_score)
            raw_json = {"score": score_val} if isinstance(vote, int) else (vote if isinstance(vote, dict) else {})
            db.add(ModelEvaluation(
                audit_id=audit.id,
                model_name=m_name,
                score=score_val,
                raw_output_json=raw_json
            ))

        # 6i. Draft Recruiter Reply (strictly in 'draft' status for human-in-the-loop review)
        if consensus.scorecard.recommendation == "SHORTLIST":
            subject = f"Interview Invitation: {job_title} at {company_name}"
            body_text = (
                f"Hi {claims.name},\n\n"
                f"We were very impressed by your background and public engineering work, particularly your verified projects on GitHub (@{target_github}). "
                f"We would love to invite you for a 30-minute introductory technical interview.\n\n"
                f"Please select a convenient time on our calendar here: {calendly_link}\n\n"
                f"Best regards,\nRecruitment Team\n{company_name}"
            )
            reply_type = "interview_invite"
        elif consensus.scorecard.recommendation == "REJECT":
            subject = f"Application Update: {job_title} at {company_name}"
            body_text = (
                f"Dear {claims.name},\n\n"
                f"Thank you for taking the time to apply for the {job_title} position at {company_name}. "
                f"While your experience is appreciated, we have decided not to move forward with your application at this time based on our specific project requirements.\n\n"
                f"We wish you every success in your ongoing job search.\n\n"
                f"Sincerely,\nTalent Acquisition Team\n{company_name}"
            )
            reply_type = "rejection"
        else:
            subject = f"Additional Information Request: {job_title} at {company_name}"
            body_text = (
                f"Hi {claims.name},\n\n"
                f"Thank you for your application for the {job_title} role at {company_name}. "
                f"Our engineering team is currently reviewing your profile. To help us best evaluate your technical experience, "
                f"could you share any additional repositories or architecture demos that demonstrate your experience with "
                f"{', '.join(claims.claimed_languages[:2]) or 'software architecture'}?\n\n"
                f"Best regards,\nRecruitment Team\n{company_name}"
            )
            reply_type = "info_request"

        reply = GeneratedReply(
            organization_id=organization_id,
            audit_id=audit.id,
            candidate_id=candidate.id,
            recipient_name=claims.name,
            recipient_email=claims.email or candidate_email_override or "candidate@example.com",
            subject=subject,
            body_text=body_text,
            reply_type=reply_type,
            status="draft",
            calendly_link=calendly_link
        )
        db.add(reply)

        # 6j. Increment quota and write AuditLog
        org.monthly_resumes_used += 1
        db.add(AuditLog(
            organization_id=organization_id,
            actor_id=actor_id,
            action="screen_candidate",
            target_type="audit",
            target_id=str(audit.id),
            details_json={
                "candidate_name": claims.name,
                "score": consensus.scorecard.overall_score,
                "recommendation": consensus.scorecard.recommendation
            }
        ))
        # 6k. Initialize Kanban Pipeline Stage
        from src.db.models import PipelineStage
        init_stage = "shortlist" if consensus.scorecard.recommendation == "SHORTLIST" else ("review" if consensus.scorecard.recommendation == "REVIEW" else "ai_screened")
        pipeline_stage = PipelineStage(
            organization_id=organization_id,
            application_id=application.id,
            candidate_id=candidate.id,
            stage=init_stage,
            notes=f"Auto-transitioned from AI consensus score {consensus.scorecard.overall_score}/100 ({consensus.scorecard.recommendation})"
        )
        db.add(pipeline_stage)

        await db.commit()

        # Construct full response payload
        return {
            "id": str(audit.id),
            "audit_id": str(audit.id),
            "candidate_id": str(candidate.id),
            "application_id": str(application.id),
            "candidate_name": claims.name,
            "candidate_email": claims.email or candidate_email_override,
            "github_username": target_github,
            "years_experience": claims.years_experience,
            "overall_score": consensus.scorecard.overall_score,
            "recommendation": consensus.scorecard.recommendation,
            "skills_match_score": consensus.scorecard.skills_match_score,
            "code_quality_score": consensus.scorecard.code_quality_score,
            "consistency_score": consensus.scorecard.consistency_score,
            "confidence_level": consensus.confidence_level,
            "needs_manual_review": consensus.needs_manual_review,
            "variance_points": consensus.variance_points,
            "executive_summary": consensus.scorecard.executive_summary,
            "red_flags": consensus.scorecard.red_flags,
            "green_flags": consensus.scorecard.green_flags,
            "consensus_notes": consensus.consensus_notes,
            "model_votes": consensus.model_votes,
            "claims": claims.model_dump(),
            "evidence": evidence.model_dump(),
            "draft_reply": {
                "id": str(reply.id),
                "subject": reply.subject,
                "body_text": reply.body_text,
                "reply_type": reply.reply_type,
                "status": reply.status
            },
            "cached": False,
            "latency_seconds": elapsed,
            "screened_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    finally:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
