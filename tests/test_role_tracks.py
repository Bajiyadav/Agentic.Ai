"""
Unit and integration tests for role-specific assessment tracks:
- 20 distinct industry tracks:
    1. software_engineer
    2. data_engineer
    3. frontend_engineer
    4. ml_engineer
    5. devops_sre
    6. fullstack_engineer
    7. security_engineer
    8. data_analyst
    9. qa_automation_engineer
    10. mobile_engineer
    11. cloud_architect
    12. database_administrator
    13. blockchain_engineer
    14. embedded_iot_engineer
    15. nlp_engineer
    16. computer_vision_engineer
    17. platform_engineer
    18. data_scientist
    19. api_integrations_engineer
    20. game_developer
- Every role includes the 5 types of exams/challenges:
    1. Multiple Choice Question (MCQ - Core Concepts)
    2. Multiple Choice Question (MCQ - System Architecture)
    3. Algorithmic Coding & DSA Challenge
    4. Interactive SQL / Database Query Challenge
    5. Code Bug Fixing & Debugging / Threat Defense Challenge
- 10 distinct customizable question modalities
"""

import pytest
from src.services.assessment_service import (
    EXAM_TRACKS,
    QUESTION_MODALITIES,
    get_question_modalities,
    get_exam_tracks_meta,
    detect_exam_track,
    get_questions_for_track,
    evaluate_assessment_submission,
)
from src.services.sandbox_service import SandboxService


def test_exam_tracks_30_roles_structure():
    """Verify that all 30 exam tracks exist with 5 questions per role covering the 5 challenge types."""
    expected_roles = [
        "software_engineer",
        "data_engineer",
        "frontend_engineer",
        "ml_engineer",
        "devops_sre",
        "fullstack_engineer",
        "security_engineer",
        "data_analyst",
        "qa_automation_engineer",
        "mobile_engineer",
        "cloud_architect",
        "database_administrator",
        "blockchain_engineer",
        "embedded_iot_engineer",
        "nlp_engineer",
        "computer_vision_engineer",
        "platform_engineer",
        "data_scientist",
        "api_integrations_engineer",
        "game_developer",
        "site_reliability_engineer",
        "cybersecurity_analyst",
        "network_engineer",
        "aiops_mlops_engineer",
        "big_data_architect",
        "crm_enterprise_developer",
        "ar_vr_engineer",
        "fintech_quant_developer",
        "bioinformatics_engineer",
        "robotics_autonomous_engineer",
    ]
    assert len(EXAM_TRACKS) == 30
    assert set(EXAM_TRACKS.keys()) == set(expected_roles)

    for role_id, track in EXAM_TRACKS.items():
        assert "role_name" in track or "title" in track
        assert "track_id" in track
        questions = track["questions"]
        assert len(questions) == 5, f"{role_id} must have exactly 5 questions"

        # Verify challenge types for every single role
        mcqs = [q for q in questions if q.type == "mcq"]
        coding = [q for q in questions if q.type in ("coding", "code")]
        sql = [q for q in questions if q.type == "sql"]
        debugging = [q for q in questions if q.type in ("debugging", "debug") or getattr(q, "modality", None) in ("code_debugging", "security_audit", "resilience_fault_tolerance")]

        assert len(mcqs) == 2, f"{role_id} must have 2 MCQs (Fundamentals + Architecture)"
        assert len(coding) >= 1, f"{role_id} must have at least 1 coding/DSA challenge"
        assert len(sql) >= 1, f"{role_id} must have at least 1 SQL challenge"
        assert len(debugging) >= 1, f"{role_id} must have at least 1 debugging/threat challenge"

        # Verify MCQs have options and correct_option
        for q in mcqs:
            assert len(q.options) >= 3
            assert q.correct_option is not None

        # Verify challenges have test cases
        challenges = [q for q in questions if q.type != "mcq"]
        for q in challenges:
            assert len(q.test_cases) >= 1


def test_question_modalities_customization():
    """Verify that 10 distinct question modalities are available for exam customization."""
    modalities = get_question_modalities()
    assert len(modalities) == 10
    modality_ids = [m["id"] for m in modalities]
    expected_ids = [
        "mcq_fundamentals",
        "mcq_architecture",
        "dsa_algorithms",
        "sql_window_cte",
        "sql_aggregation_analytics",
        "code_debugging",
        "security_audit",
        "performance_optimization",
        "resilience_fault_tolerance",
        "data_transformation",
    ]
    assert set(modality_ids) == set(expected_ids)


def test_data_engineer_sql_sandbox_execution():
    """Verify that the Data Engineer SQL challenge executes against SQLite in-memory sandbox."""
    de_track = EXAM_TRACKS["data_engineer"]
    sql_q = de_track["questions"][3]
    assert sql_q.type == "sql"

    correct_sql_query = """
    WITH ranked AS (
        SELECT department, name, salary,
               DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) as rank
        FROM employees
    )
    SELECT department, name, salary, rank
    FROM ranked
    WHERE rank <= 2
    ORDER BY department ASC, salary DESC, name ASC;
    """

    test_cases_dicts = [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in sql_q.test_cases]
    results = SandboxService.execute_code(
        language="sql",
        code=correct_sql_query,
        test_cases=test_cases_dicts,
    )

    assert results.tests_passed == len(sql_q.test_cases)
    assert results.all_passed is True
    assert results.success is True


def test_software_engineer_two_sum_dsa():
    """Verify Software Engineer DSA coding question executes in Python sandbox."""
    swe_track = EXAM_TRACKS["software_engineer"]
    coding_q = swe_track["questions"][2]
    assert coding_q.type == "coding"

    two_sum_code = """
def solution(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        comp = target - num
        if comp in seen:
            return [seen[comp], i]
        seen[num] = i
    return []
"""
    test_cases_dicts = [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in coding_q.test_cases]
    results = SandboxService.execute_code(
        language="python",
        code=two_sum_code,
        test_cases=test_cases_dicts,
    )
    assert results.all_passed is True
    assert results.tests_passed == len(coding_q.test_cases)


def test_software_engineer_debugging_solution():
    """Verify Software Engineer sliding window rate limiter debugging solution executes in Python sandbox."""
    swe_track = EXAM_TRACKS["software_engineer"]
    debug_q = swe_track["questions"][4]
    assert debug_q.type == "debugging"

    fixed_code = """
def solution(timestamps, max_requests, window_sec):
    allowed = []
    q = []
    for t in timestamps:
        while q and q[0] <= t - window_sec:
            q.pop(0)
        if len(q) < max_requests:
            q.append(t)
            allowed.append(True)
        else:
            allowed.append(False)
    return allowed
"""
    test_cases_dicts = [tc.model_dump() if hasattr(tc, 'model_dump') else tc for tc in debug_q.test_cases]
    results = SandboxService.execute_code(
        language="python",
        code=fixed_code,
        test_cases=test_cases_dicts,
    )
    assert results.all_passed is True
    assert results.tests_passed == len(debug_q.test_cases)


def test_detect_exam_track_all_20_roles():
    """Verify dynamic keyword detection for all 20 candidate role tracks."""
    mappings = [
        ("Senior Data Engineer", ["SQL", "Airflow", "Spark"], "data_engineer"),
        ("React Frontend Specialist", ["TypeScript", "CSS"], "frontend_engineer"),
        ("Machine Learning Scientist", ["PyTorch", "NLP"], "ml_engineer"),
        ("Site Reliability Engineer", ["Kubernetes", "Linux"], "devops_sre"),
        ("Full Stack Developer", ["Node", "React"], "fullstack_engineer"),
        ("Cybersecurity Analyst", ["AppSec", "OWASP"], "security_engineer"),
        ("Senior BI Analyst", ["Tableau", "SQL"], "data_analyst"),
        ("Lead SDET / QA Automation Engineer", ["Selenium", "Pytest"], "qa_automation_engineer"),
        ("iOS Mobile Architect", ["Swift", "CoreData"], "mobile_engineer"),
        ("Backend Software Engineer", ["Algorithms", "FastAPI"], "software_engineer"),
        ("Enterprise Cloud Solutions Architect", ["AWS", "Terraform", "GCP"], "cloud_architect"),
        ("Lead Database Administrator", ["PostgreSQL", "Replication", "WAL"], "database_administrator"),
        ("Senior NLP Research Engineer", ["Transformers", "HuggingFace", "BERT"], "nlp_engineer"),
        ("Computer Vision Specialist", ["OpenCV", "YOLO", "CNN"], "computer_vision_engineer"),
        ("Smart Contract Solidity Developer", ["Solidity", "EVM", "Web3"], "blockchain_engineer"),
        ("Firmware & Embedded Systems Engineer", ["C++", "RTOS", "UART"], "embedded_iot_engineer"),
        ("Core Platform Infrastructure Engineer", ["Kubernetes", "CRDs", "Platform"], "platform_engineer"),
        ("Principal Data Scientist", ["Statistics", "Regression", "R"], "data_scientist"),
        ("Partner API Integrations Engineer", ["REST", "Webhooks", "OAuth2"], "api_integrations_engineer"),
        ("Lead 3D Game Developer", ["Unreal", "Unity", "C++"], "game_developer"),
    ]

    for title, skills, expected_track in mappings:
        detected = detect_exam_track(title, skills)
        assert detected == expected_track, f"Expected {expected_track} for '{title}' with {skills}, got {detected}"
