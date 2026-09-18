import pytest
from fastapi.testclient import TestClient
from src.api import app
from src.agent_2_code_auditor import (
    validate_github_url_or_username,
    verify_claims_against_github,
    RepoHighlight,
    GitHubEvidence,
    CandidateGitHubAuditResult,
)

client = TestClient(app)

def test_validate_github_url_or_username():
    # Valid formats
    valid, user, repo = validate_github_url_or_username("octocat")
    assert valid is True and user == "octocat" and repo is None

    valid, user, repo = validate_github_url_or_username("@octocat")
    assert valid is True and user == "octocat" and repo is None

    valid, user, repo = validate_github_url_or_username("https://github.com/octocat")
    assert valid is True and user == "octocat" and repo is None

    valid, user, repo = validate_github_url_or_username("github.com/octocat")
    assert valid is True and user == "octocat" and repo is None

    valid, user, repo = validate_github_url_or_username("https://github.com/octocat/Hello-World")
    assert valid is True and user == "octocat" and repo == "Hello-World"

    valid, user, repo = validate_github_url_or_username("octocat/Hello-World")
    assert valid is True and user == "octocat" and repo == "Hello-World"

    # Invalid / non-GitHub URLs
    valid, err, _ = validate_github_url_or_username("https://gitlab.com/octocat")
    assert valid is False and "Only official public GitHub URLs" in err

    valid, err, _ = validate_github_url_or_username("https://bitbucket.org/octocat/repo")
    assert valid is False and "Only official public GitHub URLs" in err

    valid, err, _ = validate_github_url_or_username("../../../etc/passwd")
    assert valid is False and "Invalid GitHub username" in err

    valid, err, _ = validate_github_url_or_username("<script>alert(1)</script>")
    assert valid is False and "Invalid GitHub username" in err

    valid, err, _ = validate_github_url_or_username("")
    assert valid is False and "cannot be empty" in err

def test_verify_claims_against_github_safety_rule():
    # Setup candidate resume claims
    claims = {
        "languages": ["Python", "Go", "Rust"],
        "frameworks": ["FastAPI", "Django", "Spring Boot"],
        "databases": ["PostgreSQL", "Cassandra"],
        "cloud_devops": ["Docker", "Kubernetes", "AWS"],
    }

    # Setup mock repo highlights
    top_repos = [
        RepoHighlight(
            name="distributed-fastapi-service",
            description="High-throughput asynchronous microservice with FastAPI, PostgreSQL, and Docker",
            stars=120,
            forks=15,
            language="Python",
            html_url="https://github.com/octocat/distributed-fastapi-service",
            detected_frameworks=["FastAPI", "SQLAlchemy", "Docker"],
            detected_files=["app/main.py", "requirements.txt", "Dockerfile", "alembic/env.py"],
            commit_samples=[
                {"message": "Add Dockerfile for multi-stage build", "date": "2026-08-01T10:00:00Z"},
                {"message": "Optimize PostgreSQL connection pooling", "date": "2026-08-02T10:00:00Z"},
                {"message": "feat: async endpoints with FastAPI", "date": "2026-08-03T10:00:00Z"}
            ]
        ),
        RepoHighlight(
            name="cloud-infra-k8s",
            description="Terraform and Kubernetes cluster configurations on AWS",
            stars=45,
            forks=8,
            language="HCL",
            html_url="https://github.com/octocat/cloud-infra-k8s",
            detected_frameworks=["Kubernetes", "AWS"],
            detected_files=["k8s/deployment.yaml", "terraform/main.tf"],
            commit_samples=[
                {"message": "Configure AWS EKS cluster", "date": "2026-07-01T10:00:00Z"},
                {"message": "Add Kubernetes deployment manifests", "date": "2026-07-02T10:00:00Z"}
            ]
        )
    ]

    languages = {"Python": 10, "HCL": 4}

    evidence = GitHubEvidence(
        username="octocat",
        profile_found=True,
        total_public_repos=2,
        original_repos_count=2,
        total_stars=165,
        languages_detected=languages,
        repo_highlights=top_repos
    )

    verifications = verify_claims_against_github(claims, evidence)

    # Convert to dict by claim name
    v_dict = {v.claim: v for v in verifications}

    # Python: should be Verified or Strong Evidence with files & repo
    assert "Python" in v_dict
    assert v_dict["Python"].status in ["Verified", "Strong Evidence"]
    assert "distributed-fastapi-service" in v_dict["Python"].repositories
    assert v_dict["Python"].confidence_score >= 0.8

    # FastAPI: should be Verified or Strong Evidence
    assert "FastAPI" in v_dict
    assert v_dict["FastAPI"].status in ["Verified", "Strong Evidence"]
    assert any("app/main.py" in f or "requirements.txt" in f for f in v_dict["FastAPI"].files)

    # Spring Boot: NOT in public repos -> MUST be 'No Public Evidence'
    assert "Spring Boot" in v_dict
    assert v_dict["Spring Boot"].status == "No Public Evidence"
    assert v_dict["Spring Boot"].confidence_score == 0.0
    # CRITICAL: Confirm safety explanation is present
    assert "does not imply the candidate lacks this skill" in v_dict["Spring Boot"].evidence_description
    assert "private repositories" in v_dict["Spring Boot"].evidence_description

    # Cassandra: NOT in public repos -> MUST be 'No Public Evidence'
    assert "Cassandra" in v_dict
    assert v_dict["Cassandra"].status == "No Public Evidence"
    assert "does not imply the candidate lacks this skill" in v_dict["Cassandra"].evidence_description

    # Docker & Kubernetes: should have evidence
    assert "Docker" in v_dict
    assert v_dict["Docker"].status in ["Verified", "Strong Evidence", "Moderate Evidence"]
    assert "Kubernetes" in v_dict
    assert v_dict["Kubernetes"].status in ["Verified", "Strong Evidence", "Moderate Evidence"]

def test_no_scoring_or_recommendation_present():
    """Verify that Test 5 strictly avoids qualification scores or shortlist recommendations."""
    claims = {"languages": ["Python"], "frameworks": ["FastAPI"]}
    top_repos = [
        RepoHighlight(
            name="my-service",
            description="FastAPI service",
            stars=10,
            forks=1,
            language="Python",
            html_url="https://github.com/octocat/my-service",
            detected_frameworks=["FastAPI"],
            detected_files=["main.py", "requirements.txt"],
            commit_samples=[{"message": "initial commit", "date": "2026-01-01T00:00:00Z"}]
        )
    ]
    evidence = GitHubEvidence(
        username="octocat",
        profile_found=True,
        total_public_repos=1,
        original_repos_count=1,
        total_stars=10,
        languages_detected={"Python": 1},
        repo_highlights=top_repos
    )
    verifications = verify_claims_against_github(claims, evidence)
    v_json = [v.model_dump() for v in verifications]

    for item in v_json:
        assert "score" not in item or item["confidence_score"] is not None  # only confidence_score allowed
        assert "job_match_score" not in item
        assert "recommendation" not in item
        assert "decision" not in item

def test_api_audit_github_flow_and_isolation():
    # 1. First get or create an active job
    jobs_res = client.get("/api/v1/jobs")
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()
    assert len(jobs) >= 2
    job_1_id = jobs[0]["id"]
    job_2_id = jobs[1]["id"]

    # 2. Upload a sample candidate resume to job 1 using clean reportlab PDF
    import io
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Alex Mercer")
    c.drawString(100, 735, "alex.mercer@example.com | 555-0199 | San Francisco, CA")
    c.drawString(100, 720, "Role: Senior Backend Systems Engineer")
    c.drawString(100, 700, "github.com/alexmercer-dev")
    c.drawString(100, 680, "Technical Skills:")
    c.drawString(100, 665, "Languages: Python, Go, Rust")
    c.drawString(100, 650, "Frameworks: FastAPI, SQLAlchemy, Gin")
    c.drawString(100, 635, "Databases: PostgreSQL, Redis")
    c.drawString(100, 620, "Cloud & DevOps: Docker, Kubernetes, AWS")
    c.drawString(100, 600, "Work Experience:")
    c.drawString(100, 585, "Lead Backend Engineer at CloudScale (2021-Present)")
    c.drawString(100, 570, "Built microservices in Go, Python, FastAPI, PostgreSQL, Kubernetes")
    c.save()
    buf.seek(0)
    pdf_content = buf.read()

    files = {"file": ("alex_mercer_resume.pdf", pdf_content, "application/pdf")}
    upload_res = client.post(f"/api/v1/jobs/{job_1_id}/candidates/upload", files=files)
    assert upload_res.status_code in [200, 201]
    candidate = upload_res.json()["candidate"]
    cand_id = candidate["id"]

    # 3. Call POST /api/v1/jobs/{job_1_id}/candidates/{cand_id}/audit-github
    audit_res = client.post(
        f"/api/v1/jobs/{job_1_id}/candidates/{cand_id}/audit-github",
        json={"github_url_or_username": "https://github.com/tiangolo"}
    )
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["status"] == "Completed"

    assert audit_data["candidate_id"] == cand_id
    assert audit_data["job_id"] == job_1_id
    assert audit_data["github_username"] == "tiangolo"
    assert audit_data["public_repos"] > 0
    assert len(audit_data["claims_verified"]) > 0

    # Verify claim items structure
    claims_list = audit_data["claims_verified"]
    status_set = {c["status"] for c in claims_list}
    assert any(s in ["Verified", "Strong Evidence", "Moderate Evidence"] for s in status_set)
    assert "No Public Evidence" in status_set

    # Verify GET endpoint retrieves the exact audit record for Job 1
    get_res = client.get(f"/api/v1/jobs/{job_1_id}/candidates/{cand_id}/audit-github")
    assert get_res.status_code == 200
    get_json = get_res.json()
    assert get_json["status"] == "Completed"
    assert get_json["candidate_id"] == cand_id
    assert get_json["job_id"] == job_1_id

    # 4. Job Isolation Verification: Job 2 must not have audit data for this candidate
    get_job2_res = client.get(f"/api/v1/jobs/{job_2_id}/candidates/{cand_id}/audit-github")
    assert get_job2_res.status_code == 200
    assert get_job2_res.json()["status"] == "Not Audited"
    assert len(get_job2_res.json()["claim_verifications"]) == 0

    # 5. Invalid URL error test with valid candidate
    res_bad_url = client.post(
        f"/api/v1/jobs/{job_1_id}/candidates/{cand_id}/audit-github",
        json={"github_url_or_username": "https://gitlab.com/alexmercer-dev"}
    )
    assert res_bad_url.status_code == 400
    assert "Only official public GitHub URLs" in res_bad_url.json()["detail"]

    # 6. Non-existent candidate returns 404
    res_bad_cand = client.post(
        f"/api/v1/jobs/{job_1_id}/candidates/00000000-0000-0000-0000-000000000000/audit-github",
        json={"github_url_or_username": "alexmercer-dev"}
    )
    assert res_bad_cand.status_code == 404
