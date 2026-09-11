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
    recruiter_recommendation: Optional[str] = None
    next_action: Optional[str] = None
    next_action_label: Optional[str] = None
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
    job_title: Optional[str] = None
    job_match_score: Optional[int] = None
    technical_score: Optional[int] = None
    evidence_score: Optional[int] = None
    verdict: Optional[str] = None

class BatchScreeningSummary(BaseModel):
    batch_id: str
    total_candidates: int = 0
    shortlisted_count: int = 0
    review_count: int = 0
    rejected_count: int = 0
    invalid_count: int = 0
    failed_count: int = 0
    average_score: float = 0.0
    processing_time_seconds: float = 0.0
    status: str = "completed"
    candidates: List[BatchCandidateResult] = Field(default_factory=list)

async def _audit_single_candidate(
    candidate_name: str,
    pdf_bytes: bytes,
    github_override: Optional[str],
    linkedin_url: Optional[str],
    semaphore: asyncio.Semaphore,
    target_role: Optional[str] = None,
    required_skills: Optional[List[str]] = None,
    min_experience: Optional[float] = None,
    job_description: Optional[str] = None
) -> BatchCandidateResult:
    async with semaphore:
        start_time = time.time()
        
        # Check SmartCache
        file_hash = smart_cache.compute_file_hash(pdf_bytes) if pdf_bytes else "no_pdf"
        skills_hash = ",".join(sorted(required_skills)) if required_skills else ""
        cache_key = f"batch:{file_hash}:{github_override or ''}:{target_role or ''}:{skills_hash}"
        cached = smart_cache.get("batch_candidate", cache_key)
        if cached:
            res = BatchCandidateResult(**cached)
            res.cached = True
            res.latency_seconds = round(time.time() - start_time, 2)
            return res

        try:
            # Delegate to Unified Single Screening Pipeline (Single Source of Truth)
            from .services.screening_service import execute_screening_pipeline_core
            core = execute_screening_pipeline_core(
                file_bytes=pdf_bytes,
                filename=f"{candidate_name or 'candidate'}.pdf",
                candidate_name_override=candidate_name if candidate_name != "Candidate Application" else None,
                github_user_override=github_override,
                linkedin_url_override=linkedin_url,
                target_role=target_role,
                required_skills=required_skills,
                min_experience=min_experience,
                job_description=job_description
            )

            result = BatchCandidateResult(
                candidate_name=core["candidate_name"],
                github_username=core["github_username"],
                linkedin_url=linkedin_url,
                overall_score=core["overall_score"],
                recommendation=core["recommendation"],
                recruiter_recommendation=core["recruiter_recommendation"],
                next_action=core["next_action"],
                next_action_label=core["next_action_label"],
                skills_match_score=core["skills_match_score"],
                code_quality_score=core["code_quality_score"],
                consistency_score=core["consistency_score"],
                years_experience=core["years_experience"],
                is_valid_resume=core["is_valid_resume"],
                document_type=core["document_type"],
                red_flags=core["red_flags"],
                green_flags=core["green_flags"],
                executive_summary=core["executive_summary"],
                latency_seconds=core["latency_seconds"],
                cached=False,
                email_draft=core.get("draft_reply_data"),
                job_title=target_role or "Software Engineer",
                job_match_score=core["overall_score"],
                technical_score=core["skills_match_score"],
                evidence_score=core["code_quality_score"],
                verdict=core["recommendation"]
            )
            smart_cache.set("batch_candidate", cache_key, result.model_dump())
            return result

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return BatchCandidateResult(
                candidate_name=candidate_name or "Unknown Candidate",
                github_username="none",
                linkedin_url=linkedin_url,
                overall_score=0,
                recommendation="REJECT",
                recruiter_recommendation="INVALID_DOCUMENT",
                next_action="REQUEST_RESUME",
                next_action_label="Request a valid resume",
                skills_match_score=0,
                code_quality_score=0,
                consistency_score=0,
                years_experience=0.0,
                is_valid_resume=False,
                document_type="UNREADABLE_FILE",
                red_flags=[f"Processing error: {str(e)}"],
                green_flags=[],
                executive_summary=f"Failed to process candidate file: {str(e)}. Score: 0/100.",
                latency_seconds=elapsed,
                cached=False,
                email_draft=None
            )

async def run_batch_screening(
    batch_id: str,
    applications: List[Dict[str, Any]],
    max_concurrency: int = 10,
    target_role: Optional[str] = None,
    required_skills: Optional[List[str]] = None,
    min_experience: Optional[float] = None,
    job_description: Optional[str] = None
) -> BatchScreeningSummary:
    """Processes a batch of candidate applications concurrently against target job requirements."""
    start_batch = time.time()
    semaphore = asyncio.Semaphore(max_concurrency)

    tasks = [
        _audit_single_candidate(
            candidate_name=app.get("name", "Candidate"),
            pdf_bytes=app.get("pdf_bytes", b""),
            github_override=app.get("github_username"),
            linkedin_url=app.get("linkedin_url"),
            semaphore=semaphore,
            target_role=target_role,
            required_skills=required_skills,
            min_experience=min_experience,
            job_description=job_description
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
    failed = sum(1 for c in results if c.document_type in ("UNREADABLE_FILE", "CORRUPT_OR_UNREADABLE_FILE") or (c.red_flags and any("Processing error" in rf for rf in c.red_flags)))
    invalid = sum(1 for c in results if not c.is_valid_resume and c.document_type not in ("UNREADABLE_FILE", "CORRUPT_OR_UNREADABLE_FILE"))
    shortlisted = sum(1 for c in results if c.recommendation == "SHORTLIST" and c.is_valid_resume)
    review = sum(1 for c in results if c.recommendation == "REVIEW" and c.is_valid_resume)
    rejected = sum(1 for c in results if c.recommendation == "REJECT" and c.is_valid_resume)
    avg_score = round(sum(c.overall_score for c in results) / total, 1) if total > 0 else 0.0
    elapsed_total = round(time.time() - start_batch, 2)

    return BatchScreeningSummary(
        batch_id=batch_id,
        total_candidates=total,
        shortlisted_count=shortlisted,
        review_count=review,
        rejected_count=rejected,
        invalid_count=invalid,
        failed_count=failed,
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
        "Rank", "Candidate Name", "Job Title", "Job Match Score", "Technical Score",
        "Evidence Score", "Verdict", "Skills Match (40%)", "Code Quality (30%)", "Consistency (30%)",
        "GitHub Handle", "LinkedIn Profile", "Experience (Yrs)",
        "Key Red Flags", "Verified Strengths", "Executive Summary"
    ])

    for c in summary.candidates:
        writer.writerow([
            c.rank,
            c.candidate_name,
            c.job_title or "Software Engineer",
            f"{c.job_match_score if c.job_match_score is not None else c.overall_score}/100",
            f"{c.technical_score if c.technical_score is not None else c.skills_match_score}%",
            f"{c.evidence_score if c.evidence_score is not None else c.code_quality_score}%",
            c.verdict or c.recommendation,
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
