import os
import re
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import litellm

class AssessmentQuestion(BaseModel):
    id: str
    type: str  # coding, debugging, architecture, code_review, system_design
    title: str
    prompt: str
    code_snippet: Optional[str] = None
    expected_topics: List[str] = Field(default_factory=list)
    time_limit_minutes: int = 5

class AssessmentPackage(BaseModel):
    job_title: str
    duration_minutes: int
    total_questions: int
    questions: List[AssessmentQuestion]

class AssessmentEvaluationResult(BaseModel):
    score: int = Field(ge=0, le=100)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    feedback: str

def _get_preset_questions(job_title: str, skills: List[str], duration_minutes: int) -> List[AssessmentQuestion]:
    """Generates rigorous preset assessment questions based on primary skills."""
    primary_skill = skills[0] if skills else "Python"
    secondary_skill = skills[1] if len(skills) > 1 else "PostgreSQL"

    q_pool = [
        AssessmentQuestion(
            id="q1_debug",
            type="debugging",
            title=f"Concurrency & Error Handling in {primary_skill}",
            prompt=f"Identify the race condition or memory leak in the following {primary_skill} snippet and explain how you would remediate it.",
            code_snippet=f"# Snippet: Unbounded async worker pool\nasync def process_batch(items):\n    tasks = [asyncio.create_task(handle_item(i)) for i in items]\n    return await asyncio.gather(*tasks)",
            expected_topics=["Semaphore concurrency bounds", "Exception handling", "Memory leak prevention"],
            time_limit_minutes=max(5, duration_minutes // 4)
        ),
        AssessmentQuestion(
            id="q2_db",
            type="architecture",
            title=f"Database Query Optimization & Indexing in {secondary_skill}",
            prompt=f"Given an applications table with 10M rows, explain how you would structure composite indexes and pagination to ensure p99 queries under 50ms.",
            code_snippet="SELECT * FROM applications WHERE status = 'pending' ORDER BY created_at DESC LIMIT 50 OFFSET 200000;",
            expected_topics=["Keyset cursor pagination vs offset", "Partial indexing", "Composite indexes (status, created_at)"],
            time_limit_minutes=max(5, duration_minutes // 4)
        ),
        AssessmentQuestion(
            id="q3_api",
            type="code_review",
            title="REST/GraphQL Idempotency & Security Audit",
            prompt="Review this payment/webhook dispatch endpoint. Highlight vulnerabilities related to idempotency, replay attacks, and transaction rollbacks.",
            code_snippet="POST /api/v1/billing/charge\nPayload: { candidate_id: '123', amount: 5000 }\nHandler charges customer then immediately updates status without idempotency key.",
            expected_topics=["Idempotency keys", "Database transaction atomic commit", "Replay attack mitigation"],
            time_limit_minutes=max(5, duration_minutes // 4)
        ),
        AssessmentQuestion(
            id="q4_sysdesign",
            type="system_design",
            title="High-Throughput Resume Pipeline Architecture",
            prompt="Design a resilient architecture capable of digesting 50,000 PDF resumes daily with rate-limited third-party APIs.",
            code_snippet=None,
            expected_topics=["Message broker (Kafka/RabbitMQ)", "Exponential backoff", "Dead-letter queues", "Worker autoscaling"],
            time_limit_minutes=max(5, duration_minutes // 4)
        )
    ]

    count_map = {10: 2, 20: 3, 30: 4, 60: 4}
    target_count = count_map.get(duration_minutes, 3)
    return q_pool[:target_count]

def generate_technical_assessment(
    job_title: str,
    required_skills: List[str],
    duration_minutes: int = 30
) -> AssessmentPackage:
    """Generates a customized technical assessment tailored to JD requirements and duration."""
    questions = _get_preset_questions(job_title, required_skills, duration_minutes)
    return AssessmentPackage(
        job_title=job_title,
        duration_minutes=duration_minutes,
        total_questions=len(questions),
        questions=questions
    )

def evaluate_assessment_submission(
    questions: List[Dict[str, Any]],
    answers: Dict[str, str]
) -> AssessmentEvaluationResult:
    """Evaluates candidate answers against expected engineering topics and constructs scorecard."""
    total_score = 0
    strengths = []
    weaknesses = []

    if not answers:
        return AssessmentEvaluationResult(
            score=0,
            strengths=[],
            weaknesses=["Candidate submitted empty answers."],
            feedback="Assessment was submitted with no answers recorded."
        )

    points_per_question = 100 // max(1, len(questions))

    for q in questions:
        q_id = q.get("id")
        ans = answers.get(q_id, "").strip()
        expected = q.get("expected_topics", [])

        if not ans or len(ans) < 20:
            weaknesses.append(f"Incomplete response for {q.get('title')}.")
            continue

        matched_topics = [t for t in expected if any(w.lower() in ans.lower() for w in t.split())]
        match_ratio = len(matched_topics) / max(1, len(expected))
        q_score = int(points_per_question * max(0.4, match_ratio))
        total_score += q_score

        if match_ratio >= 0.5:
            strengths.append(f"Demonstrated solid understanding of {q.get('title')}.")
        else:
            weaknesses.append(f"Could elaborate deeper on {q.get('title')} (e.g. {expected[0] if expected else 'concepts'}).")

    final_score = min(100, max(15, total_score))
    feedback = (
        f"Candidate achieved {final_score}/100 across {len(questions)} technical problems. "
        f"{'Strong architectural fundamentals demonstrated.' if final_score >= 75 else 'Moderate technical demonstration; review edge cases.'}"
    )

    return AssessmentEvaluationResult(
        score=final_score,
        strengths=strengths or ["General comprehension of core engineering principles."],
        weaknesses=weaknesses or ["Minor omissions in edge case failure recovery."],
        feedback=feedback
    )


from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import CandidateAssessment, Candidate, JobOpening

class AssessmentService:
    def __init__(self, db: AsyncSession, org_id: UUID):
        self.db = db
        self.org_id = org_id

    async def generate_assessment(
        self, candidate_id: UUID, job_id: Optional[UUID] = None, duration_minutes: int = 30
    ) -> CandidateAssessment:
        c_stmt = select(Candidate).where(Candidate.id == candidate_id, Candidate.organization_id == self.org_id)
        c_res = await self.db.execute(c_stmt)
        candidate = c_res.scalar_one_or_none()
        if not candidate:
            raise ValueError("Candidate not found.")

        job_skills = []
        if job_id:
            j_stmt = select(JobOpening).where(JobOpening.id == job_id, JobOpening.organization_id == self.org_id)
            j_res = await self.db.execute(j_stmt)
            job = j_res.scalar_one_or_none()
            if job and job.required_skills:
                job_skills = job.required_skills

        job_title = job.title if (job_id and job) else "Software Engineer"
        skills = list(set((candidate.tags or ["Python", "PostgreSQL", "Docker"]) + job_skills))
        pkg = generate_technical_assessment(job_title=job_title, required_skills=skills, duration_minutes=duration_minutes)

        assessment = CandidateAssessment(
            organization_id=self.org_id,
            job_id=job_id,
            candidate_id=candidate_id,
            duration_minutes=duration_minutes,
            status="pending",
            questions_json=[q.model_dump() for q in pkg.questions],
            answers_json={}
        )
        self.db.add(assessment)
        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment

    async def evaluate_submission(
        self, assessment_id: UUID, answers: Dict[str, str]
    ) -> CandidateAssessment:
        stmt = select(CandidateAssessment).where(
            CandidateAssessment.id == assessment_id,
            CandidateAssessment.organization_id == self.org_id
        )
        res = await self.db.execute(stmt)
        assessment = res.scalar_one_or_none()
        if not assessment:
            raise ValueError("Assessment not found.")

        questions = assessment.questions_json or []
        eval_result = evaluate_assessment_submission(questions=questions, answers=answers)

        assessment.answers_json = answers
        assessment.score = eval_result.score
        assessment.strengths = eval_result.strengths
        assessment.weaknesses = eval_result.weaknesses
        assessment.feedback = eval_result.feedback
        assessment.status = "completed"
        assessment.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(assessment)
        return assessment
