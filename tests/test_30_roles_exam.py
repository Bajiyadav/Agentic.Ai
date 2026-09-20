"""
End-to-End Automated Test: Exam Taking and Evaluation for All 30 Roles.

Validates that:
1. All 30 industry roles have complete 5-challenge assessments.
2. Every role's exam can be generated, submitted, and automatically graded.
3. Coding, SQL (SQLite in-memory), and Debugging challenges execute and pass in SandboxService.
4. Evaluation produces high composite scores, strengths, and feedback for each of the 30 roles.
"""

import pytest
from typing import Dict, Any, List
from src.services.assessment_service import (
    EXAM_TRACKS,
    get_exam_tracks_meta,
    evaluate_assessment_submission,
)
from src.services.sandbox_service import SandboxService


def test_30_roles_catalog_completeness():
    """Verify that all 30 roles exist and are fully populated in catalog and metadata."""
    assert len(EXAM_TRACKS) == 30, f"Expected 30 roles, got {len(EXAM_TRACKS)}"
    meta = get_exam_tracks_meta()
    # At least 30 roles (plus campus_graduate_engineer)
    assert len(meta) >= 30

    role_ids = list(EXAM_TRACKS.keys())
    for role_id in role_ids:
        track = EXAM_TRACKS[role_id]
        assert "track_id" in track
        assert "title" in track
        assert "description" in track
        assert "skills" in track
        assert len(track["skills"]) >= 3
        questions = track["questions"]
        assert len(questions) == 5, f"Role {role_id} must have exactly 5 questions"


@pytest.mark.parametrize("role_id", list(EXAM_TRACKS.keys()))
def test_take_and_grade_exam_for_role(role_id: str):
    """Simulate a candidate taking the exam for each role and verify automated grading."""
    track = EXAM_TRACKS[role_id]
    questions = track["questions"]
    q_dicts = [q.model_dump() if hasattr(q, "model_dump") else q for q in questions]

    answers: Dict[str, str] = {}

    for q in q_dicts:
        q_id = q["id"]
        q_type = q.get("type", "coding")

        if q_type == "mcq":
            correct_idx = q.get("correct_option", 0)
            options = q.get("options", [])
            answers[q_id] = options[correct_idx]

        elif q_type == "sql" or q.get("section") == "sql":
            starter = q.get("starter_code", {}).get("sql", "")
            answers[q_id] = starter

        elif q_type in ("coding", "debugging", "code"):
            starter = q.get("starter_code", {}).get("python", "")
            answers[q_id] = starter

    # Evaluate the submission using real SandboxService (SQLite and Python)
    result = evaluate_assessment_submission(
        questions=q_dicts,
        answers=answers
    )

    # Assert evaluation succeeds with high score
    assert result.score >= 80, f"Role {role_id} score was {result.score}, expected >= 80"
    assert len(result.strengths) >= 2, f"Role {role_id} should have recognized strengths"
    assert "Candidate achieved" in result.feedback or "score" in result.feedback.lower()
