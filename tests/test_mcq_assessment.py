import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from src.api import app
from src.db.session import async_session_factory
from src.db.models import Organization, User, Membership, Candidate, CandidateAssessment
from src.security import hash_password, create_access_token
from src.services.assessment_service import _get_preset_questions, evaluate_assessment_submission

@pytest.mark.asyncio
async def test_mcq_preset_generation_and_scoring():
    # 1. Preset generation test
    questions = _get_preset_questions(job_title="Senior Backend Engineer", skills=["Python", "PostgreSQL"], duration_minutes=30)
    assert len(questions) == 5
    mcq_questions = [q for q in questions if q.type == "mcq"]
    coding_questions = [q for q in questions if q.type == "coding"]

    assert len(mcq_questions) >= 2
    assert len(coding_questions) >= 1

    # Verify each MCQ has options and correct_option defined
    for mcq in mcq_questions:
        assert len(mcq.options) >= 4
        assert mcq.correct_option is not None
        assert 0 <= mcq.correct_option < len(mcq.options)

    # 2. Evaluation test: Correct MCQ answers
    correct_answers = {
        mcq.id: str(mcq.correct_option)
        for mcq in mcq_questions
    }
    res = evaluate_assessment_submission(
        [q.model_dump() for q in questions],
        correct_answers,
        sandbox_results=None
    )
    # 2 MCQs correctly answered out of 5 total questions = 2 * 20 = 40 pts
    assert res.score == 40
    assert any("Serializable" in s or "PostgreSQL" in s or "MCQ" in s for s in res.strengths)
    assert any("Concurrency" in s or "Event Loop" in s or "MCQ" in s for s in res.strengths)

    # 3. Evaluation test: Incorrect MCQ answers
    wrong_answers = {
        mcq_questions[0].id: str((mcq_questions[0].correct_option + 1) % len(mcq_questions[0].options)),
        mcq_questions[1].id: str((mcq_questions[1].correct_option + 1) % len(mcq_questions[1].options)),
    }
    w_res = evaluate_assessment_submission(
        [q.model_dump() for q in questions],
        wrong_answers,
        sandbox_results=None
    )
    assert w_res.score == 15  # min baseline score is 15
    assert len(w_res.weaknesses) >= 2


@pytest.mark.asyncio
async def test_candidate_view_sanitizes_mcq_answers():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    async with async_session_factory() as db:
        org = Organization(id=org_id, name="Security Tech", slug=f"sec-{org_id.hex[:6]}", plan_tier="enterprise", is_active=True)
        db.add(org)
        user = User(id=user_id, email=f"lead-{user_id.hex[:6]}@example.com", hashed_password=hash_password("Pass123!"), full_name="Lead Engineer", is_active=True)
        db.add(user)
        membership = Membership(user_id=user.id, organization_id=org.id, role="admin")
        db.add(membership)
        candidate = Candidate(id=candidate_id, organization_id=org.id, name="Test Candidate", email=f"cand-{candidate_id.hex[:6]}@example.com", tags=["Go", "PostgreSQL"])
        db.add(candidate)
        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "org": str(org_id), "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        gen_res = await ac.post("/api/v1/assessments/generate", headers=headers, json={
            "candidate_id": str(candidate_id),
            "duration_minutes": 20
        })
        assert gen_res.status_code == 200
        assessment_id = gen_res.json()["id"]
        access_token = gen_res.json()["access_token"]

        # Request candidate view
        view_res = await ac.get(f"/api/v1/assessments/{assessment_id}/candidate-view?token={access_token}")
        assert view_res.status_code == 200
        data = view_res.json()

        for q in data["questions"]:
            if q.get("type") == "mcq":
                # Must provide options for candidate selection
                assert len(q.get("options", [])) > 0
                # Must NOT leak correct_option or explanation to candidate
                assert "correct_option" not in q
                assert "explanation" not in q

@pytest.mark.asyncio
async def test_custom_domain_and_real_link_generation():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    async with async_session_factory() as db:
        org = Organization(id=org_id, name="Apex Hiring", slug=f"apex-{org_id.hex[:6]}", plan_tier="enterprise", is_active=True)
        db.add(org)
        user = User(id=user_id, email=f"talent-{user_id.hex[:6]}@example.com", hashed_password=hash_password("Pass123!"), full_name="Talent Lead", is_active=True)
        db.add(user)
        membership = Membership(user_id=user.id, organization_id=org.id, role="admin")
        db.add(membership)
        candidate = Candidate(id=candidate_id, organization_id=org.id, name="Samir Developer", email=f"samir-{candidate_id.hex[:6]}@example.com", tags=["Python", "Docker"])
        db.add(candidate)
        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "org": str(org_id), "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    custom_public_domain = "https://careers.mycompany.com"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Generate with custom domain
        gen_res = await ac.post("/api/v1/assessments/generate", headers=headers, json={
            "candidate_id": str(candidate_id),
            "duration_minutes": 30,
            "custom_domain": custom_public_domain
        })
        assert gen_res.status_code == 200
        gen_data = gen_res.json()

        # Must be a real absolute link with the specified custom domain
        assert gen_data["invite_url"].startswith(custom_public_domain)
        assert "/assessment.html?id=" in gen_data["invite_url"]
        assert f"token={gen_data['access_token']}" in gen_data["invite_url"]

        # Fetch assessment details
        ass_id = gen_data["id"]
        get_res = await ac.get(f"/api/v1/assessments/{ass_id}", headers=headers)
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["invite_url"].startswith("http")
        assert f"/assessment.html?id={ass_id}" in get_data["invite_url"]

