import pytest
from starlette.testclient import TestClient
from src.api import app
from src.services.campus_assessment_catalog import CAMPUS_GRADUATE_TRACK, build_campus_graduate_questions
from src.services.assessment_service import (
    get_exam_tracks_meta,
    get_questions_for_track,
    detect_exam_track,
    evaluate_assessment_submission,
)


def test_campus_graduate_track_structure():
    """Verify that Campus & Graduate track has the exact 4 modules, 56 questions, and 70 minutes duration."""
    track = CAMPUS_GRADUATE_TRACK
    assert track["track_id"] == "campus_graduate_engineer"
    assert track["duration_minutes"] == 70
    assert track["total_questions"] == 56

    questions = track["questions"]
    assert len(questions) == 56

    # Verify 4 exact module sections
    english_qs = [q for q in questions if q.section == "english"]
    logical_qs = [q for q in questions if q.section == "logical"]
    quant_qs = [q for q in questions if q.section == "quantitative"]
    ds_qs = [q for q in questions if q.section == "data_structures"]

    assert len(english_qs) == 12, "English Comprehension must have exactly 12 questions"
    assert len(logical_qs) == 12, "Logical Ability must have exactly 12 questions"
    assert len(quant_qs) == 14, "Quantitative Ability must have exactly 14 questions"
    assert len(ds_qs) == 18, "Data Structures must have exactly 18 questions"

    # Verify time per section
    breakdown = track["section_breakdown"]
    assert breakdown["english"]["minutes"] == 15
    assert breakdown["logical"]["minutes"] == 15
    assert breakdown["quantitative"]["minutes"] == 20
    assert breakdown["data_structures"]["minutes"] == 20

    # Total time check
    total_section_mins = sum(b["minutes"] for b in breakdown.values())
    assert total_section_mins == 70


def test_campus_questions_quality_and_integrity():
    """Verify all 56 questions are MCQs with 4 options, valid correct option index, and explanations."""
    questions = build_campus_graduate_questions()
    assert len(questions) == 56

    for idx, q in enumerate(questions):
        assert q.type == "mcq", f"Question {q.id} must be MCQ"
        assert len(q.options) == 4, f"Question {q.id} must have exactly 4 options"
        assert q.correct_option in [0, 1, 2, 3], f"Question {q.id} must have correct_option between 0 and 3"
        assert q.prompt and len(q.prompt.strip()) > 10, f"Question {q.id} must have a valid prompt"
        assert q.explanation and len(q.explanation.strip()) > 5, f"Question {q.id} must have an explanation"
        assert q.section in ["english", "logical", "quantitative", "data_structures"]


def test_campus_track_detection():
    """Verify detect_exam_track correctly routes campus, fresher, and graduate roles."""
    assert detect_exam_track("Campus Graduate Software Engineer") == "campus_graduate_engineer"
    assert detect_exam_track("Junior Backend Developer") == "campus_graduate_engineer"
    assert detect_exam_track("Graduate Engineer Trainee") == "campus_graduate_engineer"
    assert detect_exam_track("Entry-Level Software Engineer") == "campus_graduate_engineer"
    assert detect_exam_track("Fresher Programmer") == "campus_graduate_engineer"
    assert detect_exam_track("Associate Software Engineer") == "campus_graduate_engineer"
    assert detect_exam_track("Software Engineering Intern") == "campus_graduate_engineer"


def test_campus_track_in_tracks_meta():
    """Verify get_exam_tracks_meta exposes campus_graduate_engineer."""
    meta = get_exam_tracks_meta()
    track_ids = [m["track_id"] for m in meta]
    assert "campus_graduate_engineer" in track_ids

    campus_meta = next(m for m in meta if m["track_id"] == "campus_graduate_engineer")
    assert campus_meta["total_questions"] == 56
    assert campus_meta["duration_minutes"] == 70
    assert len(campus_meta["sections"]) == 4


def test_candidate_view_api_endpoint():
    """Verify /api/v1/assessments/demo/candidate-view returns the full 56 questions for campus track."""
    client = TestClient(app)
    response = client.get("/api/v1/assessments/demo/candidate-view?role=campus_graduate_engineer")
    assert response.status_code == 200

    data = response.json()
    assert data["role_track"] == "campus_graduate_engineer"
    assert data["duration_minutes"] == 70
    assert len(data["questions"]) == 56

    # Verify sections present in question payload
    sections = {q["section"] for q in data["questions"]}
    assert sections == {"english", "logical", "quantitative", "data_structures"}


def test_campus_assessment_evaluation():
    """Verify evaluate_assessment_submission scores campus MCQ answers accurately."""
    questions_dump = [q.model_dump() for q in CAMPUS_GRADUATE_TRACK["questions"]]

    # Perfect answers
    perfect_answers = {q["id"]: str(q["correct_option"]) for q in questions_dump}
    result = evaluate_assessment_submission(questions_dump, perfect_answers)
    assert result.score >= 95
    assert len(result.strengths) > 10

    # Empty answers
    empty_result = evaluate_assessment_submission(questions_dump, {})
    assert empty_result.score == 0
