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
from ..agent_3_evaluator import ScreeningScorecard
from ..consensus_evaluator import run_consensus_evaluation
from ..smart_cache import smart_cache

def build_claim_evidence_items(
    claims: CandidateClaims,
    evidence: GitHubEvidence,
    required_skills: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Builds a recruiter-friendly Claim vs Evidence list with statuses: Verified, Partially Verified, Unverified, Unavailable."""
    items = []
    seen = set()
    all_skills = []

    if required_skills:
        for s in required_skills:
            s_clean = s.strip()
            if s_clean and s_clean.lower() not in seen:
                all_skills.append((s_clean, True))
                seen.add(s_clean.lower())

    for l in (claims.claimed_languages or []):
        if l and l.strip() and l.strip().lower() not in seen:
            all_skills.append((l.strip(), False))
            seen.add(l.strip().lower())

    for f in (claims.claimed_frameworks or []):
        if f and f.strip() and f.strip().lower() not in seen:
            all_skills.append((f.strip(), False))
            seen.add(f.strip().lower())

    github_available = bool(evidence.profile_found and evidence.username not in ("none", "", "null", "undefined"))
    detected_langs = {k.lower(): count for k, count in (evidence.languages_detected or {}).items()}

    for skill, is_req in all_skills:
        sk_lower = skill.lower()
        if not github_available:
            status = "Unavailable"
            details = "GitHub profile unavailable; evaluated on resume claims alone"
        else:
            if sk_lower in detected_langs:
                repo_cnt = detected_langs[sk_lower]
                status = "Verified"
                details = f"Verified across {repo_cnt} public repository codebase(s)"
            else:
                found_in_repos = False
                for r in (evidence.repo_highlights or []):
                    desc = (r.description or "").lower()
                    rname = (r.name or "").lower()
                    rlang = (r.language or "").lower()
                    if sk_lower in desc or sk_lower in rname or sk_lower == rlang:
                        found_in_repos = True
                        break
                if found_in_repos:
                    status = "Verified"
                    details = "Code or configuration found in public repository"
                elif is_req and sk_lower not in [c.lower() for c in ((claims.claimed_languages or []) + (claims.claimed_frameworks or []))]:
                    status = "Unverified"
                    details = "Missing: Absent from both resume claims and public code"
                else:
                    status = "Unverified"
                    details = "Mentioned in resume, but no supporting public code evidence found"
        notes_text = "Verified in public code" if status == "Verified" else ("Mentioned on resume, no code found in repos" if status == "Unverified" else "GitHub profile unavailable")
        items.append({
            "skill": skill,
            "skill_or_claim": skill,
            "claimed_in": "Job Requirement" if is_req else "Candidate Resume",
            "evidence": details,
            "evidence_found": details,
            "status": status,
            "notes": notes_text,
            "is_required": is_req
        })

    return items


def build_recruiter_assessment(
    scorecard: Any,
    claims: CandidateClaims,
    evidence: GitHubEvidence,
    is_valid: bool = True,
    required_skills: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Constructs a clean recruiter assessment object with standard sub-scores and actionable recommendation."""
    if not is_valid:
        return {
            "overall_score": 0,
            "recommendation": "INVALID_DOCUMENT",
            "skills_match": 0,
            "experience": 0,
            "projects": 0,
            "technical_evidence": 0,
            "resume_quality": 0,
            "next_action": "REQUEST_RESUME",
            "next_action_label": "Request a valid resume"
        }

    overall = scorecard.overall_score
    rec_raw = (getattr(scorecard, "recommendation", "") or "").upper()
    if rec_raw == "SHORTLIST" or overall >= 80:
        recommendation = "STRONG_CANDIDATE"
        next_action = "SCHEDULE_INTERVIEW"
        next_action_label = "Proceed to technical interview"
    elif rec_raw == "REVIEW" or overall >= 40:
        recommendation = "REVIEW"
        next_action = "REVIEW_RECOMMENDED"
        next_action_label = "Recruiter review recommended"
    else:
        recommendation = "REJECT"
        next_action = "DO_NOT_PROCEED"
        next_action_label = "Do not proceed"

    skills_match = scorecard.skills_match_score or overall
    exp_years = claims.years_experience or 1.0
    exp_score = min(98, max(40, int(exp_years * 20))) if exp_years <= 5 else min(98, 80 + int(exp_years * 2))
    projects_score = scorecard.code_quality_score or overall
    tech_ev_score = min(98, max(25, int((evidence.documentation_ratio or 0.5) * 50 + min(48, (evidence.total_public_repos or 1) * 5)))) if evidence.profile_found else min(overall, 65)
    resume_quality = scorecard.consistency_score or overall

    return {
        "overall_score": overall,
        "recommendation": recommendation,
        "skills_match": skills_match,
        "experience": exp_score,
        "projects": projects_score,
        "technical_evidence": tech_ev_score,
        "resume_quality": resume_quality,
        "next_action": next_action,
        "next_action_label": next_action_label
    }


def build_why_score(
    scorecard: Any,
    claims: CandidateClaims,
    evidence: GitHubEvidence,
    is_valid: bool = True
) -> Dict[str, Any]:
    """Generates an explainable 'Why [Score]?' breakdown with bulleted strengths and areas to verify."""
    if not is_valid:
        return {
            "score": 0,
            "reasons": [],
            "areas_to_verify": [
                "Uploaded document failed validation checks.",
                f"Classified as: {getattr(claims, 'document_type', 'ACADEMIC_LAB_OR_EXERCISE')}.",
                "Document lacks professional work experience or technical projects."
            ]
        }

    reasons = []
    for g in (scorecard.green_flags or []):
        reasons.append(f"✓ {g}")
    if not reasons:
        if claims.claimed_languages:
            reasons.append(f"✓ Strong proficiency demonstrated in {', '.join(claims.claimed_languages[:3])}")
        if claims.years_experience:
            reasons.append(f"✓ {claims.years_experience}+ years of relevant technical experience")
        if evidence.profile_found and evidence.original_repos_count > 0:
            reasons.append(f"✓ {evidence.original_repos_count} original public code repositories supporting claims")

    areas = []
    for r in (scorecard.red_flags or []):
        areas.append(f"• {r}")
    if not areas:
        areas.append("• Standard technical interview screening recommended")

    return {
        "score": scorecard.overall_score,
        "reasons": reasons[:5],
        "areas_to_verify": areas[:5]
    }


def execute_screening_pipeline_core(
    file_bytes: Optional[bytes] = None,
    file_path: Optional[str] = None,
    filename: str = "resume.pdf",
    file_name: Optional[str] = None,
    github_user_override: Optional[str] = None,
    candidate_name_override: Optional[str] = None,
    candidate_email_override: Optional[str] = None,
    linkedin_url_override: Optional[str] = None,
    job_title: Optional[str] = None,
    target_role: Optional[str] = None,
    required_skills: Optional[List[str]] = None,
    min_experience: Optional[float] = None,
    job_description: Optional[str] = None,
    company_name: str = "TechCorp Solutions",
    calendly_link: str = "https://calendly.com/techcorp-hiring/30min"
) -> Dict[str, Any]:
    """
    Unified Single Screening Orchestration (Single Source of Truth):
    1. Validates file security (magic bytes).
    2. Parses text and runs multi-signal document classification.
    3. Binary validity decision:
       - If INVALID: Halts immediately in <0.05s. Skips GitHub, skips LLM consensus,
         forces score 0, recommendation REJECT / INVALID_DOCUMENT, next_action REQUEST_RESUME.
       - If VALID: Audits GitHub profile (no fake repos/users), evaluates multi-agent consensus,
         enforces final safety gate, generates 5 sub-scores, why-score breakdown, claim vs evidence,
         and tailored human-in-the-loop email drafts.
    """
    start_time = time.time()
    tmp_path = None
    role = target_role or job_title or "Software Engineer"
    filename = file_name or filename

    try:
        # 1. Resolve bytes or file path
        if file_bytes is None and file_path is not None:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

        if not file_bytes:
            elapsed = round(time.time() - start_time, 2)
            claims = CandidateClaims(
                name=candidate_name_override or "Corrupt / Empty Document",
                email=candidate_email_override,
                github_username=None,
                years_experience=0.0,
                claimed_languages=[],
                claimed_frameworks=[],
                claimed_tools=[],
                key_claims=[],
                raw_text_length=0,
                is_valid_resume=False,
                document_type="EMPTY_OR_WHITESPACE_ONLY",
                validation_flags=["File is empty or 0 bytes."]
            )
        elif not file_bytes.startswith(b"%PDF-"):
            elapsed = round(time.time() - start_time, 2)
            claims = CandidateClaims(
                name=candidate_name_override or "Non-PDF File",
                email=candidate_email_override,
                github_username=None,
                years_experience=0.0,
                claimed_languages=[],
                claimed_frameworks=[],
                claimed_tools=[],
                key_claims=[],
                raw_text_length=len(file_bytes),
                is_valid_resume=False,
                document_type="CORRUPT_OR_UNREADABLE_FILE",
                validation_flags=["File does not start with valid %PDF- magic bytes."]
            )
        else:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            claims = parse_resume(tmp_path)

        if candidate_name_override and claims.is_valid_resume:
            claims.name = candidate_name_override
        if candidate_email_override and claims.is_valid_resume:
            claims.email = candidate_email_override
        if linkedin_url_override and not claims.key_claims:
            claims.key_claims.append(f"LinkedIn: {linkedin_url_override}")

        # 🚨 P0 EARLY TERMINATION GATE: Invalid documents halt immediately!
        # Zero GitHub audit. Zero LLM consensus. Zero candidate-quality score.
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
                audit_notes=["Screening halted: Document validation failed. No code audit conducted."]
            )
            scorecard = ScreeningScorecard(
                candidate_name=claims.name,
                github_username="none",
                target_role=role,
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
            recruiter_assessment = build_recruiter_assessment(scorecard, claims, evidence, is_valid=False, required_skills=required_skills)
            why_score_data = build_why_score(scorecard, claims, evidence, is_valid=False)

            from ..email_connector import DraftResponseGenerator
            draft_obj = DraftResponseGenerator.create_draft(
                candidate_name=claims.name,
                recipient_email=claims.email or candidate_email_override or "candidate@example.com",
                verdict="REJECT",
                company_name=company_name,
                role_title=role,
                calendly_link=calendly_link,
                score=0
            )
            draft_reply_data = {
                "subject": draft_obj.subject,
                "body_text": draft_obj.body_text,
                "reply_type": "resubmission_request",
                "status": "draft"
            }

            return {
                "is_valid_resume": False,
                "overall_score": 0,
                "recommendation": "REJECT",
                "recruiter_recommendation": "INVALID_DOCUMENT",
                "status_label": "Invalid Document",
                "document_type": claims.document_type,
                "validation_flags": claims.validation_flags,
                "next_action": "REQUEST_RESUME",
                "next_action_label": "Request a valid resume",
                "skills_match_score": 0,
                "code_quality_score": 0,
                "consistency_score": 0,
                "company_skills_match_score": 0 if required_skills else None,
                "candidate_name": claims.name,
                "candidate_email": claims.email or candidate_email_override,
                "github_username": "none",
                "years_experience": 0.0,
                "target_role": job_title,
                "job_description": job_description,
                "company_required_skills": required_skills or [],
                "matched_company_skills": [],
                "verified_company_skills": [],
                "missing_company_skills": required_skills or [],
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
                "assessment": recruiter_assessment,
                "why_score": why_score_data,
                "evidence_items": [],
                "strengths": [],
                "weaknesses": scorecard.red_flags,
                "draft_reply_data": draft_reply_data,
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
                "scorecard_obj": scorecard,
                "claims_obj": claims,
                "evidence_obj": evidence,
                "latency_seconds": elapsed,
                "cached": False
            }

        # If valid resume:
        # 4. Audit GitHub Evidence
        target_github = (github_user_override or claims.github_username or "").strip()
        if target_github and target_github.lower() not in ("none", "null", "undefined", "unknown", "n/a"):
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
            target_role=role,
            min_experience=min_experience
        )

        # 🚨 FINAL REINFORCED GATE: Ensure invalid documents NEVER score points
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
        scorecard = consensus.scorecard

        recruiter_assessment = build_recruiter_assessment(scorecard, claims, evidence, is_valid=True, required_skills=required_skills)
        why_score_data = build_why_score(scorecard, claims, evidence, is_valid=True)
        evidence_data = build_claim_evidence_items(claims, evidence, required_skills=required_skills)

        # Draft reply based on verdict
        if scorecard.recommendation == "SHORTLIST":
            subject = f"Interview Invitation: {role} at {company_name}"
            body_text = (
                f"Hi {claims.name},\n\n"
                f"We were very impressed by your background and public engineering work, particularly your verified projects on GitHub (@{target_github}). "
                f"We would love to invite you for a 30-minute introductory technical interview.\n\n"
                f"Please select a convenient time on our calendar here: {calendly_link}\n\n"
                f"Best regards,\nRecruitment Team\n{company_name}"
            )
            reply_type = "interview_invite"
        elif scorecard.recommendation == "REJECT":
            subject = f"Application Update: {role} at {company_name}"
            body_text = (
                f"Dear {claims.name},\n\n"
                f"Thank you for taking the time to apply for the {role} position at {company_name}. "
                f"While your experience is appreciated, we have decided not to move forward with your application at this time based on our specific project requirements.\n\n"
                f"We wish you every success in your ongoing job search.\n\n"
                f"Sincerely,\nTalent Acquisition Team\n{company_name}"
            )
            reply_type = "rejection"
        else:
            subject = f"Additional Information Request: {role} at {company_name}"
            body_text = (
                f"Hi {claims.name},\n\n"
                f"Thank you for your application for the {role} role at {company_name}. "
                f"Our engineering team is currently reviewing your profile. To help us best evaluate your technical experience, "
                f"could you share any additional repositories or architecture demos that demonstrate your experience with "
                f"{', '.join(claims.claimed_languages[:2]) or 'software architecture'}?\n\n"
                f"Best regards,\nRecruitment Team\n{company_name}"
            )
            reply_type = "info_request"

        draft_reply_data = {
            "subject": subject,
            "body_text": body_text,
            "reply_type": reply_type,
            "status": "draft"
        }

        return {
            "is_valid_resume": True,
            "overall_score": scorecard.overall_score,
            "recommendation": scorecard.recommendation,
            "recruiter_recommendation": recruiter_assessment["recommendation"],
            "status_label": "Strong Candidate" if recruiter_assessment["recommendation"] == "STRONG_CANDIDATE" else ("Needs Review" if recruiter_assessment["recommendation"] == "REVIEW" else "Not Recommended"),
            "document_type": getattr(claims, "document_type", "RESUME"),
            "validation_flags": getattr(claims, "validation_flags", []),
            "next_action": recruiter_assessment["next_action"],
            "next_action_label": recruiter_assessment["next_action_label"],
            "skills_match_score": scorecard.skills_match_score,
            "code_quality_score": scorecard.code_quality_score,
            "consistency_score": scorecard.consistency_score,
            "company_skills_match_score": scorecard.company_skills_match_score,
            "candidate_name": claims.name,
            "candidate_email": claims.email or candidate_email_override,
            "github_username": target_github,
            "years_experience": claims.years_experience,
            "target_role": scorecard.target_role or job_title,
            "job_description": job_description,
            "company_required_skills": scorecard.company_required_skills,
            "matched_company_skills": scorecard.matched_company_skills,
            "verified_company_skills": scorecard.verified_company_skills,
            "missing_company_skills": scorecard.missing_company_skills,
            "linkedin_url": linkedin_url_override,
            "confidence_level": consensus.confidence_level,
            "needs_manual_review": consensus.needs_manual_review,
            "variance_points": consensus.variance_points,
            "executive_summary": scorecard.executive_summary,
            "red_flags": scorecard.red_flags,
            "green_flags": scorecard.green_flags,
            "topic_interview_questions": [q.model_dump() for q in getattr(scorecard, "topic_interview_questions", [])],
            "consensus_notes": consensus.consensus_notes,
            "model_votes": consensus.model_votes,
            "claims": claims.model_dump(),
            "evidence": evidence.model_dump(),
            "assessment": recruiter_assessment,
            "why_score": why_score_data,
            "evidence_items": evidence_data,
            "strengths": scorecard.green_flags,
            "weaknesses": scorecard.red_flags,
            "draft_reply_data": draft_reply_data,
            "candidate": {
                "name": claims.name,
                "email": claims.email or candidate_email_override
            },
            "document": {
                "is_valid_resume": True,
                "document_type": getattr(claims, "document_type", "RESUME")
            },
            "scorecard": {
                "overall_score": scorecard.overall_score,
                "recommendation": scorecard.recommendation,
                "skills_match_score": scorecard.skills_match_score,
                "code_quality_score": scorecard.code_quality_score,
                "consistency_score": scorecard.consistency_score
            },
            "scorecard_obj": scorecard,
            "claims_obj": claims,
            "evidence_obj": evidence,
            "consensus_obj": consensus,
            "latency_seconds": elapsed,
            "cached": False
        }

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# Single screening orchestration alias
screen_resume_orchestrated = execute_screening_pipeline_core


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
    Core database-integrated screening service:
    1. Enforces organization quota check.
    2. Executes unified single screening pipeline (single source of truth).
    3. Persists Candidate, Resume, Claims, GitHubProfile, Application, Audit, Flags, ModelEvaluations, and Reply to DB.
    4. Increments tenant quota and writes AuditLog.
    """
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

    # 2. File hash computation
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # 3. Unified screening execution
    res = execute_screening_pipeline_core(
        file_bytes=file_bytes,
        filename=filename,
        github_user_override=github_user_override,
        candidate_name_override=candidate_name_override,
        candidate_email_override=candidate_email_override,
        linkedin_url_override=linkedin_url_override,
        job_title=job_title,
        required_skills=required_skills,
        min_experience=min_experience,
        job_description=job_description,
        company_name=company_name,
        calendly_link=calendly_link
    )

    claims_obj: CandidateClaims = res["claims_obj"]
    evidence_obj: GitHubEvidence = res["evidence_obj"]
    scorecard_obj: ScreeningScorecard = res["scorecard_obj"]
    draft_info: Dict[str, Any] = res["draft_reply_data"]

    # 4. Database Persistence
    if not res["is_valid_resume"]:
        # Persist minimal rejected record to DB so recruiter sees the audit entry
        candidate = Candidate(
            organization_id=organization_id,
            name=res["candidate_name"],
            email=res["candidate_email"],
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
            raw_text=f"Invalid Document ({res['document_type']}). Parsed {claims_obj.raw_text_length} chars."
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
            executive_summary=scorecard_obj.executive_summary,
            latency_seconds=res["latency_seconds"]
        )
        db.add(audit)
        await db.flush()

        for rf in scorecard_obj.red_flags:
            db.add(AuditFlag(audit_id=audit.id, flag_type="red", message=rf, severity="critical"))

        db.add(ModelEvaluation(
            audit_id=audit.id,
            model_name="Validation Gate",
            score=0,
            raw_output_json={"status": "rejected", "document_type": res["document_type"]}
        ))

        reply = GeneratedReply(
            organization_id=organization_id,
            audit_id=audit.id,
            candidate_id=candidate.id,
            recipient_name=res["candidate_name"],
            recipient_email=res["candidate_email"] or "candidate@example.com",
            subject=draft_info["subject"],
            body_text=draft_info["body_text"],
            reply_type=draft_info["reply_type"],
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
                "candidate_name": res["candidate_name"],
                "score": 0,
                "recommendation": "REJECT",
                "document_type": res["document_type"]
            }
        ))

        from src.db.models import PipelineStage
        pipeline_stage = PipelineStage(
            organization_id=organization_id,
            application_id=application.id,
            candidate_id=candidate.id,
            stage="rejected",
            notes=f"Auto-rejected by Document Validation Gate ({res['document_type']})"
        )
        db.add(pipeline_stage)

        await db.commit()

    else:
        # Valid Resume Persistence
        candidate = None
        if claims_obj.email:
            cand_stmt = select(Candidate).where(
                Candidate.organization_id == organization_id,
                Candidate.email == claims_obj.email
            )
            c_res = await db.execute(cand_stmt)
            candidate = c_res.scalar_one_or_none()

        if not candidate:
            candidate = Candidate(
                organization_id=organization_id,
                name=claims_obj.name,
                email=claims_obj.email or candidate_email_override,
                github_username=res["github_username"],
                linkedin_url=linkedin_url_override or claims_obj.github_url,
                years_experience=claims_obj.years_experience or 1.0,
                tags=claims_obj.claimed_languages[:5]
            )
            db.add(candidate)
            await db.flush()
        else:
            if not candidate.github_username:
                candidate.github_username = res["github_username"]

        resume = Resume(
            organization_id=organization_id,
            candidate_id=candidate.id,
            filename=filename,
            file_size_bytes=len(file_bytes),
            mime_type="application/pdf",
            file_hash=file_hash,
            raw_text=f"Parsed {claims_obj.raw_text_length} chars. Name: {claims_obj.name}"
        )
        db.add(resume)
        await db.flush()

        for lang in claims_obj.claimed_languages:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="language", claim_text=lang))
        for fw in claims_obj.claimed_frameworks:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="framework", claim_text=fw))
        for tool in claims_obj.claimed_tools:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="tool", claim_text=tool))
        for claim in claims_obj.key_claims:
            db.add(ResumeClaim(resume_id=resume.id, claim_type="project_impact", claim_text=claim))

        gh_stmt = select(GitHubProfile).where(GitHubProfile.candidate_id == candidate.id)
        gh_res = await db.execute(gh_stmt)
        gh_profile = gh_res.scalar_one_or_none()
        if not gh_profile:
            gh_profile = GitHubProfile(
                candidate_id=candidate.id,
                username=res["github_username"],
                profile_found=evidence_obj.profile_found,
                total_public_repos=evidence_obj.total_public_repos,
                original_repos_count=evidence_obj.original_repos_count,
                forked_repos_count=evidence_obj.forked_repos_count,
                total_stars=evidence_obj.total_stars,
                documentation_ratio=evidence_obj.documentation_ratio,
                recent_activity_count=evidence_obj.recent_activity_count,
                languages_json=evidence_obj.languages_detected,
                raw_json=evidence_obj.model_dump()
            )
            db.add(gh_profile)
        else:
            gh_profile.total_public_repos = evidence_obj.total_public_repos
            gh_profile.original_repos_count = evidence_obj.original_repos_count
            gh_profile.forked_repos_count = evidence_obj.forked_repos_count
            gh_profile.total_stars = evidence_obj.total_stars
            gh_profile.documentation_ratio = evidence_obj.documentation_ratio
            gh_profile.recent_activity_count = evidence_obj.recent_activity_count
            gh_profile.languages_json = evidence_obj.languages_detected
            gh_profile.raw_json = evidence_obj.model_dump()

        application = Application(
            organization_id=organization_id,
            candidate_id=candidate.id,
            job_title=job_title,
            source=source,
            status=scorecard_obj.recommendation.lower()
        )
        db.add(application)
        await db.flush()

        audit = Audit(
            organization_id=organization_id,
            application_id=application.id,
            candidate_id=candidate.id,
            overall_score=scorecard_obj.overall_score,
            skills_match_score=scorecard_obj.skills_match_score,
            code_quality_score=scorecard_obj.code_quality_score,
            consistency_score=scorecard_obj.consistency_score,
            ai_recommendation=scorecard_obj.recommendation,
            confidence_level=res["confidence_level"],
            needs_manual_review=res["needs_manual_review"],
            variance_points=res["variance_points"],
            executive_summary=scorecard_obj.executive_summary,
            latency_seconds=res["latency_seconds"]
        )
        db.add(audit)
        await db.flush()

        for red_flag in scorecard_obj.red_flags:
            severity = "critical" if ("0 public" in red_flag or "could not be verified" in red_flag) else "normal"
            db.add(AuditFlag(audit_id=audit.id, flag_type="red", message=red_flag, severity=severity))
        for green_flag in scorecard_obj.green_flags:
            db.add(AuditFlag(audit_id=audit.id, flag_type="green", message=green_flag, severity="normal"))

        for m_name, vote in res["model_votes"].items():
            score_val = vote if isinstance(vote, int) else (vote.get("score", scorecard_obj.overall_score) if isinstance(vote, dict) else scorecard_obj.overall_score)
            raw_json = {"score": score_val} if isinstance(vote, int) else (vote if isinstance(vote, dict) else {})
            db.add(ModelEvaluation(
                audit_id=audit.id,
                model_name=m_name,
                score=score_val,
                raw_output_json=raw_json
            ))

        reply = GeneratedReply(
            organization_id=organization_id,
            audit_id=audit.id,
            candidate_id=candidate.id,
            recipient_name=res["candidate_name"],
            recipient_email=res["candidate_email"] or "candidate@example.com",
            subject=draft_info["subject"],
            body_text=draft_info["body_text"],
            reply_type=draft_info["reply_type"],
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
                "candidate_name": res["candidate_name"],
                "score": scorecard_obj.overall_score,
                "recommendation": scorecard_obj.recommendation
            }
        ))

        from src.db.models import PipelineStage
        init_stage = "shortlist" if scorecard_obj.recommendation == "SHORTLIST" else ("review" if scorecard_obj.recommendation == "REVIEW" else "ai_screened")
        pipeline_stage = PipelineStage(
            organization_id=organization_id,
            application_id=application.id,
            candidate_id=candidate.id,
            stage=init_stage,
            notes=f"Auto-transitioned from AI consensus score {scorecard_obj.overall_score}/100 ({scorecard_obj.recommendation})"
        )
        db.add(pipeline_stage)

        await db.commit()

    # Enrich core result with persisted DB entity references
    res["success"] = True
    res["status"] = "completed"
    res["id"] = str(audit.id)
    res["audit_id"] = str(audit.id)
    res["candidate_id"] = str(candidate.id)
    res["application_id"] = str(application.id)
    res["draft_reply"] = {
        "id": str(reply.id),
        "subject": reply.subject,
        "body_text": reply.body_text,
        "reply_type": reply.reply_type,
        "status": reply.status
    }
    res["screened_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    return res
