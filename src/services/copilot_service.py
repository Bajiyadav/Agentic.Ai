import os
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import (
    Candidate, Audit, JobOpening, JobMatchScore,
    CandidateAssessment, TechnicalInterview, PipelineStage
)
import litellm

logger = logging.getLogger("auditagent.copilot")

class RecruiterCopilotService:
    """
    Conversational Recruiter Copilot grounded in tenant PostgreSQL data.
    Provides candidate summaries, stack comparisons, evidence evaluations, and role shortlists.
    """

    def __init__(self, db: AsyncSession, org_id):
        self.db = db
        self.org_id = org_id

    async def _fetch_tenant_context(self) -> Dict[str, Any]:
        """Gathers tenant candidate portfolio for grounding."""
        # Fetch up to 25 recent audits with candidates
        audits_stmt = (
            select(Audit, Candidate)
            .join(Candidate, Audit.candidate_id == Candidate.id)
            .where(Audit.organization_id == self.org_id)
            .order_by(desc(Audit.created_at))
            .limit(25)
        )
        res = await self.db.execute(audits_stmt)
        audits_data = []
        for audit, candidate in res.all():
            from src.db.models import AuditFlag
            flags_stmt = select(AuditFlag).where(AuditFlag.audit_id == audit.id)
            flags_res = await self.db.execute(flags_stmt)
            all_flags = flags_res.scalars().all()
            red_flags = [f.message for f in all_flags if f.flag_type == "red"]
            green_flags = [f.message for f in all_flags if f.flag_type == "green"]

            audits_data.append({
                "id": str(candidate.id),
                "audit_id": str(audit.id),
                "name": candidate.name,
                "email": candidate.email,
                "github_handle": candidate.github_username or "candidate",
                "overall_score": audit.overall_score,
                "recommendation": getattr(audit, "ai_recommendation", "REVIEW"),
                "consistency_score": audit.consistency_score,
                "code_quality_score": audit.code_quality_score,
                "domain_score": audit.skills_match_score,
                "red_flags": red_flags,
                "highlights": green_flags,
                "verified_skills": candidate.tags or []
            })

        # Fetch active job openings
        jobs_stmt = (
            select(JobOpening)
            .where(JobOpening.organization_id == self.org_id, JobOpening.status == "active")
            .limit(10)
        )
        jobs_res = await self.db.execute(jobs_stmt)
        jobs_data = []
        for j in jobs_res.scalars().all():
            jobs_data.append({
                "id": str(j.id),
                "title": j.title,
                "department": j.department,
                "required_skills": j.required_skills or [],
                "min_years_exp": j.experience_min_years
            })

        # Fetch pipeline counts
        stages_stmt = (
            select(PipelineStage)
            .where(PipelineStage.organization_id == self.org_id)
        )
        stage_res = await self.db.execute(stages_stmt)
        stage_counts = {}
        for st in stage_res.scalars().all():
            stage_counts[st.stage] = stage_counts.get(st.stage, 0) + 1

        return {
            "candidates": audits_data,
            "jobs": jobs_data,
            "pipeline_stages": stage_counts
        }

    async def chat(self, user_query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Processes recruiter query grounded in the tenant's actual candidate data.
        """
        context = await self._fetch_tenant_context()
        candidates = context["candidates"]
        jobs = context["jobs"]

        # Deterministic analysis for common patterns if no API key or rapid response
        query_lower = user_query.lower()

        system_instruction = (
            "You are AuditAgent Copilot, an elite technical recruiting assistant for technical founders, "
            "engineering managers, and recruiters. You are strictly grounded in the tenant's database candidates.\n"
            "Never invent candidate names, GitHub scores, or metrics. Always cite real scores from the context.\n"
            "Provide clear, actionable, technical recruiting recommendations, comparing claim vs evidence, "
            "verifications, red flags, and job match."
        )

        context_prompt = (
            f"Tenant Candidate Database Context:\n"
            f"Active Jobs: {json.dumps(jobs, indent=2)}\n"
            f"Pipeline Stats: {json.dumps(context['pipeline_stages'])}\n"
            f"Audited Candidates ({len(candidates)} records):\n"
            f"{json.dumps(candidates, indent=2)}\n\n"
            f"Recruiter Question: {user_query}\n"
        )

        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key and "placeholder" not in api_key.lower():
            try:
                model_name = os.environ.get("OPENROUTER_MODEL", "openrouter/qwen/qwen-2.5-coder-32b-instruct:free")
                res = litellm.completion(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": context_prompt}
                    ],
                    temperature=0.2,
                    timeout=15
                )
                answer_text = res.choices[0].message.content or ""
            except Exception as e:
                logger.warning(f"LLM copilot query failed, falling back to deterministic answer: {e}")
                answer_text = self._deterministic_answer(query_lower, candidates, jobs)
        else:
            answer_text = self._deterministic_answer(query_lower, candidates, jobs)

        # Identify referenced candidate IDs
        referenced_candidate_ids = []
        for c in candidates:
            if c["name"].lower() in answer_text.lower() or c["github_handle"].lower() in answer_text.lower():
                referenced_candidate_ids.append(c["id"])

        return {
            "query": user_query,
            "answer": answer_text,
            "candidates_considered_count": len(candidates),
            "referenced_candidate_ids": referenced_candidate_ids,
            "context_summary": {
                "total_candidates": len(candidates),
                "total_jobs": len(jobs)
            }
        }

    def _deterministic_answer(self, query: str, candidates: List[Dict[str, Any]], jobs: List[Dict[str, Any]]) -> str:
        """High-fidelity rule-grounded responder when external LLM is offline."""
        if not candidates:
            return "No candidates have been audited in your organization yet. Ingest resumes via Single Audit or the Email Ingestion pipeline to begin."

        if "top" in query or "best" in query or "shortlist" in query:
            top = sorted(candidates, key=lambda x: x["overall_score"], reverse=True)[:5]
            lines = ["Here are the top-ranked candidates based on claim vs evidence screening:"]
            for i, c in enumerate(top, 1):
                flags = f" (⚠️ {len(c['red_flags'])} red flags)" if c["red_flags"] else " (✅ Clean Evidence)"
                lines.append(f"{i}. **{c['name']}** (@{c['github_handle']}) — **{c['overall_score']}/100** [{c['recommendation']}]{flags}")
                if c["highlights"]:
                    lines.append(f"   • Highlight: {c['highlights'][0]}")
            return "\n".join(lines)

        if "red flag" in query or "warning" in query or "fraud" in query or "contradict" in query:
            flagged = [c for c in candidates if c["red_flags"]]
            if not flagged:
                return "Good news: No audited candidates currently exhibit major claim-evidence red flags."
            lines = [f"Found {len(flagged)} candidate(s) with evidence red flags:"]
            for c in flagged:
                lines.append(f"• **{c['name']}** (@{c['github_handle']}) — Score {c['overall_score']}/100")
                for rf in c["red_flags"][:2]:
                    lines.append(f"  - ⚠️ {rf}")
            return "\n".join(lines)

        if "compare" in query:
            # Pick first 2 or candidates mentioned
            picked = candidates[:2]
            lines = [f"Comparative Summary: **{picked[0]['name']}** vs **{picked[1]['name']}**\n"]
            for c in picked:
                lines.append(f"### {c['name']} (@{c['github_handle']})")
                lines.append(f"- Overall Score: **{c['overall_score']}/100** ({c['recommendation']})")
                lines.append(f"- Code Consistency: {c['consistency_score']}/40 | Quality: {c['code_quality_score']}/30 | Domain: {c['domain_score']}/30")
                lines.append(f"- Skills Verified: {', '.join(c['verified_skills'][:4]) if c['verified_skills'] else 'General'}")
            return "\n".join(lines)

        # Default overview
        avg_score = sum(c["overall_score"] for c in candidates) // len(candidates)
        shortlisted = sum(1 for c in candidates if c["recommendation"] == "SHORTLIST")
        return (
            f"Your organization has audited **{len(candidates)} candidate(s)** with an average score of **{avg_score}/100**.\n\n"
            f"• **Shortlisted**: {shortlisted}\n"
            f"• **In Review**: {sum(1 for c in candidates if c['recommendation'] == 'REVIEW')}\n"
            f"• **Rejected**: {sum(1 for c in candidates if c['recommendation'] == 'REJECT')}\n\n"
            f"You can ask me to rank top candidates for specific skills, summarize red flags, or compare specific candidates side-by-side."
        )
