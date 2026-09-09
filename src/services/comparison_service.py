import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import (
    Candidate, Audit, JobMatchScore, CandidateAssessment, TechnicalInterview
)

logger = logging.getLogger("auditagent.comparison")

class CandidateComparisonService:
    """
    Evaluates and compares 2 to 5 candidates side-by-side across multidimensional hiring criteria:
    Claim vs Evidence, Code Quality, Job Match, Assessments, and Technical Interviews.
    """

    def __init__(self, db: AsyncSession, org_id: UUID):
        self.db = db
        self.org_id = org_id

    async def compare_candidates(
        self, candidate_ids: List[UUID], job_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        if not candidate_ids or len(candidate_ids) < 2:
            raise ValueError("Comparison requires at least 2 candidates.")

        candidates_data = []
        all_skills_pool = set()

        for cid in candidate_ids[:5]:  # limit to max 5 for UI comparison
            # Fetch Candidate
            c_stmt = select(Candidate).where(Candidate.id == cid, Candidate.organization_id == self.org_id)
            c_res = await self.db.execute(c_stmt)
            candidate = c_res.scalar_one_or_none()
            if not candidate:
                continue

            # Fetch Latest Audit
            a_stmt = (
                select(Audit)
                .where(Audit.candidate_id == cid, Audit.organization_id == self.org_id)
                .order_by(Audit.created_at.desc())
                .limit(1)
            )
            a_res = await self.db.execute(a_stmt)
            audit = a_res.scalar_one_or_none()

            # Fetch Job Match if job_id provided
            job_match = None
            if job_id:
                jm_stmt = (
                    select(JobMatchScore)
                    .where(
                        JobMatchScore.candidate_id == cid,
                        JobMatchScore.job_id == job_id
                    )
                    .order_by(JobMatchScore.created_at.desc())
                    .limit(1)
                )
                jm_res = await self.db.execute(jm_stmt)
                job_match = jm_res.scalar_one_or_none()

            # Fetch Assessment
            ass_stmt = (
                select(CandidateAssessment)
                .where(
                    CandidateAssessment.candidate_id == cid,
                    CandidateAssessment.organization_id == self.org_id
                )
                .order_by(CandidateAssessment.created_at.desc())
                .limit(1)
            )
            ass_res = await self.db.execute(ass_stmt)
            assessment = ass_res.scalar_one_or_none()

            # Fetch Interview
            int_stmt = (
                select(TechnicalInterview)
                .where(
                    TechnicalInterview.candidate_id == cid,
                    TechnicalInterview.organization_id == self.org_id
                )
                .order_by(TechnicalInterview.created_at.desc())
                .limit(1)
            )
            int_res = await self.db.execute(int_stmt)
            interview = int_res.scalar_one_or_none()

            # Fetch Audit Flags
            from src.db.models import AuditFlag
            if audit is not None:
                flags_stmt = select(AuditFlag).where(AuditFlag.audit_id == audit.id)
                flags_res = (await self.db.execute(flags_stmt)).scalars().all()
            else:
                flags_res = []
            red_flags = [f.message for f in flags_res if f.flag_type == "red"]
            highlights = [f.message for f in flags_res if f.flag_type == "green"]

            # Extract verified skills
            verified_skills = candidate.tags or []
            all_skills_pool.update(verified_skills)

            item = {
                "candidate_id": str(candidate.id),
                "name": candidate.name,
                "email": candidate.email,
                "github_handle": candidate.github_username or "candidate",
                "overall_score": audit.overall_score if audit else None,
                "recommendation": getattr(audit, "ai_recommendation", "NOT_AUDITED") if audit else "NOT_AUDITED",
                "breakdown": {
                    "consistency_score": audit.consistency_score if audit else 0,
                    "code_quality_score": audit.code_quality_score if audit else 0,
                    "domain_score": audit.skills_match_score if audit else 0,
                },
                "verified_skills": verified_skills,
                "red_flags": red_flags,
                "highlights": highlights,
                "job_match": {
                    "overall_match_pct": job_match.overall_match_pct if job_match else None,
                    "fit_recommendation": job_match.job_fit_recommendation if job_match else None,
                    "missing_required_skills": job_match.missing_required_skills if job_match else []
                },
                "assessment": {
                    "score": assessment.score if assessment else None,
                    "status": assessment.status if assessment else None
                },
                "interview": {
                    "technical_score": interview.technical_score if interview else None,
                    "status": interview.status if interview else None
                }
            }
            candidates_data.append(item)

        # Radar matrix skills comparisons
        skills_radar = []
        for skill in sorted(list(all_skills_pool)):
            skill_entry = {"skill": skill}
            for c in candidates_data:
                skill_entry[c["candidate_id"]] = 1.0 if skill in c["verified_skills"] else 0.0
            skills_radar.append(skill_entry)

        # Compute ranking verdict
        ranked = sorted(
            candidates_data,
            key=lambda x: (
                (x["overall_score"] or 0) * 0.4 +
                (x["job_match"]["overall_match_pct"] or (x["overall_score"] or 0)) * 0.3 +
                (x["assessment"]["score"] or 60) * 0.15 +
                (x["interview"]["technical_score"] or 60) * 0.15
            ),
            reverse=True
        )
        winner = ranked[0] if ranked else None

        verdict = {
            "winner_id": winner["candidate_id"] if winner else None,
            "winner_name": winner["name"] if winner else None,
            "rationale": f"{winner['name']} demonstrated the highest combined evidence integrity and technical score." if winner else "Insufficient data.",
            "justification": f"{winner['name']} demonstrated the highest combined evidence integrity and technical score." if winner else "Insufficient data."
        }

        return {
            "candidate_count": len(candidates_data),
            "candidates": candidates_data,
            "skills_matrix": skills_radar,
            "top_candidate_verdict": verdict,
            "recommendation_summary": verdict
        }
