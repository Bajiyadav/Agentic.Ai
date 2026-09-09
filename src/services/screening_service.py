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
    required_skills: Optional[List[str]] = None,
    min_experience: Optional[float] = None,
    job_description: Optional[str] = None,
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

        # 🚨 STEP 3 EARLY TERMINATION: Invalid documents must stop immediately!
        # Do NOT audit GitHub. Do NOT run LLMs. Do NOT run consensus scoring.
        if not claims.is_valid_resume:
            elapsed = round(time.time() - start_time, 2)
            evidence = GitHubEvidence(
                username="none",
                profile_found=False,
                total_public_repos=0,
                original_repos_count=0,
                forked_repos_count=0,
                total_stars=0,
                languages_detected={},
                documentation_ratio=0.0,
                recent_activity_count=0,
                audit_notes=["Screening halted: Document validation failed."]
            )

            # Create clean 0/REJECT scorecard without calling consensus or LLMs
            from ..agent_3_evaluator import ScreeningScorecard
            scorecard = ScreeningScorecard(
                candidate_name=claims.name,
                github_username="none",
                target_role=job_title,
                company_required_skills=required_skills or [],
                matched_company_skills=[],
                verified_company_skills=[],
                missing_company_skills=required_skills or [],
                company_skills_match_score=0 if required_skills else None,
                overall_score=0,
                skills_match_score=0,
                code_quality_score=0,
                consistency_score=0,
                recommendation="REJECT",
                executive_summary=(
                    f"Screening HALTED: The uploaded file for '{claims.name}' does not appear to be a professional resume/CV "
                    f"(detected: {claims.document_type}). Verified 0 candidate claims. "
                    "Overall score: 0/100 REJECT. Please request submission of a valid resume."
                ),
                red_flags=[
                    "CRITICAL: Uploaded document is NOT a valid professional resume/CV.",
                    f"Document classified as: {claims.document_type} (e.g. academic lab, exercise, or unrelated document)."
                ] + claims.validation_flags,
                green_flags=[],
                topic_interview_questions=[]
            )

            # Persist minimal rejected record to DB so recruiter sees the audit entry
            candidate = Candidate(
                organization_id=organization_id,
                name=claims.name,
                email=claims.email or candidate_email_override,
                github_username="none",
                linkedin_url=linkedin_url_override,
                years_experience=0.0,
                tags=[]
            )
            db.add(candidate)
            await db.flush()

            resume = Resume(
                organization_id=organization_id,
                candidate_id=candidate.id,
                filename=filename,
                file_size_bytes=len(file_bytes),
                mime_type="application/pdf",
                file_hash=file_hash,
                raw_text=f"Invalid Document ({claims.document_type}). Parsed {claims.raw_text_length} chars."
            )
            db.add(resume)
            await db.flush()

            application = Application(
                organization_id=organization_id,
                candidate_id=candidate.id,
                job_title=job_title,
                source=source,
                status="reject"
            )
            db.add(application)
            await db.flush()

            audit = Audit(
                organization_id=organization_id,
                application_id=application.id,
                candidate_id=candidate.id,
                overall_score=0,
                skills_match_score=0,
                code_quality_score=0,
                consistency_score=0,
                ai_recommendation="REJECT",
                confidence_level="HIGH",
                needs_manual_review=False,
                variance_points=0,
                executive_summary=scorecard.executive_summary,
                latency_seconds=elapsed
            )
            db.add(audit)
            await db.flush()

            for rf in scorecard.red_flags:
                db.add(AuditFlag(audit_id=audit.id, flag_type="red", message=rf, severity="critical"))

            db.add(ModelEvaluation(
                audit_id=audit.id,
                model_name="Validation Gate",
                score=0,
                raw_output_json={"status": "rejected", "document_type": claims.document_type}
            ))

            # Resubmission notice (NEVER interview invitation!)
            subject = f"Action Required: Resume Resubmission for {job_title} at {company_name}"
            body_text = (
                f"Dear Applicant,\n\n"
                f"Thank you for your interest in the {job_title} position at {company_name}.\n\n"
                f"Our automated screening system was unable to evaluate your application because the submitted file does not appear to be a standard resume or CV (detected: {claims.document_type}).\n\n"
                f"Please reply with your updated professional resume PDF containing your work experience and technical projects so our engineering team can review your qualifications.\n\n"
                f"Best regards,\nTalent Acquisition Team\n{company_name}"
            )
            reply = GeneratedReply(
                organization_id=organization_id,
                audit_id=audit.id,
                candidate_id=candidate.id,
                recipient_name=claims.name,
                recipient_email=claims.email or candidate_email_override or "candidate@example.com",
                subject=subject,
                body_text=body_text,
                reply_type="resubmission_request",
                status="draft",
                calendly_link=calendly_link
            )
            db.add(reply)

            org.monthly_resumes_used += 1
            db.add(AuditLog(
                organization_id=organization_id,
                actor_id=actor_id,
                action="screen_candidate",
                target_type="audit",
                target_id=str(audit.id),
                details_json={
                    "candidate_name": claims.name,
                    "score": 0,
                    "recommendation": "REJECT",
                    "document_type": claims.document_type
                }
            ))

            from src.db.models import PipelineStage
            pipeline_stage = PipelineStage(
                organization_id=organization_id,
                application_id=application.id,
                candidate_id=candidate.id,
                stage="rejected",
                notes=f"Auto-rejected by Document Validation Gate ({claims.document_type})"
            )
            db.add(pipeline_stage)

            await db.commit()

            return {
                "id": str(audit.id),
                "audit_id": str(audit.id),
                "candidate_id": str(candidate.id),
                "application_id": str(application.id),
                "candidate_name": claims.name,
                "candidate_email": claims.email or candidate_email_override,
                "github_username": "none",
                "years_experience": 0.0,
                "is_valid_resume": False,
                "document_type": claims.document_type,
                "validation_flags": claims.validation_flags,
                "overall_score": 0,
                "recommendation": "REJECT",
                "skills_match_score": 0,
                "code_quality_score": 0,
                "consistency_score": 0,
                "target_role": job_title,
                "job_description": job_description,
                "company_required_skills": required_skills or [],
                "matched_company_skills": [],
                "verified_company_skills": [],
                "missing_company_skills": required_skills or [],
                "company_skills_match_score": 0 if required_skills else None,
                "linkedin_url": linkedin_url_override,
                "confidence_level": "HIGH",
                "needs_manual_review": False,
                "variance_points": 0,
                "executive_summary": scorecard.executive_summary,
                "red_flags": scorecard.red_flags,
                "green_flags": [],
                "topic_interview_questions": [],
                "consensus_notes": [f"Validation Gate Halted: Document classified as {claims.document_type}."],
                "model_votes": {"Validation Gate": 0},
                "claims": claims.model_dump(),
                "evidence": evidence.model_dump(),
                "draft_reply": {
                    "id": str(reply.id),
                    "subject": reply.subject,
                    "body_text": reply.body_text,
                    "reply_type": reply.reply_type,
                    "status": reply.status
                },
                "candidate": {
                    "name": claims.name,
                    "email": claims.email or candidate_email_override
                },
                "document": {
                    "is_valid_resume": False,
                    "document_type": claims.document_type
                },
                "scorecard": {
                    "overall_score": 0,
                    "recommendation": "REJECT",
                    "skills_match_score": 0,
                    "code_quality_score": 0,
                    "consistency_score": 0
                },
                "cached": False,
                "latency_seconds": elapsed,
                "screened_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        # Resolve GitHub target username (do not fallback to octocat!)
        target_github = (github_user_override or claims.github_username or "").strip()

        # 4. Audit GitHub Evidence (with smart caching)
        if target_github and target_github.lower() not in ("none", "null", "undefined"):
            github_cache = smart_cache.get("github", target_github)
            if github_cache:
                evidence = GitHubEvidence(**github_cache)
            else:
                evidence = audit_github(target_github)
                smart_cache.set("github", target_github, evidence.model_dump())
        else:
            evidence = audit_github("")
            target_github = "none"

        # 5. Consensus Multi-Agent Evaluation
        consensus = run_consensus_evaluation(
            claims,
            evidence,
            required_skills=required_skills,
            target_role=job_title,
            min_experience=min_experience
        )

        # 🚨 FINAL REINFORCED GATE: Ensure invalid documents ALWAYS score 0 and REJECT
        if not getattr(claims, "is_valid_resume", True):
            consensus.scorecard.overall_score = 0
            consensus.scorecard.skills_match_score = 0
            consensus.scorecard.code_quality_score = 0
            consensus.scorecard.consistency_score = 0
            consensus.scorecard.company_skills_match_score = 0 if required_skills else None
            consensus.scorecard.recommendation = "REJECT"
            if not any("NOT a valid" in f for f in consensus.scorecard.red_flags):
                consensus.scorecard.red_flags.insert(0, "CRITICAL: Uploaded document is NOT a valid professional resume/CV.")
            consensus.model_votes = {k: 0 for k in consensus.model_votes}

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
        if not getattr(claims, "is_valid_resume", True):
            subject = f"Action Required: Resume Resubmission for {job_title} at {company_name}"
            body_text = (
                f"Dear Applicant,\n\n"
                f"Thank you for your interest in the {job_title} position at {company_name}.\n\n"
                f"Our automated screening system was unable to evaluate your application because the submitted file does not appear to be a standard resume or CV (detected coursework, assignment sheet, or unformatted text).\n\n"
                f"Please reply with your updated resume PDF containing your work experience and technical projects so our engineering team can review your qualifications.\n\n"
                f"Best regards,\nTalent Acquisition Team\n{company_name}"
            )
            reply_type = "resubmission_request"
        elif consensus.scorecard.recommendation == "SHORTLIST":
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
            "is_valid_resume": getattr(claims, "is_valid_resume", True),
            "document_type": getattr(claims, "document_type", "RESUME"),
            "validation_flags": getattr(claims, "validation_flags", []),
            "overall_score": consensus.scorecard.overall_score,
            "recommendation": consensus.scorecard.recommendation,
            "skills_match_score": consensus.scorecard.skills_match_score,
            "code_quality_score": consensus.scorecard.code_quality_score,
            "consistency_score": consensus.scorecard.consistency_score,
            "target_role": consensus.scorecard.target_role or job_title,
            "job_description": job_description,
            "company_required_skills": consensus.scorecard.company_required_skills,
            "matched_company_skills": consensus.scorecard.matched_company_skills,
            "verified_company_skills": consensus.scorecard.verified_company_skills,
            "missing_company_skills": consensus.scorecard.missing_company_skills,
            "company_skills_match_score": consensus.scorecard.company_skills_match_score,
            "linkedin_url": linkedin_url_override or (candidate.linkedin_url if candidate else None),
            "confidence_level": consensus.confidence_level,
            "needs_manual_review": consensus.needs_manual_review,
            "variance_points": consensus.variance_points,
            "executive_summary": consensus.scorecard.executive_summary,
            "red_flags": consensus.scorecard.red_flags,
            "green_flags": consensus.scorecard.green_flags,
            "topic_interview_questions": [q.model_dump() for q in getattr(consensus.scorecard, "topic_interview_questions", [])],
            "consensus_notes": consensus.consensus_notes,
            "model_votes": consensus.model_votes,
            "claims": claims.model_dump(),
            "evidence": evidence.model_dump(),
            "candidate": {
                "name": claims.name,
                "email": claims.email or candidate_email_override
            },
            "document": {
                "is_valid_resume": True,
                "document_type": getattr(claims, "document_type", "RESUME")
            },
            "scorecard": {
                "overall_score": consensus.scorecard.overall_score,
                "recommendation": consensus.scorecard.recommendation,
                "skills_match_score": consensus.scorecard.skills_match_score,
                "code_quality_score": consensus.scorecard.code_quality_score,
                "consistency_score": consensus.scorecard.consistency_score
            },
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
