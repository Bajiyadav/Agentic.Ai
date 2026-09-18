import pytest
from httpx import AsyncClient, ASGITransport
from src.api import app
from src.services.jd_service import (
    parse_job_description,
    _skill_matches_in_text,
    _extract_experience,
    _extract_seniority,
    _segment_jd_sections
)

# Test Sample 1: Full-length Senior Distributed Systems JD
SAMPLE_DISTRIBUTED_SYSTEMS_JD = """
About the Role:
We are seeking an exceptional Senior Distributed Systems Engineer to scale and maintain our high-throughput platform infrastructure.
You will collaborate closely with product and infrastructure teams to build mission-critical backend services handling millions of events daily.

Responsibilities:
• Architect, implement, and maintain resilient asynchronous APIs and microservices using Python, FastAPI, and Go.
• Optimize relational and document databases (PostgreSQL, Redis, ClickHouse) for low-latency queries and high availability.
• Build and maintain automated CI/CD pipelines, container orchestration with Kubernetes, and observability with OpenTelemetry and Prometheus.
• Partner with machine learning engineers to deploy real-time model inference endpoints with strict SLA requirements.
• Mentor junior engineers and champion code quality, test automation, and engineering excellence.

Required Qualifications:
• 5+ years of production experience in backend software engineering with modern Python (FastAPI, asyncio) or Go.
• Deep understanding of distributed systems fundamentals: consensus algorithms, event streaming (Kafka/RabbitMQ), and database isolation levels.
• Demonstrated track record optimizing high-traffic PostgreSQL databases, partitioning, and indexing strategies.
• Strong background with Docker containerization, cloud infrastructure (AWS/GCP), and Linux networking.

Preferred Qualifications:
• Experience with vector databases, LLM orchestration frameworks, or real-time WebSockets.
• Bachelor's or Master's degree in Computer Science or equivalent practical experience.
• Active contributions to open-source systems libraries.
"""

# Test Sample 2: Seniority and Experience range JD
SAMPLE_RANGE_JD = """
Position: Lead Cloud Architect
About us: Cloud innovations company.
Responsibilities:
- Design enterprise hybrid cloud infrastructure across multiple regions.
- Ensure strict zero-trust security and SOC 2 compliance.

Requirements:
- 7 to 10 years of software engineering experience.
- Deep expertise in AWS, Terraform, Kubernetes, and Golang.
- Master of Science in Computer Science or related degree.
- Certified AWS Solutions Architect Professional (AWS-SAP).

Nice to Have:
- Hands-on experience with Azure and Snowflake.
"""

# Test Sample 3: Bare Minimal JD with NO tech skills, NO experience numbers, NO education
SAMPLE_SPARSE_JD = """
Customer Operations Associate
About the role:
Assist customers with general questions and account access inquiries.

Responsibilities:
- Respond promptly to customer inquiries via email and chat.
- Maintain accurate logs of customer feedback.
"""

def test_jd_intelligence_extraction():
    """Verifies that all structured fields are extracted accurately from a complete JD."""
    parsed = parse_job_description(SAMPLE_DISTRIBUTED_SYSTEMS_JD)
    
    assert "Senior Distributed Systems Engineer" in parsed.title
    assert parsed.seniority == "Senior"
    assert parsed.experience_min_years == 5.0
    assert parsed.experience_max_years is None

    # Required skills presence
    assert "Python" in parsed.required_skills
    assert "Go" in parsed.required_skills
    assert "FastAPI" in parsed.required_skills
    assert "PostgreSQL" in parsed.required_skills
    assert "Docker" in parsed.required_skills
    assert "AWS" in parsed.required_skills
    assert "GCP" in parsed.required_skills

    # Strict separation: Preferred skills must NOT leak into required skills
    assert "WebSockets" in parsed.preferred_skills
    assert "WebSockets" not in parsed.required_skills

    # Responsibilities
    assert len(parsed.responsibilities) >= 4
    assert any("microservices" in r.lower() for r in parsed.responsibilities)

    # Education
    assert len(parsed.education) >= 1
    assert any("Computer Science" in edu for edu in parsed.education)

    # Categorized technology stack
    cats = parsed.technologies_by_category
    assert "Python" in cats["languages"]
    assert "Go" in cats["languages"]
    assert "FastAPI" in cats["frameworks"]
    assert "PostgreSQL" in cats["databases"]
    assert "Docker" in cats["cloud_devops"]
    assert "AWS" in cats["cloud_devops"]

def test_strict_required_vs_preferred_separation():
    """Guarantees preferred skills never appear in required skills and vice versa."""
    parsed = parse_job_description(SAMPLE_RANGE_JD)
    
    assert "Terraform" in parsed.required_skills
    assert "Kubernetes" in parsed.required_skills
    assert "Go" in parsed.required_skills  # Normalized from Golang
    assert "AWS" in parsed.required_skills

    assert "Azure" in parsed.preferred_skills
    assert "Snowflake" in parsed.preferred_skills
    
    # Critical verification: No overlap
    assert "Azure" not in parsed.required_skills
    assert "Snowflake" not in parsed.required_skills
    assert "Terraform" not in parsed.preferred_skills

def test_experience_range_and_certifications():
    """Verifies experience min/max ranges and certification extraction."""
    parsed = parse_job_description(SAMPLE_RANGE_JD)
    assert parsed.experience_min_years == 7.0
    assert parsed.experience_max_years == 10.0
    assert parsed.seniority == "Lead"

    # Education and Certifications
    assert any("Master" in edu for edu in parsed.education)
    assert any("AWS" in cert or "Architect" in cert for cert in parsed.certifications)

def test_zero_hallucination_on_sparse_jd():
    """
    CRITICAL: Guarantees AuditAgent NEVER invents requirements that are not in the JD.
    No fake default skills (['Python', 'Docker', 'PostgreSQL']) and no fake 3.0 years default!
    """
    parsed = parse_job_description(SAMPLE_SPARSE_JD)

    # Empty skills lists, not hallucinated defaults
    assert parsed.required_skills == []
    assert parsed.preferred_skills == []
    assert parsed.certifications == []
    assert parsed.education == []

    # Experience is None if unstated
    assert parsed.experience_min_years is None
    assert parsed.experience_max_years is None

def test_boundary_accuracy_for_short_skill_names():
    """Verifies boundary checks for keywords like 'Go', 'REST', 'Postgres'."""
    # Word 'good', 'going', 'algorithm', 'cargo' must NOT trigger Go
    assert not _skill_matches_in_text("Go", "Good communication skills and ongoing tasks.")
    assert not _skill_matches_in_text("Go", "Implemented advanced sorting algorithms.")
    assert not _skill_matches_in_text("Go", "Overseeing cargo logistics and deployment.")
    assert _skill_matches_in_text("Go", "Hands-on experience with Go or Golang backend.")

    # PostgreSQL / Postgres
    assert _skill_matches_in_text("PostgreSQL", "Experience tuning Postgres clusters.")
    assert _skill_matches_in_text("Postgres", "Managing PostgreSQL database migrations.")

    # REST APIs / REST
    assert _skill_matches_in_text("REST APIs", "Designing secure RESTful endpoints.")

@pytest.mark.asyncio
async def test_job_intelligence_api_endpoint():
    """Verifies GET /api/v1/jobs/{job_id}/intelligence returns authoritative structured requirements."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a hiring job opening
        create_resp = await client.post(
            "/api/v1/jobs",
            json={
                "title": "Staff Platform Architect",
                "department": "Platform Engineering",
                "location": "New York, NY / Remote",
                "work_model": "remote",
                "seniority": "Staff",
                "raw_jd_text": SAMPLE_DISTRIBUTED_SYSTEMS_JD
            }
        )
        assert create_resp.status_code == 200, create_resp.text
        job_data = create_resp.json()
        job_id = job_data["id"]

        # 2. Fetch structured intelligence for this job
        intel_resp = await client.get(f"/api/v1/jobs/{job_id}/intelligence")
        assert intel_resp.status_code == 200, intel_resp.text
        intel = intel_resp.json()

        assert intel["job_id"] == job_id
        assert intel["title"] == "Staff Platform Architect"
        assert intel["experience_min_years"] == 5.0
        assert "Python" in intel["required_skills"]
        assert "Go" in intel["required_skills"]
        assert "FastAPI" in intel["required_skills"]
        assert "WebSockets" in intel["preferred_skills"]
        assert "WebSockets" not in intel["required_skills"]
        assert len(intel["responsibilities"]) >= 4
        assert len(intel["education"]) >= 1
        assert "languages" in intel["technologies_by_category"]
        assert "Python" in intel["technologies_by_category"]["languages"]
        assert "Go" in intel["technologies_by_category"]["languages"]

@pytest.mark.asyncio
async def test_job_intelligence_404_for_unknown_job():
    """Verifies 404 is returned when requesting intelligence for a non-existent job ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/jobs/00000000-0000-0000-0000-000000000000/intelligence")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
