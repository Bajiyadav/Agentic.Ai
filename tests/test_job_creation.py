import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from src.api import app

REALISTIC_LONG_JD = """
About the Role:
We are seeking an exceptional Senior Distributed Systems Engineer to design, scale, and maintain our high-throughput platform infrastructure.
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
""".strip()


@pytest.mark.asyncio
async def test_job_creation_success():
    """Test creating a hiring job with full JD and optional metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "title": "Senior Distributed Systems Engineer",
            "department": "Core Infrastructure",
            "location": "San Francisco, CA / Remote",
            "work_model": "hybrid",
            "seniority": "Senior",
            "min_years_experience": 5.0,
            "raw_jd_text": REALISTIC_LONG_JD
        }
        res = await ac.post("/api/v1/jobs", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()

        assert "id" in data
        assert uuid.UUID(data["id"])  # Valid UUID
        assert data["title"] == "Senior Distributed Systems Engineer"
        assert data["department"] == "Core Infrastructure"
        assert data["location"] == "San Francisco, CA / Remote"
        assert data["work_model"] == "hybrid"
        assert data["seniority"] == "Senior"
        assert data["min_years_experience"] == 5.0
        assert data["status"] == "active"
        assert data["created_at"] is not None

        # Verify full description was NOT truncated
        assert data["full_description"] == REALISTIC_LONG_JD
        assert "• Architect, implement, and maintain resilient asynchronous APIs" in data["full_description"]
        assert "Preferred Qualifications:" in data["full_description"]

        job_id = data["id"]

        # Verify retrieval via GET /api/v1/jobs/{job_id}
        get_res = await ac.get(f"/api/v1/jobs/{job_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == job_id
        assert get_data["title"] == data["title"]
        assert get_data["full_description"] == REALISTIC_LONG_JD
        assert get_data["location"] == "San Francisco, CA / Remote"
        assert get_data["status"] == "active"

        # Verify listing in GET /api/v1/jobs
        list_res = await ac.get("/api/v1/jobs")
        assert list_res.status_code == 200
        jobs = list_res.json()
        matching = [j for j in jobs if j["id"] == job_id]
        assert len(matching) == 1
        assert matching[0]["title"] == "Senior Distributed Systems Engineer"


@pytest.mark.asyncio
async def test_job_creation_validation_empty_title():
    """Test that empty or whitespace title is rejected with 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Completely empty title
        res = await ac.post("/api/v1/jobs", json={
            "title": "",
            "raw_jd_text": "Some valid job description with enough context."
        })
        assert res.status_code == 422
        assert "title" in res.text.lower()

        # Whitespace-only title
        res_ws = await ac.post("/api/v1/jobs", json={
            "title": "   \n\t  ",
            "raw_jd_text": "Some valid job description with enough context."
        })
        assert res_ws.status_code == 422
        assert "title" in res_ws.text.lower()


@pytest.mark.asyncio
async def test_job_creation_validation_empty_jd():
    """Test that empty or whitespace JD is rejected with 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Completely empty JD
        res = await ac.post("/api/v1/jobs", json={
            "title": "Lead Software Engineer",
            "raw_jd_text": ""
        })
        assert res.status_code == 422
        assert "description" in res.text.lower()

        # Whitespace-only JD
        res_ws = await ac.post("/api/v1/jobs", json={
            "title": "Lead Software Engineer",
            "raw_jd_text": "   \n\n\t  "
        })
        assert res_ws.status_code == 422
        assert "description" in res_ws.text.lower()


@pytest.mark.asyncio
async def test_job_get_not_found():
    """Test retrieving non-existent job ID returns 404."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        random_id = str(uuid.uuid4())
        res = await ac.get(f"/api/v1/jobs/{random_id}")
        assert res.status_code == 404
        assert "not found" in res.text.lower()
