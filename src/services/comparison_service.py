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

        # Radar matrix skills comparisons (skill-by-skill presence)
        skills_radar = []
        for skill in sorted(list(all_skills_pool)):
            skill_entry = {"skill": skill}
            for c in candidates_data:
                skill_entry[c["candidate_id"]] = 1.0 if skill in c["verified_skills"] else 0.0
            skills_radar.append(skill_entry)

        # 6-Axis Skill Radar Visualization (Normalized 0-100 across key hiring dimensions)
        radar_dimensions = [
            "Skills Alignment",
            "Code Quality",
            "Consistency",
            "Job Match",
            "Assessment",
            "Interview"
        ]
        radar_series = []
        for c in candidates_data:
            sk_align = c["breakdown"].get("domain_score") or (c["overall_score"] if c["overall_score"] is not None else 70)
            cq_score = c["breakdown"].get("code_quality_score") or (c["overall_score"] if c["overall_score"] is not None else 70)
            cs_score = c["breakdown"].get("consistency_score") or (c["overall_score"] if c["overall_score"] is not None else 70)
            jm_score = c["job_match"].get("overall_match_pct") or (c["overall_score"] if c["overall_score"] is not None else 70)
            as_score = c["assessment"].get("score") or (80 if c["assessment"].get("status") == "passed" else 65)
            in_score = c["interview"].get("technical_score") or (82 if c["interview"].get("status") == "completed" else 65)

            radar_series.append({
                "candidate_id": c["candidate_id"],
                "candidate_name": c["name"],
                "data": [sk_align, cq_score, cs_score, jm_score, as_score, in_score],
                "dimension_map": {
                    "Skills Alignment": sk_align,
                    "Code Quality": cq_score,
                    "Consistency": cs_score,
                    "Job Match": jm_score,
                    "Assessment": as_score,
                    "Interview": in_score
                }
            })

        radar_chart = {
            "dimensions": radar_dimensions,
            "max_score": 100,
            "series": radar_series
        }

        # Compute ranking verdict with composite scoring
        for c in candidates_data:
            c_overall = c["overall_score"] if c["overall_score"] is not None else 70
            c_job = c["job_match"]["overall_match_pct"] if c["job_match"]["overall_match_pct"] is not None else c_overall
            c_ass = c["assessment"]["score"] if c["assessment"]["score"] is not None else 65
            c_int = c["interview"]["technical_score"] if c["interview"]["technical_score"] is not None else 65
            c["composite_score"] = round(c_overall * 0.35 + c_job * 0.25 + c_ass * 0.20 + c_int * 0.20, 1)

        ranked = sorted(
            candidates_data,
            key=lambda x: x.get("composite_score", 0),
            reverse=True
        )
        winner = ranked[0] if ranked else None

        dimension_advantages = []
        if winner and len(ranked) > 1:
            runner_up = ranked[1]
            w_series = next((s for s in radar_series if s["candidate_id"] == winner["candidate_id"]), None)
            r_series = next((s for s in radar_series if s["candidate_id"] == runner_up["candidate_id"]), None)
            if w_series and r_series:
                for dim in radar_dimensions:
                    w_val = w_series["dimension_map"].get(dim, 0)
                    r_val = r_series["dimension_map"].get(dim, 0)
                    if w_val > r_val:
                        dimension_advantages.append(f"+{w_val - r_val}pts in {dim} vs runner-up ({runner_up['name']})")

        verdict = {
            "winner_id": winner["candidate_id"] if winner else None,
            "winner_name": winner["name"] if winner else None,
            "composite_score": winner.get("composite_score") if winner else None,
            "dimension_advantages": dimension_advantages,
            "rationale": (
                f"{winner['name']} demonstrated the highest overall evidence integrity "
                f"(composite {winner.get('composite_score')}/100) with key leads in "
                f"{', '.join(dimension_advantages[:2]) if dimension_advantages else 'core technical competencies'}."
            ) if winner else "Insufficient data.",
            "justification": (
                f"Selected {winner['name']} based on comprehensive verification across code quality, "
                f"repository authorship consistency, and technical assessments."
            ) if winner else "Insufficient data."
        }

        # Build Side-by-Side Matrix Table
        side_by_side_matrix = [
            {
                "metric": "Overall Evidence Score",
                "values": {c["candidate_id"]: f"{c['overall_score']}/100" if c['overall_score'] is not None else "Pending" for c in candidates_data}
            },
            {
                "metric": "Composite Evaluator Score",
                "values": {c["candidate_id"]: f"{c.get('composite_score', 0)}/100" for c in candidates_data}
            },
            {
                "metric": "AI Recommendation",
                "values": {c["candidate_id"]: c["recommendation"] for c in candidates_data}
            },
            {
                "metric": "Code Quality Score",
                "values": {c["candidate_id"]: f"{c['breakdown']['code_quality_score']}/100" for c in candidates_data}
            },
            {
                "metric": "Consistency & Authorship",
                "values": {c["candidate_id"]: f"{c['breakdown']['consistency_score']}/100" for c in candidates_data}
            },
            {
                "metric": "Job Fit Match",
                "values": {c["candidate_id"]: f"{c['job_match']['overall_match_pct']}%" if c['job_match']['overall_match_pct'] is not None else "N/A" for c in candidates_data}
            },
            {
                "metric": "Assessment Score",
                "values": {c["candidate_id"]: f"{c['assessment']['score']}/100" if c['assessment']['score'] is not None else "Not Taken" for c in candidates_data}
            },
            {
                "metric": "Technical Interview",
                "values": {c["candidate_id"]: f"{c['interview']['technical_score']}/100" if c['interview']['technical_score'] is not None else "Not Scheduled" for c in candidates_data}
            },
            {
                "metric": "Verified Skills Count",
                "values": {c["candidate_id"]: len(c["verified_skills"]) for c in candidates_data}
            },
            {
                "metric": "Red Flags",
                "values": {c["candidate_id"]: len(c["red_flags"]) for c in candidates_data}
            },
            {
                "metric": "Green Highlights",
                "values": {c["candidate_id"]: len(c["highlights"]) for c in candidates_data}
            }
        ]

        return {
            "candidate_count": len(candidates_data),
            "candidates": candidates_data,
            "skills_matrix": skills_radar,
            "radar_chart": radar_chart,
            "side_by_side_matrix": side_by_side_matrix,
            "top_candidate_verdict": verdict,
            "recommendation_summary": verdict
        }

