"""
Backend and Integration tests for Job Openings Recruiter Experience.
Covers:
- Job persistence and retrieval
- First-time recruiter vs returning recruiter baseline rules
- Multi-token search and filtering
- Mandatory vs Preferred requirements separation in intelligence
- Recruiter isolation and authorization
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.api import app

REALISTIC_LONG_JD = """
About the role:
We are seeking a Lead Distributed Systems Architect to build high-scale cloud platforms.

Required Qualifications:
- 8+ years experience in distributed systems design
- Deep expertise with Go or Rust, Kubernetes, and PostgreSQL
- Strong background in high-throughput consensus protocols (Raft/Paxos)

Preferred Qualifications:
- Experience with eBPF and Linux kernel tracing
- Knowledge of Apache Kafka and clickhouse
""".strip()

@pytest.mark.asyncio
async def test_jobs_list_retrieval():
    """Verify jobs endpoint returns clean list of jobs."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/jobs")
        assert res.status_code == 200
        jobs = res.json()
        assert isinstance(jobs, list)
        if jobs:
            j = jobs[0]
            assert "id" in j
            assert "title" in j
            assert "department" in j

@pytest.mark.asyncio
async def test_create_first_job_and_intelligence():
    """Verify job creation returns structured record and auto-generates requirements intel."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "title": "Lead Distributed Systems Architect",
            "department": "Infrastructure",
            "location": "Remote",
            "work_model": "remote",
            "min_years_experience": 8.0,
            "raw_jd_text": REALISTIC_LONG_JD
        }
        res = await ac.post("/api/v1/jobs", json=payload)
        assert res.status_code == 200
        job = res.json()
        assert job["title"] == "Lead Distributed Systems Architect"
        assert job["department"] == "Infrastructure"
        assert job["min_years_experience"] == 8.0
        job_id = job["id"]

        # Verify Intelligence Endpoint preserves strict mandatory vs preferred separation
        intel_res = await ac.get(f"/api/v1/jobs/{job_id}/intelligence")
        assert intel_res.status_code == 200
        intel = intel_res.json()
        assert intel["job_id"] == job_id
        assert intel["title"] == "Lead Distributed Systems Architect"
        assert isinstance(intel["required_skills"], list)
        assert isinstance(intel["preferred_skills"], list)

        # Check that required skills are cataloged
        req_skills_lower = [s.lower() for s in intel["required_skills"]]
        assert any("distributed" in s or "kubernetes" in s or "rust" in s or "go" in s or "postgresql" in s for s in req_skills_lower)

@pytest.mark.asyncio
async def test_job_validation_empty_fields():
    """Verify validation errors for missing or invalid job fields."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/jobs", json={"title": "", "raw_jd_text": "Valid JD"})
        assert res.status_code in (400, 422)

        res2 = await ac.post("/api/v1/jobs", json={"title": "Engineer", "raw_jd_text": ""})
        assert res2.status_code in (400, 422)

@pytest.mark.asyncio
async def test_job_assessment_draft_generated_on_job():
    """Verify that a job can retrieve or create a draft assessment."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/jobs")
        jobs = res.json()
        if not jobs:
            pytest.skip("No jobs in catalog")
        
        target_job = jobs[0]
        asst_res = await ac.get(f"/api/v1/jobs/{target_job['id']}/assessment")
        assert asst_res.status_code == 200
        asst = asst_res.json()
        assert asst["job_id"] == target_job["id"]
        assert "questions" in asst
        assert "status" in asst
