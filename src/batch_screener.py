import io
import csv
import time
import asyncio
import tempfile
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .agent_1_resume_parser import parse_resume, CandidateClaims
from .agent_2_code_auditor import audit_github, GitHubEvidence
from .consensus_evaluator import run_consensus_evaluation
from .smart_cache import smart_cache

class BatchCandidateResult(BaseModel):
    rank: int = 1
    candidate_name: str
    github_username: str
    linkedin_url: Optional[str] = None
    overall_score: int
    recommendation: str  # SHORTLIST | REVIEW | REJECT
    skills_match_score: int
    code_quality_score: int
    consistency_score: int
    years_experience: Optional[float] = None
    is_valid_resume: bool = True
    document_type: str = "RESUME"
    red_flags: List[str] = Field(default_factory=list)
    green_flags: List[str] = Field(default_factory=list)
    executive_summary: str
    latency_seconds: float = 0.0
    cached: bool = False
    email_draft: Optional[Dict[str, Any]] = None

class BatchScreeningSummary(BaseModel):
    batch_id: str
    total_candidates: int = 0
    shortlisted_count: int = 0
    review_count: int = 0
    rejected_count: int = 0
    average_score: float = 0.0
    processing_time_seconds: float = 0.0
    status: str = "completed"
    candidates: List[BatchCandidateResult] = Field(default_factory=list)

async def _audit_single_candidate(
    candidate_name: str,
    pdf_bytes: bytes,
    github_override: Optional[str],
    linkedin_url: Optional[str],
    semaphore: asyncio.Semaphore
) -> BatchCandidateResult:
    async with semaphore:
        start_time = time.time()
        
        # Check SmartCache
        file_hash = smart_cache.compute_file_hash(pdf_bytes) if pdf_bytes else "no_pdf"
        cache_key = f"batch:{file_hash}:{github_override or ''}"
        cached = smart_cache.get("batch_candidate", cache_key)
        if cached:
            res = BatchCandidateResult(**cached)
            res.cached = True
            res.latency_seconds = round(time.time() - start_time, 2)
            return res

        # Temporary PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            # 1. Parse Resume
            claims = parse_resume(tmp_path)
            if candidate_name and candidate_name != "Candidate Application":
                claims.name = candidate_name

            # 🚨 EARLY TERMINATION: Halt invalid documents immediately
            if not getattr(claims, "is_valid_resume", True):
                elapsed = round(time.time() - start_time, 2)
                from .email_connector import DraftResponseGenerator
                draft = DraftResponseGenerator.create_draft(
                    candidate_name=claims.name,
                    recipient_email=claims.email or f"{claims.name.lower().replace(' ', '.')}@example.com",
                    verdict="REJECT",
                    score=0
                )
                red_flags = [
                    "CRITICAL: Uploaded document is NOT a valid professional resume/CV.",
                    f"Document classified as: {getattr(claims, 'document_type', 'ACADEMIC_LAB_OR_EXERCISE')}."
                ] + getattr(claims, "validation_flags", [])

                result = BatchCandidateResult(
                    candidate_name=claims.name,
                    github_username="none",
                    linkedin_url=linkedin_url,
                    overall_score=0,
                    recommendation="REJECT",
                    skills_match_score=0,
                    code_quality_score=0,
                    consistency_score=0,
                    years_experience=0.0,
                    is_valid_resume=False,
                    document_type=getattr(claims, "document_type", "ACADEMIC_LAB_OR_EXERCISE"),
                    red_flags=red_flags,
                    green_flags=[],
                    executive_summary=(
                        f"Screening HALTED: Uploaded document for '{claims.name}' does not appear to be a professional resume/CV "
                        f"(detected: {getattr(claims, 'document_type', 'ACADEMIC_LAB_OR_EXERCISE')}). Score: 0/100 REJECT."
                    ),
                    latency_seconds=elapsed,
                    cached=False,
                    email_draft=draft.model_dump()
                )
                smart_cache.set("batch_candidate", cache_key, result.model_dump())
                return result

            target_github = github_override or claims.github_username or "none"

            # 2. GitHub Evidence (with cache)
            github_cache = smart_cache.get("github", target_github)
            if github_cache:
                evidence = GitHubEvidence(**github_cache)
            else:
                evidence = audit_github(target_github)
                smart_cache.set("github", target_github, evidence.model_dump())

            # 3. Consensus Evaluation
            consensus = run_consensus_evaluation(claims, evidence)
            card = consensus.scorecard

            # 🚨 FINAL REINFORCED GATE: Ensure invalid documents ALWAYS score 0 and REJECT
            if not getattr(claims, "is_valid_resume", True):
                card.overall_score = 0
                card.skills_match_score = 0
                card.code_quality_score = 0
                card.consistency_score = 0
                card.recommendation = "REJECT"
                if not any("NOT a valid" in f for f in card.red_flags):
                    card.red_flags.insert(0, "CRITICAL: Uploaded document is NOT a valid professional resume/CV.")

            elapsed = round(time.time() - start_time, 2)

            from .email_connector import DraftResponseGenerator
            draft = DraftResponseGenerator.create_draft(
                candidate_name=claims.name,
                recipient_email=claims.email or f"{claims.name.lower().replace(' ', '.')}@example.com",
                verdict=card.recommendation,
                score=card.overall_score
            )

            result = BatchCandidateResult(
                candidate_name=claims.name,
                github_username=target_github,
                linkedin_url=linkedin_url,
                overall_score=card.overall_score,
                recommendation=card.recommendation,
                skills_match_score=card.skills_match_score,
                code_quality_score=card.code_quality_score,
                consistency_score=card.consistency_score,
                years_experience=claims.years_experience,
                is_valid_resume=getattr(claims, "is_valid_resume", True),
                document_type=getattr(claims, "document_type", "RESUME"),
                red_flags=card.red_flags,
                green_flags=card.green_flags,
                executive_summary=card.executive_summary,
                latency_seconds=elapsed,
                cached=False,
                email_draft=draft.model_dump()
            )

            smart_cache.set("batch_candidate", cache_key, result.model_dump())
            return result
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

async def run_batch_screening(
    batch_id: str,
    applications: List[Dict[str, Any]],
    max_concurrency: int = 10
) -> BatchScreeningSummary:
    """Processes a batch of candidate applications concurrently."""
    start_batch = time.time()
    semaphore = asyncio.Semaphore(max_concurrency)

    tasks = [
        _audit_single_candidate(
            candidate_name=app.get("name", "Candidate"),
            pdf_bytes=app.get("pdf_bytes", b""),
            github_override=app.get("github_username"),
            linkedin_url=app.get("linkedin_url"),
            semaphore=semaphore
        )
        for app in applications
    ]

    results: List[BatchCandidateResult] = await asyncio.gather(*tasks, return_exceptions=False)

    # Sort descending by overall score
    results.sort(key=lambda c: c.overall_score, reverse=True)

    # Assign ranks
    for idx, cand in enumerate(results):
        cand.rank = idx + 1

    total = len(results)
    shortlisted = sum(1 for c in results if c.recommendation == "SHORTLIST")
    review = sum(1 for c in results if c.recommendation == "REVIEW")
    rejected = sum(1 for c in results if c.recommendation == "REJECT")
    avg_score = round(sum(c.overall_score for c in results) / total, 1) if total > 0 else 0.0
    elapsed_total = round(time.time() - start_batch, 2)

    return BatchScreeningSummary(
        batch_id=batch_id,
        total_candidates=total,
        shortlisted_count=shortlisted,
        review_count=review,
        rejected_count=rejected,
        average_score=avg_score,
        processing_time_seconds=elapsed_total,
        status="completed",
        candidates=results
    )

def generate_batch_csv(summary: BatchScreeningSummary) -> str:
    """Generates clean CSV text formatted for recruiter review & ATS import."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "Rank", "Candidate Name", "Overall Score", "Recommendation",
        "Skills Match (40%)", "Code Quality (30%)", "Consistency (30%)",
        "GitHub Handle", "LinkedIn Profile", "Experience (Yrs)",
        "Key Red Flags", "Verified Strengths", "Executive Summary"
    ])

    for c in summary.candidates:
        writer.writerow([
            c.rank,
            c.candidate_name,
            f"{c.overall_score}/100",
            c.recommendation,
            f"{c.skills_match_score}%",
            f"{c.code_quality_score}%",
            f"{c.consistency_score}%",
            f"https://github.com/{c.github_username}" if c.github_username != "none" else "N/A",
            c.linkedin_url or "N/A",
            c.years_experience or "N/A",
            " | ".join(c.red_flags) if c.red_flags else "None",
            " | ".join(c.green_flags) if c.green_flags else "None",
            c.executive_summary
        ])

    return output.getvalue()
