"""
Test Suite: Agent Accuracy, Deterministic Consistency, and Canonical Technology Ontology

Validates:
1. Zero-drift deterministic scoring across repeated evaluations (100% score consistency).
2. Canonical ontology alias normalization (Postgres -> PostgreSQL, Docker, Python).
3. Manifest marker resolution (Dockerfile -> Docker, asyncpg/psycopg2 -> PostgreSQL).
4. Provenance tracking in Claim vs Evidence items.
5. Safe handling of unavailable GitHub profiles (neutral Unavailable, never false penalty).
"""

import pytest
from src.services.tech_ontology import TechOntology
from src.agent_1_resume_parser import CandidateClaims
from src.agent_2_code_auditor import GitHubEvidence, RepoHighlight
from src.consensus_evaluator import run_consensus_evaluation
from src.services.screening_service import build_claim_evidence_items


def test_tech_ontology_normalization():
    """Validates that aliases resolve to standardized canonical technology names."""
    assert TechOntology.normalize("postgres") == "PostgreSQL"
    assert TechOntology.normalize("psql") == "PostgreSQL"
    assert TechOntology.normalize("postgresql") == "PostgreSQL"
    assert TechOntology.normalize("docker") == "Docker"
    assert TechOntology.normalize("python3") == "Python"
    assert TechOntology.normalize("py") == "Python"
    assert TechOntology.normalize("reactjs") == "React"
    assert TechOntology.normalize("k8s") == "Kubernetes"
    assert TechOntology.normalize("fast-api") == "FastAPI"
    assert TechOntology.normalize("golang") == "Go"


def test_manifest_marker_matching():
    """Validates that manifest files and dependencies accurately verify technologies."""
    # Docker matching via Dockerfile
    docker_match = TechOntology.match_manifest_evidence(
        "Docker",
        repo_files=["src/app.py", "Dockerfile", "requirements.txt"],
        repo_deps=[]
    )
    assert docker_match is not None
    assert "dockerfile" in docker_match.lower()

    # PostgreSQL matching via production dependency
    postgres_match = TechOntology.match_manifest_evidence(
        "PostgreSQL",
        repo_files=["src/main.py"],
        repo_deps=["fastapi", "asyncpg", "uvicorn"]
    )
    assert postgres_match is not None
    assert "asyncpg" in postgres_match.lower()

    # FastAPI matching via main.py
    fastapi_match = TechOntology.match_manifest_evidence(
        "FastAPI",
        repo_files=["main.py", "requirements.txt"],
        repo_deps=["fastapi"]
    )
    assert fastapi_match is not None


def test_zero_drift_scoring_consistency():
    """Validates that evaluating the exact same candidate 5 consecutive times yields identical scores (0 variance)."""
    claims = CandidateClaims(
        name="Alex Mercer",
        years_experience=6.0,
        claimed_languages=["Python", "TypeScript"],
        claimed_frameworks=["FastAPI", "React"],
        claimed_databases=["PostgreSQL", "Redis"],
        claimed_cloud_devops=["Docker", "AWS"],
        claimed_tools=["Git", "Pytest"],
        is_valid_resume=True
    )

    evidence = GitHubEvidence(
        username="alexmercer",
        profile_found=True,
        total_public_repos=10,
        original_repos_count=8,
        forked_repos_count=2,
        total_stars=45,
        languages_detected={"Python": 5, "TypeScript": 3},
        documentation_ratio=0.8,
        recent_activity_count=6,
        repo_highlights=[
            RepoHighlight(
                name="cloud-microservice",
                description="FastAPI backend with Postgres and Docker containerization",
                language="Python",
                stars=20,
                html_url="https://github.com/alexmercer/cloud-microservice",
                detected_frameworks=["FastAPI", "PostgreSQL", "Docker"],
                detected_files=["main.py", "Dockerfile", "docker-compose.yml", "requirements.txt"]
            )
        ]
    )

    required_skills = ["Python", "FastAPI", "Docker", "PostgreSQL"]

    # Run consensus evaluation 5 times
    scores = []
    recommendations = []
    for _ in range(5):
        result = run_consensus_evaluation(
            claims=claims,
            evidence=evidence,
            required_skills=required_skills,
            target_role="Senior Backend Engineer",
            min_experience=5.0
        )
        scores.append(result.scorecard.overall_score)
        recommendations.append(result.scorecard.recommendation)
        assert result.variance_points == 0  # 0 pts variance in deterministic mode

    # All scores must be identical
    assert len(set(scores)) == 1, f"Score drift detected across runs: {scores}"
    assert len(set(recommendations)) == 1, f"Recommendation drift detected: {recommendations}"
    assert scores[0] >= 80, f"Expected strong score for matching candidate, got {scores[0]}"


def test_claim_evidence_items_accuracy_with_manifests():
    """Validates that Docker, PostgreSQL, Python, and FastAPI are all accurately Verified via manifests and code."""
    claims = CandidateClaims(
        name="Sarah Chen",
        years_experience=5.0,
        claimed_languages=["python"],
        claimed_frameworks=["FastAPI"],
        claimed_databases=["postgres"],  # alias
        claimed_cloud_devops=["docker"],  # alias
        claimed_tools=["git"],
        is_valid_resume=True
    )

    evidence = GitHubEvidence(
        username="sarahchen",
        profile_found=True,
        total_public_repos=8,
        original_repos_count=6,
        forked_repos_count=2,
        total_stars=30,
        languages_detected={"Python": 4},
        documentation_ratio=0.85,
        recent_activity_count=5,
        repo_highlights=[
            RepoHighlight(
                name="fastapi-postgres-api",
                description="REST API service",
                language="Python",
                stars=15,
                html_url="https://github.com/sarahchen/fastapi-postgres-api",
                detected_frameworks=["FastAPI", "PostgreSQL"],
                detected_files=["main.py", "Dockerfile", "requirements.txt"]
            )
        ]
    )

    items = build_claim_evidence_items(
        claims=claims,
        evidence=evidence,
        required_skills=["Python", "Docker", "PostgreSQL", "Kubernetes"]
    )

    item_map = {item["skill"]: item for item in items}

    # Python: Verified (detected in language stats and repo)
    assert "Python" in item_map
    assert item_map["Python"]["status"] == "Verified"

    # Docker: Verified via Dockerfile manifest
    assert "Docker" in item_map
    assert item_map["Docker"]["status"] == "Verified"
    assert "repo" in item_map["Docker"]["evidence"].lower() or "dockerfile" in item_map["Docker"]["evidence"].lower()

    # PostgreSQL: Verified via frameworks/dependencies
    assert "PostgreSQL" in item_map
    assert item_map["PostgreSQL"]["status"] == "Verified"

    # Kubernetes: Required skill, not claimed and not in code -> Unverified / Missing
    assert "Kubernetes" in item_map
    assert item_map["Kubernetes"]["status"] == "Unverified"
    assert "Missing" in item_map["Kubernetes"]["evidence"]


def test_unavailable_github_profile_safe_neutral_status():
    """Validates that when GitHub profile is unavailable, skills are marked Unavailable with safe explanations."""
    claims = CandidateClaims(
        name="Jordan Lee",
        years_experience=4.0,
        claimed_languages=["Python", "Go"],
        claimed_frameworks=["Django"],
        is_valid_resume=True
    )

    unavailable_evidence = GitHubEvidence(
        username="none",
        profile_found=False,
        total_public_repos=0,
        original_repos_count=0,
        forked_repos_count=0,
        total_stars=0,
        languages_detected={},
        documentation_ratio=0.0,
        recent_activity_count=0
    )

    items = build_claim_evidence_items(
        claims=claims,
        evidence=unavailable_evidence,
        required_skills=["Python", "Django"]
    )

    for item in items:
        assert item["status"] == "Unavailable"
        assert "unavailable" in item["evidence"].lower()
        assert "unavailable" in item["notes"].lower()
