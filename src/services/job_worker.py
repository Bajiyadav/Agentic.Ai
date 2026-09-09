import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import async_session_factory
from ..db.models import Job, utc_now
from .screening_service import screen_candidate_core

logger = logging.getLogger(__name__)

async def enqueue_job(
    db: AsyncSession,
    organization_id: uuid.UUID,
    job_type: str,
    payload_json: Dict[str, Any],
    max_attempts: int = 3
) -> Job:
    """Enqueues a persistent background job into PostgreSQL."""
    job = Job(
        organization_id=organization_id,
        job_type=job_type,
        payload_json=payload_json,
        status="queued",
        attempts=0,
        max_attempts=max_attempts
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job

async def process_job(db: AsyncSession, job: Job) -> bool:
    """Executes a single job according to its job_type."""
    job.status = "processing"
    job.started_at = utc_now()
    job.attempts += 1
    await db.commit()

    try:
        if job.job_type == "screen_candidate":
            payload = job.payload_json
            file_bytes = base64.b64decode(payload["file_bytes_b64"])
            await screen_candidate_core(
                db=db,
                organization_id=job.organization_id,
                file_bytes=file_bytes,
                filename=payload.get("filename", "resume.pdf"),
                github_user_override=payload.get("github_user_override"),
                candidate_name_override=payload.get("candidate_name_override"),
                candidate_email_override=payload.get("candidate_email_override"),
                job_title=payload.get("job_title", "Software Engineer"),
                source=payload.get("source", "upload"),
                actor_id=uuid.UUID(payload["actor_id"]) if payload.get("actor_id") else None
            )

        elif job.job_type == "email_sync":
            # Synced via email_connector for specific org
            pass

        job.status = "completed"
        job.completed_at = utc_now()
        job.error_message = None
        await db.commit()
        return True

    except Exception as e:
        logger.exception(f"Job {job.id} failed: {e}")
        job.error_message = str(e)
        if job.attempts >= job.max_attempts:
            job.status = "failed"
        else:
            job.status = "queued"
        await db.commit()
        return False

async def fetch_and_process_next_job(db: AsyncSession) -> Optional[Job]:
    """Fetches the next queued job with row locking (SKIP LOCKED) to prevent race conditions across workers."""
    stmt = (
        select(Job)
        .where(Job.status == "queued")
        .order_by(Job.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if job:
        await process_job(db, job)
    return job

async def start_job_worker_loop(poll_interval: float = 2.0, max_iterations: Optional[int] = None):
    """Background worker daemon loop for processing queued jobs."""
    iterations = 0
    while True:
        try:
            async with async_session_factory() as db:
                job = await fetch_and_process_next_job(db)
                if not job:
                    await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Worker iteration error: {e}")
            await asyncio.sleep(poll_interval)

        iterations += 1
        if max_iterations and iterations >= max_iterations:
            break
