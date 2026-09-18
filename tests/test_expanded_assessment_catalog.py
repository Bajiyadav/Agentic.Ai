"""
Test Suite: Expanded Assessment Catalog (20 MCQs, 2 DSA, Debugging & SQL)

Validates:
1. 20 MCQs per technical position track (10 fundamentals + 10 architecture).
2. 2 Algorithmic DSA coding challenges per track.
3. 1 Hands-on code debugging challenge per track.
4. 1 Interactive SQL sandbox challenge per track.
5. Publishing validity and integrity checks.
"""

import uuid
import pytest
from src.services.expanded_question_bank import (
    build_software_engineer_bank,
    build_data_engineer_bank,
    get_expanded_track_questions
)
from src.services.job_assessment_service import JobAssessmentService
from src.db.models import JobOpening, JobAssessment


def test_software_engineer_expanded_bank_composition():
    """Validates that SWE question bank contains 20 MCQs + 2 DSA + 1 Debugging + 1 SQL."""
    questions = build_software_engineer_bank()
    
    assert len(questions) == 24, f"Expected 24 total questions, got {len(questions)}"
    
    mcqs = [q for q in questions if q.type == "mcq"]
    dsas = [q for q in questions if q.type == "coding" and q.modality == "dsa_algorithms"]
    debugs = [q for q in questions if q.type == "debugging"]
    sqls = [q for q in questions if q.type == "sql"]
    
    assert len(mcqs) == 20, f"Expected 20 MCQs, got {len(mcqs)}"
    assert len(dsas) == 2, f"Expected 2 DSA challenges, got {len(dsas)}"
    assert len(debugs) == 1, f"Expected 1 Debugging challenge, got {len(debugs)}"
    assert len(sqls) == 1, f"Expected 1 SQL challenge, got {len(sqls)}"
    
    # Check 10 fundamentals and 10 architecture breakdown
    fund_mcqs = [q for q in mcqs if q.modality == "mcq_fundamentals"]
    arch_mcqs = [q for q in mcqs if q.modality == "mcq_architecture"]
    assert len(fund_mcqs) == 10, f"Expected 10 fundamentals MCQs, got {len(fund_mcqs)}"
    assert len(arch_mcqs) == 10, f"Expected 10 architecture MCQs, got {len(arch_mcqs)}"

    # Validate MCQ integrity
    for q in mcqs:
        assert len(q.options) >= 2, f"MCQ {q.id} has insufficient options"
        assert 0 <= q.correct_option < len(q.options), f"MCQ {q.id} invalid correct_option"
        assert q.explanation, f"MCQ {q.id} missing explanation"
        assert q.time_limit_minutes > 0

    # Validate DSA integrity
    for q in dsas:
        assert "python" in q.starter_code, f"DSA {q.id} missing python starter code"
        assert len(q.test_cases) >= 2, f"DSA {q.id} has fewer than 2 test cases"
        assert q.time_limit_minutes >= 10

    # Validate Debugging integrity
    for q in debugs:
        assert "python" in q.starter_code, f"Debug {q.id} missing starter code"
        assert len(q.test_cases) >= 1


def test_data_engineer_expanded_bank_composition():
    """Validates that Data Engineer question bank contains 20 MCQs + 2 DSA + 1 Debugging + 1 SQL."""
    questions = build_data_engineer_bank()
    assert len(questions) == 24
    
    mcqs = [q for q in questions if q.type == "mcq"]
    dsas = [q for q in questions if q.type == "coding" and q.modality == "dsa_algorithms"]
    debugs = [q for q in questions if q.type == "debugging"]
    sqls = [q for q in questions if q.type == "sql"]
    
    assert len(mcqs) == 20
    assert len(dsas) == 2
    assert len(debugs) == 1
    assert len(sqls) == 1


def test_generate_full_comprehensive_assessment_for_job():
    """Validates JobAssessmentService generates the 24-question suite and passes publishing validation."""
    job = JobOpening(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        title="Senior Distributed Systems Engineer",
        department="Platform Infrastructure",
        raw_jd_text="Looking for an engineer experienced in Python, Concurrency, PostgreSQL, and Distributed Systems.",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Distributed Systems"]
    )
    
    questions = JobAssessmentService.generate_full_comprehensive_assessment(job)
    assert len(questions) == 24
    
    # Create assessment and validate publishing
    assessment = JobAssessment(
        id=uuid.uuid4(),
        organization_id=job.organization_id,
        job_id=job.id,
        title=f"{job.title} Comprehensive Assessment",
        questions_json=questions,
        duration_minutes=90,
        skills_covered=job.required_skills,
        status="DRAFT"
    )
    
    is_valid, errors = JobAssessmentService.validate_assessment_for_publishing(assessment)
    assert is_valid is True, f"Validation failed with errors: {errors}"
    assert len(errors) == 0
