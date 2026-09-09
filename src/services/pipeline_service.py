import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import PipelineStage, Candidate, Application, Audit

logger = logging.getLogger("auditagent.pipeline")

ALLOWED_STAGES = [
    "applied",
    "ai_screened",
    "screened",
    "review",
    "shortlist",
    "assessment",
    "interview",
    "tech_interview",
    "final_interview",
    "offer",
    "hired",
    "rejected"
]

class PipelineService:
    """
    Manages the recruitment Kanban pipeline, stage progression, and status tracking for candidates.
    """

    def __init__(self, db: AsyncSession, org_id: UUID):
        self.db = db
        self.org_id = org_id

    async def get_pipeline_board(self, job_id: Optional[UUID] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Returns all candidate cards grouped by pipeline stage for the Kanban board.
        """
        # Fetch pipeline stages
        stmt = (
            select(PipelineStage, Candidate, Application)
            .join(Candidate, PipelineStage.candidate_id == Candidate.id)
            .join(Application, PipelineStage.application_id == Application.id)
            .where(PipelineStage.organization_id == self.org_id)
        )
        if job_id:
            stmt = stmt.where(Application.job_id == job_id)

        res = await self.db.execute(stmt)
        board: Dict[str, List[Dict[str, Any]]] = {stage: [] for stage in ALLOWED_STAGES}

        for p_stage, candidate, application in res.all():
            # Get latest audit score if available
            audit_stmt = (
                select(Audit)
                .where(Audit.candidate_id == candidate.id, Audit.organization_id == self.org_id)
                .order_by(Audit.created_at.desc())
                .limit(1)
            )
            audit_res = await self.db.execute(audit_stmt)
            audit = audit_res.scalar_one_or_none()

            card = {
                "id": str(candidate.id),
                "name": candidate.name,
                "pipeline_id": str(p_stage.id),
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "candidate_email": candidate.email,
                "github_handle": candidate.github_username or "candidate",
                "github_username": candidate.github_username or "candidate",
                "application_id": str(application.id),
                "stage": p_stage.stage,
                "notes": p_stage.notes,
                "audit_score": audit.overall_score if audit else None,
                "overall_score": audit.overall_score if audit else None,
                "audit_verdict": getattr(audit, "ai_recommendation", None) if audit else None,
                "recommendation": getattr(audit, "ai_recommendation", None) if audit else None,
                "red_flag_count": 0,
                "updated_at": p_stage.updated_at.isoformat() if p_stage.updated_at else None
            }

            stage_key = p_stage.stage if p_stage.stage in board else "applied"
            board[stage_key].append(card)

        return board

    async def transition_stage(
        self,
        candidate_id: UUID,
        new_stage: str,
        user_id: Optional[UUID] = None,
        notes: Optional[str] = None
    ) -> PipelineStage:
        """
        Transitions a candidate to a new stage in the recruitment pipeline.
        """
        if new_stage not in ALLOWED_STAGES:
            raise ValueError(f"Invalid stage '{new_stage}'. Allowed: {ALLOWED_STAGES}")

        stmt = select(PipelineStage).where(
            PipelineStage.candidate_id == candidate_id,
            PipelineStage.organization_id == self.org_id
        ).order_by(PipelineStage.updated_at.desc()).limit(1)

        res = await self.db.execute(stmt)
        p_stage = res.scalar_one_or_none()

        if p_stage:
            p_stage.stage = new_stage
            p_stage.updated_by = user_id
            p_stage.updated_at = datetime.now(timezone.utc)
            if notes:
                p_stage.notes = notes
        else:
            # Check or create application
            app_stmt = select(Application).where(
                Application.candidate_id == candidate_id,
                Application.organization_id == self.org_id
            ).limit(1)
            app_res = await self.db.execute(app_stmt)
            app = app_res.scalar_one_or_none()
            if not app:
                app = Application(
                    organization_id=self.org_id,
                    candidate_id=candidate_id,
                    status="in_review"
                )
                self.db.add(app)
                await self.db.flush()

            p_stage = PipelineStage(
                organization_id=self.org_id,
                application_id=app.id,
                candidate_id=candidate_id,
                stage=new_stage,
                notes=notes,
                updated_by=user_id
            )
            self.db.add(p_stage)

        await self.db.commit()
        await self.db.refresh(p_stage)
        return p_stage
