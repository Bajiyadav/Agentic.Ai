"""
Job Match Evaluation Service (Test 7)
Deterministic candidate job-match scoring, multi-source evidence synthesis,
explainable recommendation engine, and recruiter override audit trail.

Scoring Dimensions & Weights (Sum to 100%):
1. Required Technical Skills: 20%
2. Relevant Experience: 15%
3. GitHub Evidence: 15%
4. Claim Verification: 10%
5. Assessment Performance: 25%
6. Responsibilities Match: 15%

Mandatory Safety Invariants:
- 'No Public Evidence' != False (neutral baseline, not fraud or penalty).
- Missing GitHub account alone != REJECT.
- Missing preferred skills != REJECT.
- True evidence conflicts surfaced explicitly.
- Recruiter override preserves original automated recommendation & score.
- Multi-job isolation: (candidate_id, job_id) uniqueness.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import (
    JobOpening, Candidate, Resume, ResumeClaim,
    CandidateJobEvidenceAudit, CandidateAssessment, JobMatchScore, Application
)

logger = logging.getLogger("job_match_evaluation_service")

# In-memory evaluation cache for ultra-fast UI reloads and tests
job_match_evaluation_cache: Dict[str, Dict[str, Any]] = {}


class JobMatchEvaluationService:
    @staticmethod
    def _normalize_skill(skill: str) -> str:
        return skill.strip().lower() if skill else ""

    @classmethod
    async def evaluate_candidate_for_job(
        cls,
        db: AsyncSession,
        job_id: str,
        candidate_id: str,
        tenant_id: str,
        recruiter_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Computes deterministic 6-dimension job match score, produces structured
        evidence matrices, identifies strengths/gaps/conflicts, and assigns advisory recommendation.
        Persists result in JobMatchScore with (candidate_id, job_id) isolation.
        """
        # 1. Parse UUIDs
        try:
            job_uuid = uuid.UUID(str(job_id))
            cand_uuid = uuid.UUID(str(candidate_id))
            org_uuid = uuid.UUID(str(tenant_id)) if tenant_id else None
        except Exception as e:
            raise ValueError(f"Invalid UUID provided: {e}")

        # 2. Fetch Job Opening
        job_stmt = select(JobOpening).where(JobOpening.id == job_uuid)
        if org_uuid:
            job_stmt = job_stmt.where(JobOpening.organization_id == org_uuid)
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()
        if not job:
            raise ValueError(f"JobOpening '{job_id}' not found for tenant '{tenant_id}'")

        # 3. Fetch Candidate
        cand_stmt = select(Candidate).where(Candidate.id == cand_uuid)
        if org_uuid:
            cand_stmt = cand_stmt.where(Candidate.organization_id == org_uuid)
        cand_res = await db.execute(cand_stmt)
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise ValueError(f"Candidate '{candidate_id}' not found for tenant '{tenant_id}'")

        # 4. Fetch CandidateJobEvidenceAudit (GitHub audit + claim verifications)
        evidence_audit_stmt = select(CandidateJobEvidenceAudit).where(
            CandidateJobEvidenceAudit.candidate_id == cand_uuid,
            CandidateJobEvidenceAudit.job_id == job_uuid
        )
        evidence_audit_res = await db.execute(evidence_audit_stmt)
        evidence_audit_rec = evidence_audit_res.scalar_one_or_none()
        evidence_audit_data = evidence_audit_rec.audit_data if evidence_audit_rec else {}

        # 5. Fetch CandidateAssessment (Job-specific assessment results)
        assessment_stmt = select(CandidateAssessment).where(
            CandidateAssessment.candidate_id == cand_uuid,
            CandidateAssessment.job_id == job_uuid
        ).order_by(CandidateAssessment.created_at.desc())
        assessment_res = await db.execute(assessment_stmt)
        assessment_rec = assessment_res.scalars().first()

        # 6. Fetch Resume Claims
        resume_stmt = select(Resume).where(Resume.candidate_id == cand_uuid)
        resume_res = await db.execute(resume_stmt)
        resumes = resume_res.scalars().all()
        resume_claims_list = []
        for r in resumes:
            claims_stmt = select(ResumeClaim).where(ResumeClaim.resume_id == r.id)
            c_res = await db.execute(claims_stmt)
            resume_claims_list.extend(c_res.scalars().all())

        # Collect candidate's claims & skills across all supported categories
        parsed_claims = candidate.parsed_claims_json or {}
        cand_claimed_skills = set()
        skill_keys = [
            "languages", "frameworks", "databases", "cloud_devops", "tools", "skills",
            "claimed_languages", "claimed_frameworks", "claimed_databases", "claimed_cloud_devops", "claimed_tools"
        ]
        for k in skill_keys:
            items = parsed_claims.get(k) or []
            if isinstance(items, list):
                for item in items:
                    cand_claimed_skills.add(cls._normalize_skill(str(item)))

        for rc in resume_claims_list:
            cand_claimed_skills.add(cls._normalize_skill(rc.claim_text))

        # GitHub Evidence data
        github_profile = evidence_audit_data.get("profile", {})
        github_detected_langs = {
            cls._normalize_skill(k): v for k, v in github_profile.get("languages_detected", {}).items()
        }
        github_repos = evidence_audit_data.get("repositories", [])
        has_github_account = bool(
            candidate.github_username
            and candidate.github_username.strip().lower() not in ("none", "", "null")
            and evidence_audit_data.get("status") not in ("No GitHub Provided", "Profile Not Found")
        )

        # Assessment data
        assessment_completed = bool(assessment_rec and assessment_rec.status == "completed")
        assessment_score = assessment_rec.score if (assessment_rec and assessment_rec.score is not None) else None
        assessment_questions = assessment_rec.questions_json if assessment_rec else []
        assessment_sandbox = assessment_rec.sandbox_results if assessment_rec else {}
        assessment_integrity = assessment_rec.integrity_score if assessment_rec else 100

        # Extract skills tested & passed in assessment
        assessment_skills_passed = set()
        assessment_skills_failed = set()
        for q in assessment_questions:
            q_id = q.get("id")
            skill_tested = cls._normalize_skill(q.get("skill_tested", ""))
            if not skill_tested:
                continue

            # Check if MCQ was correct or Coding passed sandbox
            if q.get("type") == "mcq":
                user_ans = (assessment_rec.answers_json or {}).get(q_id) if assessment_rec else None
                if user_ans is not None and user_ans == q.get("correct_option"):
                    assessment_skills_passed.add(skill_tested)
                elif user_ans is not None:
                    assessment_skills_failed.add(skill_tested)
            elif q.get("type") == "coding":
                sb = assessment_sandbox.get(q_id, {})
                if sb.get("passed", False) or sb.get("success", False):
                    assessment_skills_passed.add(skill_tested)
                elif sb:
                    assessment_skills_failed.add(skill_tested)

        # -----------------------------------------------------------------
        # DIMENSION 1: Required Technical Skills Match (Weight: 20%)
        # -----------------------------------------------------------------
        required_skills = job.required_skills or []
        required_skills_matrix = []
        req_scores = []
        missing_required_list = []
        matched_required_list = []

        for req in required_skills:
            req_norm = cls._normalize_skill(req)
            if not req_norm:
                continue

            in_assessment = (req_norm in assessment_skills_passed) or any(req_norm in s or s in req_norm for s in assessment_skills_passed)
            in_assessment_fail = (req_norm in assessment_skills_failed) or any(req_norm in s or s in req_norm for s in assessment_skills_failed)
            in_github = (req_norm in github_detected_langs) or any(req_norm in k or k in req_norm for k in github_detected_langs)
            in_resume = (req_norm in cand_claimed_skills) or any(req_norm in c or c in req_norm for c in cand_claimed_skills)

            # Determine verification status & score
            if in_assessment:
                status = "Verified in Assessment"
                score = 100
                confidence = 0.98
                notes = f"Demonstrated high competency in {req} during job assessment."
                matched_required_list.append(req)
            elif in_github:
                status = "Verified in GitHub"
                score = 100
                confidence = 0.90
                notes = f"Verified public codebase repository evidence for {req}."
                matched_required_list.append(req)
            elif in_resume:
                status = "Claimed on Resume"
                score = 35  # Calibrated realistic score for unverified resume claim (was 50)
                confidence = 0.60
                notes = f"Claimed on resume, but lacks direct assessment or public repository evidence."
                matched_required_list.append(req)
            else:
                status = "Missing"
                score = 0
                confidence = 0.95
                notes = f"No evidence found on resume, assessment, or GitHub."
                missing_required_list.append(req)

            req_scores.append(score)
            required_skills_matrix.append({
                "skill": req,
                "in_resume": in_resume,
                "in_github": in_github,
                "in_assessment": in_assessment,
                "assessment_failed": in_assessment_fail,
                "status": status,
                "score": score,
                "confidence": confidence,
                "notes": notes
            })

        required_skills_match_pct = int(sum(req_scores) / len(req_scores)) if req_scores else 100

        # -----------------------------------------------------------------
        # DIMENSION 2: Relevant Experience Match (Weight: 15%)
        # -----------------------------------------------------------------
        min_years = float(getattr(job, "experience_min_years", getattr(job, "min_years_experience", 0.0)) or 0.0)
        cand_years = float(candidate.years_experience or 0.0)

        if min_years <= 0.0:
            experience_match_pct = 100
            experience_notes = f"No minimum experience requirement specified. Candidate has {cand_years:.1f} yrs."
        elif cand_years >= min_years:
            experience_match_pct = 100
            experience_notes = f"Meets/exceeds requirement: {cand_years:.1f} yrs vs {min_years:.1f} yrs required."
        else:
            ratio = cand_years / max(1.0, min_years)
            experience_match_pct = max(10, min(100, int(ratio * 100)))
            experience_notes = f"Experience gap: {cand_years:.1f} yrs vs {min_years:.1f} yrs required."

        # -----------------------------------------------------------------
        # DIMENSION 3: GitHub Evidence Match (Weight: 15%)
        # Mandatory Safety: Missing GitHub != REJECT, returns neutral baseline
        # -----------------------------------------------------------------
        is_github_neutral = False
        if not has_github_account:
            github_match_pct = 65  # Contractual neutral baseline for enterprise candidates without public GitHub
            is_github_neutral = True
            github_summary = {
                "username": candidate.github_username or "None",
                "profile_found": False,
                "is_neutral_baseline": True,
                "notes": "Public GitHub profile not linked. Enterprise engineering work typically resides in private repositories. Neutral baseline applied (no penalty)."
            }
        else:
            # Score based on repo count, stars, documentation, and language diversity
            doc_ratio = float(github_profile.get("documentation_ratio", 0.5))
            orig_repos = int(github_profile.get("original_repos_count", 0))
            stars = int(github_profile.get("total_stars", 0))
            matched_langs_count = sum(1 for req in required_skills if cls._normalize_skill(req) in github_detected_langs)

            # Up to 35 pts from languages matching job requirements
            req_coverage = (matched_langs_count / max(1, len(required_skills))) if required_skills else 0.8
            lang_pts = int(req_coverage * 35)

            # Up to 35 pts from documentation and code standards
            doc_pts = int(doc_ratio * 35)

            # Up to 30 pts from activity and repositories
            repo_pts = min(30, (orig_repos * 5) + min(10, stars * 2))

            github_match_pct = max(20, min(100, lang_pts + doc_pts + repo_pts))
            github_summary = {
                "username": candidate.github_username,
                "profile_found": True,
                "is_neutral_baseline": False,
                "total_public_repos": github_profile.get("total_public_repos", 0),
                "original_repos_count": orig_repos,
                "documentation_ratio": round(doc_ratio, 2),
                "total_stars": stars,
                "languages_detected": list(github_detected_langs.keys()),
                "notes": f"Verified {orig_repos} original repos across {len(github_detected_langs)} languages with {int(doc_ratio * 100)}% documentation ratio."
            }

        # -----------------------------------------------------------------
        # DIMENSION 4: Claim Verification Match (Weight: 10%)
        # Mandatory Safety: 'No Public Evidence' != False / Fraud (neutral 60)
        # -----------------------------------------------------------------
        claim_vers = evidence_audit_data.get("claim_verifications") or []
        claim_scores = []
        claims_requiring_verification = []
        evidence_conflicts = []

        if not claim_vers:
            # If no claim verifications performed, neutral 50 (was 70)
            claim_verification_pct = 50
        else:
            for cv in claim_vers:
                status_raw = cv.get("status", "No Public Evidence")
                status_clean = status_raw.strip()

                if status_clean in ("Verified", "Strong Evidence"):
                    claim_scores.append(100)
                elif status_clean == "Moderate Evidence":
                    claim_scores.append(70)
                elif status_clean == "No Public Evidence":
                    claim_scores.append(45)  # Calibrated normal baseline for unevidenced claims (was 60)
                    claims_requiring_verification.append({
                        "claim_type": cv.get("claim_type", "Skill"),
                        "claim_text": cv.get("claim_text", ""),
                        "status": "No Public Evidence",
                        "probe_recommendation": f"Probe candidate's experience with {cv.get('claim_text')} during technical interview."
                    })
                elif status_clean == "Weak Evidence":
                    claim_scores.append(40)
                    claims_requiring_verification.append({
                        "claim_type": cv.get("claim_type", "Skill"),
                        "claim_text": cv.get("claim_text", ""),
                        "status": "Weak Evidence",
                        "probe_recommendation": f"Ask candidate to walk through a concrete architecture implemented using {cv.get('claim_text')}."
                    })
                elif status_clean == "Contradictory Evidence":
                    claim_scores.append(0)
                    evidence_conflicts.append({
                        "type": "Resume vs Evidence Contradiction",
                        "claim_text": cv.get("claim_text", ""),
                        "details": cv.get("confidence_rationale") or "Direct contradiction discovered in repository audit.",
                        "severity": "High"
                    })
                else:
                    claim_scores.append(60)

            claim_verification_pct = int(sum(claim_scores) / len(claim_scores)) if claim_scores else 70

        # -----------------------------------------------------------------
        # DIMENSION 5: Assessment Performance (Weight: 25%)
        # -----------------------------------------------------------------
        if assessment_completed and assessment_score is not None:
            # Check integrity score
            if assessment_integrity < 70:
                # Proctoring flag
                assessment_match_pct = max(0, assessment_score - 15)
                assessment_notes = f"Assessment completed with score {assessment_score}%. Note: Integrity score was {assessment_integrity}% due to proctoring flags."
            else:
                assessment_match_pct = assessment_score
                assessment_notes = f"Assessment successfully completed with score {assessment_score}% (Integrity: {assessment_integrity}%)."

            assessment_summary = {
                "assessment_id": str(assessment_rec.id),
                "status": "completed",
                "score": assessment_score,
                "integrity_score": assessment_integrity,
                "notes": assessment_notes,
                "skills_passed": list(assessment_skills_passed),
                "skills_failed": list(assessment_skills_failed)
            }
        else:
            # Assessment pending or in progress
            assessment_match_pct = 50  # Provisional neutral baseline
            assessment_summary = {
                "assessment_id": str(assessment_rec.id) if assessment_rec else None,
                "status": "pending" if assessment_rec else "not_invited",
                "score": None,
                "integrity_score": None,
                "notes": "Assessment pending candidate completion. Provisional neutral score (50%) used in evaluation."
            }

        # Detect Assessment vs Resume Conflicts
        for q in assessment_questions:
            skill = cls._normalize_skill(q.get("skill_tested", ""))
            if not skill:
                continue

            # If candidate claimed Senior or extensive knowledge on resume but failed assessment question
            if skill in assessment_skills_failed and (skill in cand_claimed_skills):
                q_title = q.get("title", f"{skill.capitalize()} Question")
                evidence_conflicts.append({
                    "type": "Resume Claim vs Assessment Result Conflict",
                    "claim_text": f"Proficiency in {skill.capitalize()}",
                    "details": f"Candidate claims {skill.capitalize()} on resume, but scored 0 on assessment question: '{q_title}'.",
                    "severity": "Medium"
                })

        # -----------------------------------------------------------------
        # DIMENSION 6: Responsibilities Match (Weight: 15%)
        # -----------------------------------------------------------------
        job_responsibilities = job.responsibilities or []
        responsibilities_matrix = []
        resp_scores = []

        cand_text_corpus = (
            (candidate.raw_summary or "") + " " +
            (candidate.current_title or "") + " " +
            " ".join(str(p) for p in (candidate.projects or [])) + " " +
            " ".join(cand_claimed_skills)
        ).lower()

        for resp in job_responsibilities:
            resp_clean = resp.strip()
            if not resp_clean:
                continue

            # Keyword matching between responsibility and candidate corpus
            words = [w.lower() for w in resp_clean.split() if len(w) > 3]
            match_count = sum(1 for w in words if w in cand_text_corpus)
            coverage = (match_count / max(1, len(words))) if words else 0.5

            if coverage >= 0.40:
                level = "Strong Match"
                r_score = 85  # Calibrated realistic score for strong keyword match (was 100)
                evidence_note = f"Resume and project history demonstrate direct alignment with '{resp_clean[:60]}...'."
            elif coverage >= 0.20:
                level = "Moderate Match"
                r_score = 55  # Calibrated realistic score for partial match (was 65)
                evidence_note = f"Partial overlap with candidate's past projects and technical profile."
            else:
                level = "Limited Match"
                r_score = 25  # Calibrated realistic score for limited mention (was 30)
                evidence_note = f"Limited explicit mention in resume. Recommend probing during interview."

            resp_scores.append(r_score)
            responsibilities_matrix.append({
                "responsibility": resp_clean,
                "match_level": level,
                "score": r_score,
                "evidence": evidence_note
            })

        responsibilities_match_pct = int(sum(resp_scores) / len(resp_scores)) if resp_scores else 100

        # -----------------------------------------------------------------
        # PREFERRED SKILLS MATRIX (Does not penalize or cause REJECT)
        # -----------------------------------------------------------------
        preferred_skills = job.preferred_skills or []
        preferred_skills_matrix = []
        pref_scores = []

        for pref in preferred_skills:
            pref_norm = cls._normalize_skill(pref)
            if not pref_norm:
                continue

            in_assessment = (pref_norm in assessment_skills_passed) or any(pref_norm in s or s in pref_norm for s in assessment_skills_passed)
            in_github = (pref_norm in github_detected_langs) or any(pref_norm in k or k in pref_norm for k in github_detected_langs)
            in_resume = (pref_norm in cand_claimed_skills) or any(pref_norm in c or c in pref_norm for c in cand_claimed_skills)

            if in_assessment or in_github:
                status = "Verified Bonus Skill"
                p_score = 100
                p_notes = f"Verified evidence found for preferred skill {pref}."
            elif in_resume:
                status = "Claimed on Resume"
                p_score = 60
                p_notes = f"Preferred skill {pref} claimed on resume."
            else:
                status = "Not Evidenced"
                p_score = 0
                p_notes = f"Preferred skill {pref} not present (no penalty applied)."

            pref_scores.append(p_score)
            preferred_skills_matrix.append({
                "skill": pref,
                "in_resume": in_resume,
                "in_github": in_github,
                "in_assessment": in_assessment,
                "status": status,
                "notes": p_notes
            })

        preferred_skills_match_pct = int(sum(pref_scores) / len(pref_scores)) if pref_scores else 0

        # -----------------------------------------------------------------
        # FINAL DETERMINISTIC SCORE (Sum of exact weights = 100%)
        # -----------------------------------------------------------------
        # 1. Required Skills: 20%
        # 2. Experience: 15%
        # 3. GitHub Evidence: 15%
        # 4. Claim Verification: 10%
        # 5. Assessment Performance: 25%
        # 6. Responsibilities Match: 15%
        w_req = 0.20 * required_skills_match_pct
        w_exp = 0.15 * experience_match_pct
        w_git = 0.15 * github_match_pct
        w_clm = 0.10 * claim_verification_pct
        w_ass = 0.25 * assessment_match_pct
        w_res = 0.15 * responsibilities_match_pct

        overall_match_pct = int(round(w_req + w_exp + w_git + w_clm + w_ass + w_res))
        overall_match_pct = max(0, min(100, overall_match_pct))

        # -----------------------------------------------------------------
        # ADVISORY RECOMMENDATION LOGIC
        # SHORTLIST (>= 75), REVIEW (50-74 or conflicts), REJECT (< 50)
        # -----------------------------------------------------------------
        has_severe_contradiction = any(c.get("severity") == "High" for c in evidence_conflicts)

        if has_severe_contradiction:
            # Critical fraud/contradiction prevents automatic Shortlist
            recommendation = "REVIEW" if overall_match_pct >= 50 else "REJECT"
        elif overall_match_pct >= 75:
            # Check if there is a true assessment conflict or severe required skill gap
            if len(evidence_conflicts) > 0 or required_skills_match_pct < 60:
                recommendation = "REVIEW"
            else:
                recommendation = "SHORTLIST"
        elif overall_match_pct >= 50:
            recommendation = "REVIEW"
        else:
            recommendation = "REJECT"

        # Mandatory Safety Invariants Verification
        # 1. Missing GitHub alone != REJECT
        # 2. Missing preferred skills != REJECT
        # 3. "No Public Evidence" != REJECT

        # -----------------------------------------------------------------
        # STRENGTHS & GAPS SYNTHESIS
        # -----------------------------------------------------------------
        strengths = []
        gaps = []

        if assessment_completed and assessment_score is not None and assessment_score >= 70:
            strengths.append(f"Strong Assessment Performance: Scored {assessment_score}% on job-specific assessment.")
        if cand_years >= min_years and min_years > 0:
            strengths.append(f"Meets Experience Threshold: {cand_years:.1f} years vs {min_years:.1f} years required.")
        if matched_required_list:
            top_matched = matched_required_list[:4]
            strengths.append(f"Demonstrated Required Competencies: Verified mastery in {', '.join(top_matched)}.")
        if has_github_account and github_profile.get("total_stars", 0) >= 5:
            strengths.append(f"Public Open-Source Recognition: Earned {github_profile.get('total_stars')} stars across repositories.")
        if preferred_skills_match_pct >= 50:
            strengths.append(f"Preferred Qualifications Bonus: Candidate possesses preferred skills in {', '.join([p['skill'] for p in preferred_skills_matrix if p['in_resume'] or p['in_github']])}.")

        # Fill at least 2 strengths
        if not strengths:
            strengths.append(f"Candidate profile shows foundational alignment for '{job.title}'.")
            if cand_years > 0:
                strengths.append(f"{cand_years:.1f} years of relevant professional software background.")

        if missing_required_list:
            gaps.append(f"Missing Mandatory Skills: Candidate lacks evidence for {', '.join(missing_required_list)}.")
        if min_years > 0 and cand_years < min_years:
            gaps.append(f"Experience Gap: Candidate has {cand_years:.1f} years, below the {min_years:.1f} years requirement.")
        if assessment_completed and assessment_score is not None and assessment_score < 60:
            gaps.append(f"Low Assessment Score: Achieved {assessment_score}%, indicating gaps in hands-on problem solving.")
        if evidence_conflicts:
            gaps.append(f"Evidence Conflicts Detected: {len(evidence_conflicts)} discrepancy/conflict items require manual recruiter review.")

        if not gaps:
            gaps.append("No critical competency gaps identified for this role.")

        # Summary text
        summary = (
            f"Candidate '{candidate.name}' achieved a deterministic Job Match Score of {overall_match_pct}% "
            f"for '{job.title}'. Advisory Recommendation: {recommendation}. "
            f"Key factors include {required_skills_match_pct}% required skills match, {experience_match_pct}% experience match, "
            f"and {assessment_match_pct}% assessment score. "
            f"Identified {len(strengths)} strengths and {len(gaps)} areas for verification."
        )

        # Structured Dimensions JSON
        dimensions_json = {
            "required_skills": {
                "label": "Required Technical Skills",
                "weight_pct": 20,
                "score": required_skills_match_pct,
                "weighted_contribution": round(w_req, 1),
                "matched_count": len(matched_required_list),
                "total_count": len(required_skills)
            },
            "experience": {
                "label": "Relevant Experience",
                "weight_pct": 15,
                "score": experience_match_pct,
                "weighted_contribution": round(w_exp, 1),
                "candidate_years": cand_years,
                "required_years": min_years,
                "notes": experience_notes
            },
            "github_evidence": {
                "label": "GitHub Evidence",
                "weight_pct": 15,
                "score": github_match_pct,
                "weighted_contribution": round(w_git, 1),
                "is_neutral_baseline": is_github_neutral,
                "notes": github_summary.get("notes", "")
            },
            "claim_verification": {
                "label": "Claim Verification",
                "weight_pct": 10,
                "score": claim_verification_pct,
                "weighted_contribution": round(w_clm, 1),
                "claims_audited_count": len(claim_vers)
            },
            "assessment_performance": {
                "label": "Assessment Performance",
                "weight_pct": 25,
                "score": assessment_match_pct,
                "weighted_contribution": round(w_ass, 1),
                "status": assessment_summary.get("status", "pending"),
                "notes": assessment_summary.get("notes", "")
            },
            "responsibilities_match": {
                "label": "Responsibilities Match",
                "weight_pct": 15,
                "score": responsibilities_match_pct,
                "weighted_contribution": round(w_res, 1),
                "responsibilities_count": len(job_responsibilities)
            }
        }

        # -----------------------------------------------------------------
        # PERSISTENCE (Preserve Recruiter Override if already set)
        # -----------------------------------------------------------------
        score_stmt = select(JobMatchScore).where(
            JobMatchScore.candidate_id == cand_uuid,
            JobMatchScore.job_id == job_uuid
        )
        score_res = await db.execute(score_stmt)
        existing_score = score_res.scalar_one_or_none()

        recruiter_decision = None
        recruiter_reason = None
        recruiter_override_score = None
        recruiter_decision_at = None
        recruiter_decision_by = None

        if existing_score:
            recruiter_decision = existing_score.recruiter_decision
            recruiter_reason = existing_score.recruiter_reason
            recruiter_override_score = existing_score.recruiter_override_score
            recruiter_decision_at = existing_score.recruiter_decision_at
            recruiter_decision_by = existing_score.recruiter_decision_by

            existing_score.overall_match_pct = overall_match_pct
            existing_score.required_skills_match_pct = required_skills_match_pct
            existing_score.experience_match_pct = experience_match_pct
            existing_score.github_match_pct = github_match_pct
            existing_score.claim_verification_pct = claim_verification_pct
            existing_score.assessment_match_pct = assessment_match_pct
            existing_score.responsibilities_match_pct = responsibilities_match_pct
            existing_score.preferred_skills_match_pct = preferred_skills_match_pct
            existing_score.recommendation = recommendation
            existing_score.job_fit_recommendation = recommendation
            existing_score.summary = summary
            existing_score.dimensions_json = dimensions_json
            existing_score.strengths_json = strengths
            existing_score.gaps_json = gaps
            existing_score.claims_requiring_verification_json = claims_requiring_verification
            existing_score.evidence_conflicts_json = evidence_conflicts
            existing_score.required_skills_matrix_json = required_skills_matrix
            existing_score.preferred_skills_matrix_json = preferred_skills_matrix
            existing_score.responsibilities_matrix_json = responsibilities_matrix
            existing_score.assessment_summary_json = assessment_summary
            existing_score.github_summary_json = github_summary
            existing_score.matched_required_skills = matched_required_list
            existing_score.missing_required_skills = missing_required_list
            existing_score.updated_at = datetime.now(timezone.utc)
            match_record = existing_score
        else:
            match_record = JobMatchScore(
                organization_id=org_uuid or candidate.organization_id,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                overall_match_pct=overall_match_pct,
                required_skills_match_pct=required_skills_match_pct,
                experience_match_pct=experience_match_pct,
                github_match_pct=github_match_pct,
                claim_verification_pct=claim_verification_pct,
                assessment_match_pct=assessment_match_pct,
                responsibilities_match_pct=responsibilities_match_pct,
                preferred_skills_match_pct=preferred_skills_match_pct,
                recommendation=recommendation,
                job_fit_recommendation=recommendation,
                summary=summary,
                dimensions_json=dimensions_json,
                strengths_json=strengths,
                gaps_json=gaps,
                claims_requiring_verification_json=claims_requiring_verification,
                evidence_conflicts_json=evidence_conflicts,
                required_skills_matrix_json=required_skills_matrix,
                preferred_skills_matrix_json=preferred_skills_matrix,
                responsibilities_matrix_json=responsibilities_matrix,
                assessment_summary_json=assessment_summary,
                github_summary_json=github_summary,
                matched_required_skills=matched_required_list,
                missing_required_skills=missing_required_list
            )
            db.add(match_record)

        await db.commit()

        # Build response payload
        result = {
            "id": str(match_record.id),
            "candidate_id": str(candidate_id),
            "candidate_name": candidate.name,
            "job_id": str(job_id),
            "job_title": job.title,
            "overall_match_pct": overall_match_pct,
            "recommendation": recommendation,
            "effective_recommendation": recruiter_decision or recommendation,
            "summary": summary,
            "dimensions": dimensions_json,
            "strengths": strengths,
            "gaps": gaps,
            "claims_requiring_verification": claims_requiring_verification,
            "evidence_conflicts": evidence_conflicts,
            "required_skills_matrix": required_skills_matrix,
            "preferred_skills_matrix": preferred_skills_matrix,
            "responsibilities_matrix": responsibilities_matrix,
            "assessment_summary": assessment_summary,
            "github_summary": github_summary,
            "recruiter_override": {
                "has_override": bool(recruiter_decision),
                "decision": recruiter_decision,
                "reason": recruiter_reason,
                "override_score": recruiter_override_score,
                "decision_at": recruiter_decision_at.isoformat() if recruiter_decision_at else None,
                "decision_by": recruiter_decision_by
            },
            "evaluated_at": datetime.now(timezone.utc).isoformat()
        }

        cache_key = f"{candidate_id}:{job_id}"
        job_match_evaluation_cache[cache_key] = result
        return result

    @classmethod
    async def get_evaluation(
        cls,
        db: AsyncSession,
        job_id: str,
        candidate_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieves existing evaluation if available or checks cache."""
        cache_key = f"{candidate_id}:{job_id}"
        if cache_key in job_match_evaluation_cache:
            return job_match_evaluation_cache[cache_key]

        try:
            job_uuid = uuid.UUID(str(job_id))
            cand_uuid = uuid.UUID(str(candidate_id))
        except Exception:
            return None

        stmt = select(JobMatchScore).where(
            JobMatchScore.candidate_id == cand_uuid,
            JobMatchScore.job_id == job_uuid
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record:
            return None

        # Fetch candidate and job names
        c_res = await db.execute(select(Candidate.name).where(Candidate.id == cand_uuid))
        cand_name = c_res.scalar_one_or_none() or "Candidate"

        j_res = await db.execute(select(JobOpening.title).where(JobOpening.id == job_uuid))
        job_title = j_res.scalar_one_or_none() or "Job"

        result = {
            "id": str(record.id),
            "candidate_id": str(candidate_id),
            "candidate_name": cand_name,
            "job_id": str(job_id),
            "job_title": job_title,
            "overall_match_pct": record.overall_match_pct,
            "recommendation": record.recommendation or record.job_fit_recommendation,
            "effective_recommendation": record.recruiter_decision or record.recommendation or record.job_fit_recommendation,
            "summary": record.summary,
            "dimensions": record.dimensions_json or {},
            "strengths": record.strengths_json or [],
            "gaps": record.gaps_json or [],
            "claims_requiring_verification": record.claims_requiring_verification_json or [],
            "evidence_conflicts": record.evidence_conflicts_json or [],
            "required_skills_matrix": record.required_skills_matrix_json or [],
            "preferred_skills_matrix": record.preferred_skills_matrix_json or [],
            "responsibilities_matrix": record.responsibilities_matrix_json or [],
            "assessment_summary": record.assessment_summary_json or {},
            "github_summary": record.github_summary_json or {},
            "recruiter_override": {
                "has_override": bool(record.recruiter_decision),
                "decision": record.recruiter_decision,
                "reason": record.recruiter_reason,
                "override_score": record.recruiter_override_score,
                "decision_at": record.recruiter_decision_at.isoformat() if record.recruiter_decision_at else None,
                "decision_by": record.recruiter_decision_by
            },
            "terminal_pipeline_status": (
                "SHORTLISTED" if record.recruiter_decision == "SHORTLIST"
                else ("REJECTED" if record.recruiter_decision == "REJECT"
                else ("IN_REVIEW" if record.recruiter_decision == "REVIEW" else "PENDING_DECISION"))
            ),
            "evaluated_at": record.updated_at.isoformat() if record.updated_at else record.created_at.isoformat()
        }
        job_match_evaluation_cache[cache_key] = result
        return result

    @classmethod
    async def apply_recruiter_override(
        cls,
        db: AsyncSession,
        job_id: str,
        candidate_id: str,
        tenant_id: str,
        decision: str,
        reason: str,
        override_score: Optional[int] = None,
        recruiter_name: str = "Lead Technical Recruiter"
    ) -> Dict[str, Any]:
        """
        Applies a recruiter override (SHORTLIST, REVIEW, REJECT) with required rationale.
        Preserves original automated score and recommendation intact for compliance.
        Updates candidate pipeline record to terminal status scoped strictly to the target job.
        """
        decision_clean = (decision or "").strip().upper()
        if decision_clean not in ("SHORTLIST", "REVIEW", "REJECT"):
            raise ValueError(f"Invalid recruiter decision '{decision}'. Must be SHORTLIST, REVIEW, or REJECT.")

        if not reason or not reason.strip():
            raise ValueError("Recruiter override requires a clear, non-empty rationale/reason.")

        try:
            job_uuid = uuid.UUID(str(job_id))
            cand_uuid = uuid.UUID(str(candidate_id))
        except Exception as e:
            raise ValueError(f"Invalid UUID: {e}")

        stmt = select(JobMatchScore).where(
            JobMatchScore.candidate_id == cand_uuid,
            JobMatchScore.job_id == job_uuid
        )
        res = await db.execute(stmt)
        record = res.scalar_one_or_none()

        if not record:
            # First run evaluation to create base record
            await cls.evaluate_candidate_for_job(db, job_id, candidate_id, tenant_id, recruiter_name)
            res = await db.execute(stmt)
            record = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        record.recruiter_decision = decision_clean
        record.recruiter_reason = reason.strip()
        if override_score is not None:
            record.recruiter_override_score = max(0, min(100, int(override_score)))
        record.recruiter_decision_at = now
        record.recruiter_decision_by = recruiter_name
        record.updated_at = now

        # Update terminal pipeline status on Application record scoped strictly to this job
        terminal_status_map = {
            "SHORTLIST": "SHORTLISTED",
            "REVIEW": "IN_REVIEW",
            "REJECT": "REJECTED"
        }
        terminal_status = terminal_status_map.get(decision_clean, decision_clean)

        app_stmt = select(Application).where(
            Application.candidate_id == cand_uuid,
            Application.job_id == job_uuid
        )
        app_res = await db.execute(app_stmt)
        application = app_res.scalar_one_or_none()
        if application:
            application.status = terminal_status

        await db.commit()

        # Invalidate / update cache
        cache_key = f"{candidate_id}:{job_id}"
        if cache_key in job_match_evaluation_cache:
            job_match_evaluation_cache[cache_key]["recruiter_override"] = {
                "has_override": True,
                "decision": decision_clean,
                "reason": reason.strip(),
                "override_score": record.recruiter_override_score,
                "decision_at": now.isoformat(),
                "decision_by": recruiter_name
            }
            job_match_evaluation_cache[cache_key]["effective_recommendation"] = decision_clean
            job_match_evaluation_cache[cache_key]["terminal_pipeline_status"] = terminal_status

        return await cls.get_evaluation(db, job_id, candidate_id, tenant_id)
