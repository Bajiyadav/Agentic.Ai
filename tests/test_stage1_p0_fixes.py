"""
Comprehensive Regression Test Suite for Stage 1 P0 Issues:
- P0-1: JD Experience Requirement Crash / NoneType Handling & Formats
- P0-2: Database, Cloud, DevOps, and Infrastructure Skill Aggregation
- P0-3: No Public GitHub Handling (Neutral baseline, Never Auto-Reject, Scenarios A-F)
"""

import pytest
from src.agent_1_resume_parser import CandidateClaims
from src.agent_2_code_auditor import GitHubEvidence, RepoHighlight
from src.agent_3_evaluator import evaluate_candidate
from src.services.jd_service import (
    StructuredJobDescription,
    evaluate_candidate_job_fit,
    _extract_experience,
    parse_job_description
)
from src.services.tech_ontology import TechOntology
from src.services.job_match_evaluation_service import JobMatchEvaluationService


# ==============================================================================
# P0-1: JD EXPERIENCE REQUIREMENT TESTS
# ==============================================================================

class TestP01JDExperience:
    """Test experience extraction and evaluation across varied JD formats and missing values."""

    def test_p01_format_a_3_plus_years(self):
        """A. JD with '3+ years experience'."""
        text = "We are seeking a Backend Engineer with 3+ years experience in Python and PostgreSQL."
        min_y, max_y = _extract_experience(text)
        assert min_y == 3.0
        assert max_y is None

    def test_p01_format_b_5_years(self):
        """B. JD with '5 years experience'."""
        text = "Requirements: 5 years experience designing scalable distributed systems."
        min_y, max_y = _extract_experience(text)
        assert min_y == 5.0
        assert max_y is None

    def test_p01_format_c_no_experience_requirement(self):
        """C. JD with no experience requirement must not crash and must return (None, None)."""
        text = "Looking for a talented software developer skilled in Go and Kubernetes. Competitive salary."
        min_y, max_y = _extract_experience(text)
        assert min_y is None
        assert max_y is None

    def test_p01_format_d_malformed_experience_text(self):
        """D. JD with malformed experience text must safely return (None, None)."""
        malformed_samples = [
            "We value extensive experience in building software.",
            "Candidate must have experience with Python.",
            "Years of experience: many.",
            "Requires solid industry experience."
        ]
        for sample in malformed_samples:
            min_y, max_y = _extract_experience(sample)
            assert min_y is None, f"Expected None for: {sample}"
            assert max_y is None

    def test_p01_format_e_varied_valid_formats(self):
        """E. JD with experience expressed in different valid formats."""
        cases = [
            ("3-5 years of software engineering experience", (3.0, 5.0)),
            ("minimum 4 years of hands-on experience", (4.0, None)),
            ("at least 6 years of industry experience", (6.0, None)),
            ("Experience: 7+ years in cloud architecture", (7.0, None)),
            ("Requires 2 to 4 yrs experience", (2.0, 4.0)),
            ("No experience required. New graduates welcome.", (0.0, None)),
            ("0 years experience necessary for junior role", (0.0, None))
        ]
        for text, expected in cases:
            res = _extract_experience(text)
            assert res == expected, f"Failed for '{text}': got {res}, expected {expected}"

    def test_p01_matching_pipeline_no_experience_does_not_crash(self):
        """Pipeline must evaluate safely when JD has experience_min_years = None."""
        jd = StructuredJobDescription(
            title="Full Stack Engineer",
            seniority="Mid-Level",
            required_skills=["Python", "PostgreSQL", "Docker"],
            preferred_skills=["Redis"],
            experience_min_years=None,
            experience_max_years=None
        )
        claims = CandidateClaims(
            name="Jordan Lee",
            claimed_languages=["Python"],
            claimed_frameworks=[],
            claimed_databases=["PostgreSQL"],
            claimed_cloud_devops=["Docker"],
            claimed_tools=[],
            years_experience=3.0
        )
        evidence = GitHubEvidence(username="none", profile_found=False)

        # Must not raise TypeError: '>=' not supported between instances of 'float' and 'NoneType'
        result = evaluate_candidate_job_fit(claims, evidence, jd)
        assert result is not None
        assert result.experience_match_pct == 100
        assert "shortfall" not in " ".join(result.contradictions).lower()
        assert result.breakdown["relevant_experience"] == 100

    def test_p01_preserve_existing_behavior_when_experience_present(self):
        """Preserve exact shortfall calculation when experience requirement IS present."""
        jd = StructuredJobDescription(
            title="Senior Staff Engineer",
            seniority="Staff",
            required_skills=["Python"],
            preferred_skills=[],
            experience_min_years=8.0,
            experience_max_years=12.0
        )
        claims = CandidateClaims(
            name="Alex Junior",
            claimed_languages=["Python"],
            years_experience=2.0
        )
        evidence = GitHubEvidence(username="none", profile_found=False)

        result = evaluate_candidate_job_fit(claims, evidence, jd)
        # 2.0 yrs vs 8.0 yrs = 25% match
        assert result.experience_match_pct == 25
        assert any("shortfall" in c.lower() for c in result.contradictions)


# ==============================================================================
# P0-2: DATABASE / CLOUD / DEVOPS SKILL AGGREGATION TESTS
# ==============================================================================

class TestP02SkillAggregation:
    """Verify that databases, cloud, devops, and infrastructure skills flow into candidate sets and scoring."""

    def test_p02_all_5_skill_categories_flow_to_jd_matching(self):
        """Verify database, cloud, devops, tools, frameworks, and languages all flow into JD matching."""
        jd = StructuredJobDescription(
            title="DevOps & Data Platform Engineer",
            seniority="Senior",
            required_skills=["PostgreSQL", "Kubernetes", "Terraform", "FastAPI", "Python"],
            preferred_skills=["Redis", "AWS"],
            experience_min_years=4.0
        )
        claims = CandidateClaims(
            name="Morgan Taylor",
            claimed_languages=["Python"],
            claimed_frameworks=["FastAPI"],
            claimed_databases=["PostgreSQL", "Redis"],
            claimed_cloud_devops=["Kubernetes", "Terraform", "AWS"],
            claimed_tools=["Git", "Docker"],
            years_experience=5.0
        )
        evidence = GitHubEvidence(
            username="morgant",
            profile_found=True,
            total_public_repos=3,
            original_repos_count=2,
            documentation_ratio=0.8,
            languages_detected={"Python": 5000, "HCL": 2000}
        )

        result = evaluate_candidate_job_fit(claims, evidence, jd)

        # All 5 required skills must be matched (PostgreSQL, Kubernetes, Terraform, FastAPI, Python)
        assert result.matched_required_skills == ["PostgreSQL", "Kubernetes", "Terraform", "FastAPI", "Python"]
        assert result.missing_required_skills == []
        assert result.required_skills_match_pct == 100
        assert result.overall_match_pct >= 80

    def test_p02_job_match_evaluation_service_aggregation(self):
        """Verify JobMatchEvaluationService includes database and cloud/devops keys from parsed claims."""
        class MockCandidate:
            parsed_claims_json = {
                "claimed_languages": ["Python"],
                "claimed_frameworks": ["Django"],
                "claimed_databases": ["PostgreSQL", "MongoDB"],
                "claimed_cloud_devops": ["Docker", "Kubernetes", "AWS"],
                "claimed_tools": ["Git"]
            }
            github_username = "candidate123"

        parsed = MockCandidate.parsed_claims_json
        skill_keys = [
            "languages", "frameworks", "databases", "cloud_devops", "tools", "skills",
            "claimed_languages", "claimed_frameworks", "claimed_databases", "claimed_cloud_devops", "claimed_tools"
        ]
        aggregated = set()
        for k in skill_keys:
            for item in (parsed.get(k) or []):
                aggregated.add(JobMatchEvaluationService._normalize_skill(str(item)))

        assert "postgresql" in aggregated
        assert "mongodb" in aggregated
        assert "docker" in aggregated
        assert "kubernetes" in aggregated
        assert "aws" in aggregated

    def test_p02_database_cloud_ontology_normalization(self):
        """Verify TechOntology correctly canonicalizes database and cloud/devops aliases."""
        assert TechOntology.normalize("postgres") == "PostgreSQL"
        assert TechOntology.normalize("k8s") == "Kubernetes"
        assert TechOntology.normalize("amazon web services") == "AWS"
        assert TechOntology.normalize("mongo") == "MongoDB"
        assert TechOntology.normalize("terraform") == "Terraform"


# ==============================================================================
# P0-3: NO PUBLIC GITHUB MUST NOT AUTOMATICALLY REJECT TESTS (SCENARIOS A-F)
# ==============================================================================

class TestP03GitHubAvailabilityScenarios:
    """Test all scenarios A-F for GitHub availability vs skill match."""

    def test_scenario_a_strong_candidate_with_github(self):
        """Scenario A: Strong candidate + verified public GitHub -> SHORTLIST."""
        claims = CandidateClaims(
            name="Alice Verified",
            claimed_languages=["Python", "Go"],
            claimed_frameworks=["FastAPI"],
            claimed_databases=["PostgreSQL"],
            years_experience=5.0
        )
        evidence = GitHubEvidence(
            username="alicev",
            profile_found=True,
            total_public_repos=8,
            original_repos_count=6,
            documentation_ratio=0.85,
            total_stars=25,
            recent_activity_count=5,
            languages_detected={"Python": 15000, "Go": 12000},
            repo_highlights=[
                RepoHighlight(name="fastapi-core", html_url="https://github.com/alicev/fastapi-core", language="Python", detected_frameworks=["FastAPI"])
            ]
        )
        scorecard = evaluate_candidate(
            claims,
            evidence,
            required_skills=["Python", "Go", "FastAPI"],
            min_experience=3.0
        )
        assert scorecard.recommendation == "SHORTLIST"
        assert scorecard.overall_score >= 75
        assert scorecard.skills_match_score >= 80

    def test_scenario_b_strong_candidate_no_github_neutral_baseline(self):
        """Scenario B: Strong candidate + no GitHub -> REVIEW (NEVER 25/100 REJECT)."""
        claims = CandidateClaims(
            name="Bob Enterprise",
            claimed_languages=["Python", "Go"],
            claimed_frameworks=["FastAPI"],
            claimed_databases=["PostgreSQL"],
            years_experience=6.0
        )
        evidence = GitHubEvidence(
            username="none",
            profile_found=False,
            total_public_repos=0,
            original_repos_count=0
        )
        scorecard = evaluate_candidate(
            claims,
            evidence,
            required_skills=["Python", "Go", "FastAPI"],
            min_experience=3.0
        )
        # Must apply neutral baseline and NOT automatically reject with 25/100
        assert scorecard.recommendation == "REVIEW"
        assert scorecard.overall_score >= 50, f"Expected neutral score >= 50, got {scorecard.overall_score}"
        assert scorecard.consistency_score == 65
        assert scorecard.code_quality_score == 50

    def test_scenario_c_weak_candidate_with_github(self):
        """Scenario C: Weak candidate + GitHub -> REJECT (due to skill mismatch, not GitHub)."""
        claims = CandidateClaims(
            name="Charlie PHP",
            claimed_languages=["PHP"],
            claimed_frameworks=["Laravel"],
            years_experience=2.0
        )
        evidence = GitHubEvidence(
            username="charliep",
            profile_found=True,
            total_public_repos=4,
            original_repos_count=2,
            languages_detected={"PHP": 8000}
        )
        # Job requires Go and Kubernetes
        scorecard = evaluate_candidate(
            claims,
            evidence,
            required_skills=["Go", "Kubernetes"],
            min_experience=4.0
        )
        assert scorecard.recommendation == "REJECT"
        assert scorecard.overall_score <= 45

    def test_scenario_d_weak_candidate_no_github(self):
        """Scenario D: Weak candidate + no GitHub -> REJECT (rejected for skill failure, not solely GitHub)."""
        claims = CandidateClaims(
            name="David Mismatch",
            claimed_languages=["Ruby"],
            claimed_frameworks=["Rails"],
            years_experience=1.0
        )
        evidence = GitHubEvidence(
            username="none",
            profile_found=False,
            total_public_repos=0
        )
        # Job requires Go, Kubernetes, and Terraform
        scorecard = evaluate_candidate(
            claims,
            evidence,
            required_skills=["Go", "Kubernetes", "Terraform"],
            min_experience=5.0
        )
        assert scorecard.recommendation == "REJECT"
        assert scorecard.overall_score <= 45

    def test_scenario_e_candidate_with_github_url_but_unavailable_repo(self):
        """Scenario E: Candidate with GitHub URL but 0 public repos / private repo -> REVIEW."""
        claims = CandidateClaims(
            name="Emma Private",
            claimed_languages=["Python", "Rust"],
            claimed_frameworks=["FastAPI"],
            years_experience=4.0
        )
        evidence = GitHubEvidence(
            username="emmaprivate",
            profile_found=True,
            total_public_repos=0,
            original_repos_count=0
        )
        scorecard = evaluate_candidate(
            claims,
            evidence,
            required_skills=["Python", "FastAPI"],
            min_experience=3.0
        )
        # Zero public repos must NOT force 25/100 REJECT
        assert scorecard.recommendation == "REVIEW"
        assert scorecard.overall_score >= 50

    def test_scenario_f_candidate_with_malformed_github_url(self):
        """Scenario F: Candidate with malformed GitHub URL -> Safe fallback to neutral, no crash."""
        claims = CandidateClaims(
            name="Frank BrokenUrl",
            claimed_languages=["Java", "Spring Boot"],
            claimed_frameworks=["Spring Boot"],
            years_experience=5.0
        )
        # Malformed username parsed as 'none' or unverified
        evidence = GitHubEvidence(
            username="none",
            profile_found=False,
            api_rate_limited=False
        )
        scorecard = evaluate_candidate(
            claims,
            evidence,
            required_skills=["Java", "Spring Boot"],
            min_experience=4.0
        )
        assert scorecard.recommendation == "REVIEW"
        assert scorecard.overall_score >= 50
        assert not any("TypeError" in flag for flag in scorecard.red_flags)
