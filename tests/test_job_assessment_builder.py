import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from src.api import app
from src.services.job_assessment_service import JobAssessmentService


SAMPLE_RESUME_TEXT = b"""
Candidate Name: Alex Johnson
Email: alex.johnson@example.com
Phone: +1-555-0182
Current Role: Senior Backend Engineer
Location: Austin, TX

Summary:
Senior engineer with 6 years experience building scalable backend microservices.

Skills:
Languages: Python, Go
Frameworks: FastAPI, pytest
Databases: PostgreSQL, Redis
Cloud & DevOps: Docker

Experience:
Senior Software Engineer at CloudScale (2021 - Present)
Engineered REST APIs using FastAPI and optimized PostgreSQL database queries.
"""


@pytest.mark.asyncio
async def test_job_assessment_get_or_create_draft():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a job first
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Backend Systems Engineer",
            "department": "Infrastructure",
            "raw_jd_text": "We need a Backend Systems Engineer proficient in Python, FastAPI, and PostgreSQL to scale microservices."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Retrieve assessment (should auto-create draft)
        res = await client.get(f"/api/v1/jobs/{job_id}/assessment")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == job_id
        assert data["status"] == "draft"
        assert "Backend Systems Engineer" in data["title"]
        assert isinstance(data["questions"], list)


@pytest.mark.asyncio
async def test_job_assessment_404_on_invalid_job():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        random_job_id = str(uuid.uuid4())
        res = await client.get(f"/api/v1/jobs/{random_job_id}/assessment")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_anti_hallucination_jd_question_generation():
    """Verify that generated questions only test skills present in the Job Description,
    never inventing unmentioned technologies like Kubernetes, Rust, or AWS."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Job description strictly mentions Python, FastAPI, PostgreSQL, Redis
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Python API Developer",
            "department": "Platform",
            "raw_jd_text": (
                "Role: Python API Developer\n"
                "Required Skills: Python, FastAPI, PostgreSQL\n"
                "Preferred Skills: Redis caching\n"
                "Responsibilities: Build REST APIs with FastAPI and optimize PostgreSQL database queries."
            )
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Generate questions from JD
        gen_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd")
        assert gen_res.status_code == 200
        assessment = gen_res.json()
        questions = assessment["questions"]
        assert len(questions) >= 3

        allowed_skills = {"python", "fastapi", "postgresql", "postgres", "redis", "sql", "api", "rest"}
        forbidden_skills = {"kubernetes", "k8s", "rust", "aws", "gcp", "azure", "graphql", "solidity", "c++"}

        for q in questions:
            skill = (q.get("skill_tested") or "").lower()
            prompt = (q.get("prompt") or "").lower()
            relevance = (q.get("relevance") or "").lower()

            # Every question must have relevance justification
            assert relevance != "", f"Question {q['id']} missing relevance justification"
            assert "requirement" in relevance or "job" in relevance or "role" in relevance or "skill" in relevance

            # Assert no forbidden/unmentioned technology hallucination
            for forbidden in forbidden_skills:
                assert forbidden not in skill, f"Hallucinated technology '{forbidden}' found in skill_tested: {skill}"
                assert forbidden not in prompt, f"Hallucinated technology '{forbidden}' found in prompt: {prompt}"

            # Verify skill classification
            assert q.get("skill_type") in ["required", "preferred"]


@pytest.mark.asyncio
async def test_question_crud_and_reorder():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Full Stack Engineer",
            "department": "Core",
            "raw_jd_text": "Full stack role requiring TypeScript and Python."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Add Question 1 (MCQ)
        q1_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/questions", json={
            "type": "mcq",
            "prompt": "What is the primary benefit of TypeScript interfaces?",
            "skill_tested": "TypeScript",
            "skill_type": "required",
            "difficulty": "easy",
            "points": 10,
            "options": ["Runtime type checking", "Compile-time type safety", "Faster execution", "Garbage collection"],
            "correct_option": 1,
            "explanation": "TypeScript interfaces define contracts verified at compile time.",
            "relevance": "TypeScript is required by the Job Description."
        })
        assert q1_res.status_code == 201
        q1_id = q1_res.json()["question_id"]

        # Add Question 2 (Coding)
        q2_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/questions", json={
            "type": "coding",
            "prompt": "Implement reverse_string(s: str) -> str",
            "skill_tested": "Python",
            "skill_type": "required",
            "difficulty": "easy",
            "points": 20,
            "starter_code": {"python": "def reverse_string(s: str) -> str:\n    pass"},
            "test_cases": [
                {"input": "hello", "expected_output": "olleh", "hidden": False},
                {"input": "world", "expected_output": "dlrow", "hidden": True}
            ],
            "relevance": "Required Python coding proficiency."
        })
        assert q2_res.status_code == 201
        q2_id = q2_res.json()["question_id"]

        # Verify both questions exist
        assess_res = await client.get(f"/api/v1/jobs/{job_id}/assessment")
        assert len(assess_res.json()["questions"]) == 2
        assert assess_res.json()["questions"][0]["id"] == q1_id
        assert assess_res.json()["questions"][1]["id"] == q2_id

        # Update Question 1
        edit_res = await client.put(f"/api/v1/jobs/{job_id}/assessment/questions/{q1_id}", json={
            "type": "mcq",
            "prompt": "What is the primary benefit of TypeScript interfaces in production?",
            "skill_tested": "TypeScript",
            "skill_type": "required",
            "difficulty": "medium",
            "points": 15,
            "options": ["Runtime verification", "Static compile-time type safety", "Faster execution", "Automatic memory"],
            "correct_option": 1,
            "explanation": "Compile-time checking prevents runtime bugs.",
            "relevance": "Direct TS requirement."
        })
        assert edit_res.status_code == 200

        # Reorder Questions (Put Q2 first, Q1 second)
        reorder_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/reorder", json={
            "question_ids": [q2_id, q1_id]
        })
        assert reorder_res.status_code == 200

        # Verify reordered in GET
        assess_after = await client.get(f"/api/v1/jobs/{job_id}/assessment")
        questions_after = assess_after.json()["questions"]
        assert questions_after[0]["id"] == q2_id
        assert questions_after[1]["id"] == q1_id
        assert questions_after[1]["points"] == 15

        # Delete Question 1
        del_res = await client.delete(f"/api/v1/jobs/{job_id}/assessment/questions/{q1_id}")
        assert del_res.status_code == 200
        assess_final = await client.get(f"/api/v1/jobs/{job_id}/assessment")
        assert len(assess_final.json()["questions"]) == 1
        assert assess_final.json()["questions"][0]["id"] == q2_id


@pytest.mark.asyncio
async def test_publish_validation_rules():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job with empty assessment
        job_res = await client.post("/api/v1/jobs", json={
            "title": "DevOps Architect",
            "department": "Platform",
            "raw_jd_text": "DevOps role requiring CI/CD and automation."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Attempt to publish empty assessment -> should fail with 400
        pub_fail = await client.post(f"/api/v1/jobs/{job_id}/assessment/publish")
        assert pub_fail.status_code == 400
        assert "at least one question" in pub_fail.json()["detail"].lower()

        # Add valid question
        await client.post(f"/api/v1/jobs/{job_id}/assessment/questions", json={
            "type": "mcq",
            "prompt": "What does a CI/CD pipeline automate?",
            "skill_tested": "CI/CD",
            "skill_type": "required",
            "difficulty": "easy",
            "points": 10,
            "options": ["Code builds", "Code testing", "Deployment", "All of the above"],
            "correct_option": 3,
            "explanation": "CI/CD automates build, test, and release.",
            "relevance": "Core DevOps requirement."
        })

        # Publish should now succeed
        pub_ok = await client.post(f"/api/v1/jobs/{job_id}/assessment/publish")
        assert pub_ok.status_code == 200
        published = pub_ok.json()
        assert published["status"] == "published"
        assert published["published_at"] is not None


@pytest.mark.asyncio
async def test_candidate_invitation_requires_published_assessment():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job without publishing assessment
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Data Analyst",
            "department": "Analytics",
            "raw_jd_text": "SQL and Tableau analysis."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Upload candidate under job
        files = {"file": ("analyst.txt", SAMPLE_RESUME_TEXT, "text/plain")}
        cand_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/upload", files=files)
        assert cand_res.status_code == 201
        cand_id = cand_res.json()["candidate_id"]

        # Try to invite before publishing -> 400
        inv_fail = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/invite-assessment")
        assert inv_fail.status_code == 400
        assert "published assessment" in inv_fail.json()["detail"].lower()


@pytest.mark.asyncio
async def test_candidate_invitation_success_and_sanitized_view():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job and publish assessment
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Senior Frontend Developer",
            "department": "Web",
            "raw_jd_text": "React, TypeScript, CSS frontend developer."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Generate and publish assessment
        await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd")
        pub_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/publish")
        assert pub_res.status_code == 200

        # Upload candidate
        files = {"file": ("cand.txt", SAMPLE_RESUME_TEXT, "text/plain")}
        cand_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/upload", files=files)
        assert cand_res.status_code == 201
        cand_id = cand_res.json()["candidate_id"]

        # Invite candidate
        inv_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/invite-assessment")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()
        assert "token" in inv_data
        assert "otp" in inv_data
        assert len(inv_data["otp"]) == 6
        assessment_instance_id = inv_data["assessment_id"]

        # Query candidate assessment under job
        query_res = await client.get(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/assessment")
        assert query_res.status_code == 200
        q_data = query_res.json()
        assert q_data["published_assessment"] is not None
        assert q_data["candidate_assessment"]["status"] == "invited"
        assert q_data["candidate_assessment"]["otp"] == inv_data["otp"]

        # Verify candidate view is SANITIZED (zero leaks of answers or hidden test cases)
        view_res = await client.get(f"/api/v1/assessments/{assessment_instance_id}/candidate-view?token={inv_data['token']}")
        assert view_res.status_code == 200
        view_data = view_res.json()
        assert view_data["assessment_title"] is not None
        assert view_data["job_title"] == "Senior Frontend Developer"

        for q in view_data["questions"]:
            assert "correct_option" not in q, f"Security leak: correct_option exposed in question {q['id']}"
            assert "explanation" not in q, f"Security leak: explanation exposed in question {q['id']}"
            for tc in q.get("test_cases", []):
                assert not tc.get("hidden", False), f"Security leak: hidden test case exposed in question {q['id']}"


@pytest.mark.asyncio
async def test_candidate_submission_and_strict_non_scoring_boundary():
    """Verify assessment submission completes and tests pass,
    AND verifies that NO final match score or recommendation (Shortlist/Reject) is computed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create Job & Publish Assessment
        job_res = await client.post("/api/v1/jobs", json={
            "title": "QA Automation Engineer",
            "department": "Quality",
            "raw_jd_text": "Python pytest automation testing."
        })
        assert job_res.status_code == 200
        job_id = job_res.json()["id"]

        # Add single MCQ
        await client.post(f"/api/v1/jobs/{job_id}/assessment/questions", json={
            "type": "mcq",
            "prompt": "Which decorator is used in pytest for fixtures?",
            "skill_tested": "pytest",
            "skill_type": "required",
            "difficulty": "easy",
            "points": 10,
            "options": ["@pytest.fixture", "@pytest.test", "@pytest.setup", "@pytest.mock"],
            "correct_option": 0,
            "explanation": "@pytest.fixture declares a fixture function.",
            "relevance": "Pytest fixture knowledge."
        })
        await client.post(f"/api/v1/jobs/{job_id}/assessment/publish")

        # Upload candidate & invite
        files = {"file": ("cand.txt", SAMPLE_RESUME_TEXT, "text/plain")}
        cand_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/upload", files=files)
        assert cand_res.status_code == 201
        cand_id = cand_res.json()["candidate_id"]

        inv_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/invite-assessment")
        inv_data = inv_res.json()
        assess_id = inv_data["assessment_id"]

        # Submit candidate answers
        sub_res = await client.post(f"/api/v1/assessments/{assess_id}/submit", json={
            "token": inv_data["token"],
            "answers": {
                "0": {"answer": 0}
            }
        })
        assert sub_res.status_code == 200
        result = sub_res.json()

        assert result["status"] == "completed"
        assert result["score"] >= 0

        # STRICT PROHIBITIONS:
        # 1. No final candidate Job Match score
        assert "job_match_score" not in result
        assert "final_score" not in result
        assert "match_percentage" not in result

        # 2. No final recommendation (SHORTLIST / REVIEW / REJECT)
        assert "recommendation" not in result
        assert "hiring_decision" not in result

        # Check job candidate assessment status
        cand_assess_res = await client.get(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/assessment")
        assert cand_assess_res.status_code == 200
        ca_data = cand_assess_res.json()["candidate_assessment"]
        assert ca_data["status"] == "completed"
