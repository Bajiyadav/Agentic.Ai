import pytest
from src.agent_1_resume_parser import CandidateClaims
from src.agent_2_code_auditor import GitHubEvidence
from src.agent_3_evaluator import _deterministic_evaluator, evaluate_candidate
from main import run_screening_pipeline

def test_company_required_skills_evaluation():
    claims = CandidateClaims(
        name="Test Dev",
        years_experience=4.0,
        claimed_languages=["Python", "JavaScript"],
        claimed_frameworks=["FastAPI"],
        claimed_tools=["Docker"]
    )
    evidence = GitHubEvidence(
        username="testdev",
        languages_detected={"Python": 12, "HTML": 3},
        total_public_repos=5,
        original_repos_count=4,
        forked_repos_count=1,
        total_stars=50,
        documentation_ratio=0.8,
        recent_activity_count=2,
        profile_found=True
    )

    required_skills = ["Python", "FastAPI", "Docker", "Kubernetes"]
    scorecard = _deterministic_evaluator(
        claims=claims,
        evidence=evidence,
        required_skills=required_skills,
        target_role="Senior Backend Engineer",
        min_experience=3.0
    )

    # Assert company skills mapping
    assert scorecard.target_role == "Senior Backend Engineer"
    assert scorecard.company_required_skills == required_skills
    # Python is detected in GitHub evidence -> verified
    assert "Python" in scorecard.verified_company_skills
    # FastAPI & Docker are claimed on resume -> matched but unverified
    assert "FastAPI" in scorecard.matched_company_skills
    assert "Docker" in scorecard.matched_company_skills
    assert "FastAPI" not in scorecard.verified_company_skills
    # Kubernetes is absent -> missing
    assert "Kubernetes" in scorecard.missing_company_skills

    # Assert company match score is calculated
    assert scorecard.company_skills_match_score is not None
    # 100 (Python) + 50 (FastAPI) + 50 (Docker) + 0 (Kubernetes) = 200 / 4 = 50
    assert scorecard.company_skills_match_score == 50

    # Assert red flags include missing skill
    assert any("Kubernetes" in flag for flag in scorecard.red_flags)
    # Assert green flags include verified skill
    assert any("Python" in flag for flag in scorecard.green_flags)

def test_pipeline_with_company_skills():
    scorecard = run_screening_pipeline(
        pdf_path="sample_resume.pdf",
        github_username="octocat",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        target_role="Backend Developer",
        min_experience=2.0,
        save_report=False
    )
    assert scorecard.target_role == "Backend Developer"
    assert "Python" in scorecard.company_required_skills
    assert scorecard.company_skills_match_score is not None

def test_screening_with_job_description_paragraph():
    from src.services.jd_service import parse_job_description
    jd_text = (
        "We are hiring a Senior Backend Engineer with 4+ years of experience in Python, "
        "FastAPI, Docker, and PostgreSQL to scale our real-time microservices."
    )
    parsed_jd = parse_job_description(jd_text)
    assert "Python" in parsed_jd.required_skills
    assert "Docker" in parsed_jd.required_skills
    assert parsed_jd.experience_min_years == 4.0

    scorecard = run_screening_pipeline(
        pdf_path="sample_resume.pdf",
        github_username="octocat",
        required_skills=parsed_jd.required_skills,
        target_role=parsed_jd.title,
        min_experience=parsed_jd.experience_min_years,
        save_report=False
    )
    assert "Python" in scorecard.company_required_skills
    assert scorecard.company_skills_match_score is not None

def test_unrelated_academic_lab_document_rejected():
    """Verifies that an unrelated document (e.g. SQL lab manual) is detected as invalid, scored 0, and rejected."""
    from src.agent_1_resume_parser import _heuristic_resume_parser
    from src.agent_2_code_auditor import audit_github
    from src.email_connector import DraftResponseGenerator

    lab_text = (
        "### Experiment 2 Types Of Constraints\n"
        "This document provides the SQL commands and expected outcomes for each lab exercise.\n"
        "You should execute these commands in your SQL environment (e.g., MySQL, PostgreSQL, SQL Server) and observe the results."
    )
    claims = _heuristic_resume_parser(lab_text)
    assert claims.is_valid_resume is False
    assert claims.document_type == "ACADEMIC_LAB_OR_EXERCISE"
    assert claims.name == "Non-Resume Document"
    assert len(claims.claimed_languages) == 0

    evidence = audit_github("none")
    scorecard = _deterministic_evaluator(claims, evidence, required_skills=["Python", "Docker"])
    assert scorecard.overall_score == 0
    assert scorecard.recommendation == "REJECT"
    assert any("NOT a valid professional resume/CV" in flag for flag in scorecard.red_flags)

    # Draft email must request a proper resume, NOT invite for an interview!
    draft = DraftResponseGenerator.create_draft(
        candidate_name=claims.name,
        recipient_email="applicant@example.com",
        verdict=scorecard.recommendation,
        score=scorecard.overall_score
    )
    assert "Action Required: Resume Submission" in draft.subject
    assert "unable to review your application" in draft.body_text
    assert "Interview Invitation" not in draft.subject

def test_strict_company_requirements_rejection():
    """Verifies that candidates who meet 0 company required skills are strictly rejected."""
    claims = CandidateClaims(
        name="Frontend Specialist",
        years_experience=2.0,
        claimed_languages=["HTML", "CSS"],
        claimed_frameworks=["Bootstrap"],
        claimed_tools=[]
    )
    evidence = GitHubEvidence(
        username="frontdev",
        languages_detected={"HTML": 10, "CSS": 5},
        total_public_repos=3,
        original_repos_count=3,
        total_stars=5,
        documentation_ratio=0.5,
        recent_activity_count=1,
        profile_found=True
    )
    # Company strictly requires Python and Kubernetes backend skills
    scorecard = _deterministic_evaluator(
        claims=claims,
        evidence=evidence,
        required_skills=["Python", "Kubernetes", "PostgreSQL"],
        target_role="Senior Platform Engineer"
    )
    assert scorecard.company_skills_match_score == 0
    assert scorecard.overall_score <= 25
    assert scorecard.recommendation == "REJECT"
    assert any("failed 100% of company required skills" in flag for flag in scorecard.red_flags)

