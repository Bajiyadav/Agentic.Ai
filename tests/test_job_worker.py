import uuid
import base64
import pytest
from sqlalchemy import select

from src.db.session import async_session_factory
from src.db.models import Organization, Job, Audit
from src.services.job_worker import enqueue_job, fetch_and_process_next_job, process_job

@pytest.mark.asyncio
async def test_job_worker_queue_and_execution():
    org_id = uuid.uuid4()
    org_slug = f"job-test-{org_id.hex[:6]}"

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Job Worker Corp",
            slug=org_slug,
            plan_tier="growth",
            monthly_resume_limit=50,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.commit()

    with open("sample_resume.pdf", "rb") as f:
        pdf_bytes = f.read()

    # 1. Enqueue a screening job
    payload = {
        "file_bytes_b64": base64.b64encode(pdf_bytes).decode("utf-8"),
        "filename": "sample_resume.pdf",
        "candidate_name_override": "Queued Worker Candidate",
        "github_user_override": "octocat",
        "job_title": "Distributed Systems Engineer",
        "source": "async_queue"
    }

    async with async_session_factory() as db:
        job = await enqueue_job(
            db=db,
            organization_id=org_id,
            job_type="screen_candidate",
            payload_json=payload
        )
        assert job.status == "queued"
        assert job.attempts == 0
        job_id = job.id

    # 2. Worker fetches and processes next job with SKIP LOCKED
    async with async_session_factory() as db:
        processed_job = await fetch_and_process_next_job(db)
        assert processed_job is not None
        assert processed_job.id == job_id
        assert processed_job.status == "completed"
        assert processed_job.attempts == 1
        assert processed_job.started_at is not None
        assert processed_job.completed_at is not None
        assert processed_job.error_message is None

    # 3. Verify that the screening resulted in a persistent Audit in PostgreSQL
    async with async_session_factory() as db:
        audit_stmt = select(Audit).where(Audit.organization_id == org_id)
        audit = (await db.execute(audit_stmt)).scalar_one_or_none()
        assert audit is not None
        assert audit.overall_score >= 0

@pytest.mark.asyncio
async def test_job_worker_failure_and_retry_exhaustion():
    org_id = uuid.uuid4()
    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Retry Corp",
            slug=f"retry-{org_id.hex[:6]}",
            plan_tier="starter",
            monthly_resume_limit=10,
            monthly_resumes_used=0,
            is_active=True
        )
        db.add(org)
        await db.commit()

    # Enqueue a malformed job that will raise an error
    bad_payload = {
        "file_bytes_b64": "NOT_VALID_BASE64_BYTES!!!",
        "filename": "broken.pdf"
    }

    async with async_session_factory() as db:
        job = await enqueue_job(
            db=db,
            organization_id=org_id,
            job_type="screen_candidate",
            payload_json=bad_payload,
            max_attempts=2
        )
        job_id = job.id

    # Attempt 1: Should fail and return to 'queued'
    async with async_session_factory() as db:
        j1 = await db.get(Job, job_id)
        await process_job(db, j1)
        assert j1.attempts == 1
        assert j1.status == "queued"
        assert j1.error_message is not None

    # Attempt 2: Should fail and transition to 'failed' because max_attempts=2
    async with async_session_factory() as db:
        j2 = await db.get(Job, job_id)
        await process_job(db, j2)
        assert j2.attempts == 2
        assert j2.status == "failed"
        assert j2.error_message is not None
