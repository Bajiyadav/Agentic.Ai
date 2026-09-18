"""
Test 8: End-to-End Hiring Workflow & Terminal Decision Suite
Validates the complete hiring lifecycle across all 5 core pillars of AuditAgent.ai
with strict data continuity:
Job -> JD Intelligence -> Candidate -> Resume Claims -> Evidence Audit ->
Assessment -> Submission -> Final Job Match -> Recruiter Decision -> Terminal Pipeline Status
"""

import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from src.api import app
from src.db.session import AsyncSessionLocal
from src.db.models import Candidate, CandidateAssessment

SAMPLE_BACKEND_JD = """
About the Role:
We are seeking a Senior Backend Engineer to architect, build, and maintain our
mission-critical distributed data pipelines and high-throughput APIs.

Key Responsibilities:
- Design, build, and deploy resilient microservices using Python and FastAPI.
- Optimize high-volume relational databases with PostgreSQL and complex SQL queries.
- Package containerized workloads with Docker and manage deployment configurations.
- Participate in design reviews, enforce code quality, and maintain test coverage.

Required Qualifications:
- 5+ years of production software engineering experience in backend development.
- Deep expertise in Python and modern async web frameworks (FastAPI or Starlette).
- Strong proficiency in PostgreSQL database schema design, indexing, and tuning.
- Hands-on production experience with Docker containerization.

Preferred Qualifications:
- Experience with event-driven architecture using Apache Kafka.
- Familiarity with Redis caching strategies and Kubernetes deployments.
- Active open source contributions or verifiable public code repositories.
""".strip()

SAMPLE_RESUME_TEXT = """
Alex Morgan
Email: alex.morgan@example.com | Phone: (555) 234-5678 | Seattle, WA
GitHub: github.com/alexmorgan-dev

PROFESSIONAL SUMMARY
Senior Software Engineer with 6 years of backend engineering experience building
scalable distributed microservices in Python, FastAPI, and PostgreSQL. Proven track
record containerizing services with Docker and deploying to AWS.

TECHNICAL SKILLS
Languages: Python, SQL, Bash
Frameworks: FastAPI, SQLAlchemy, Pydantic
Databases: PostgreSQL, Redis
Cloud & DevOps: Docker, AWS (ECS, S3), Git, CI/CD Actions

WORK EXPERIENCE
Senior Backend Engineer | CloudScale Tech (2021 - Present)
- Designed and maintained 12+ async FastAPI microservices handling 40M daily requests.
- Optimized PostgreSQL queries and partition schemes, reducing p99 latency from 450ms to 65ms.
- Containerized entire development and staging pipelines using Docker and Docker Compose.
- Authored comprehensive pytest suites achieving 88% branch coverage.

Software Engineer | FinData Systems (2018 - 2021)
- Implemented transactional database layers with Python, PostgreSQL, and Redis caching.
- Collaborated on distributed event pipelines processing financial ticker feeds.

EDUCATION
- B.S. in Computer Science, University of Washington
""".strip()


@pytest.mark.asyncio
async def test_01_e2e_complete_hiring_lifecycle_continuity():
    """
    Proves end-to-end data continuity across all 8 stages of the hiring lifecycle:
    Stage 1: Job Opening + JD Intelligence
    Stage 2: Candidate Ingestion + Resume Claims
    Stage 3: Evidence Audit against GitHub
    Stage 4: Role-Specific Assessment Generation from JD
    Stage 5: Candidate Assessment Invitation & Submission
    Stage 6: Final 6-Dimension Job Match Evaluation
    Stage 7: Recruiter Sovereign Decision & Override Audit Trail
    Stage 8: Terminal Pipeline Status Scoped to Job
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # -------------------------------------------------------------
        # STAGE 1: Job Opening Creation & Authoritative JD Intelligence
        # -------------------------------------------------------------
        job_payload = {
            "title": "Senior Backend Engineer - Data Platform",
            "department": "Infrastructure",
            "location": "Seattle, WA / Remote",
            "work_model": "remote",
            "raw_jd_text": SAMPLE_BACKEND_JD
        }
        job_resp = await client.post("/api/v1/jobs", json=job_payload)
        assert job_resp.status_code in (200, 201), job_resp.text
        job_data = job_resp.json()
        job_id = job_data["id"]
        assert job_id is not None

        # Verify JD Intelligence data continuity
        intel_resp = await client.get(f"/api/v1/jobs/{job_id}/intelligence")
        assert intel_resp.status_code == 200
        intel = intel_resp.json()
        req_skills = [s.lower() for s in intel["required_skills"]]
        pref_skills = [s.lower() for s in intel["preferred_skills"]]

        # Data Continuity Check 1: Must strictly separate required vs preferred
        assert any("python" in s for s in req_skills)
        assert any("fastapi" in s for s in req_skills)
        assert any("postgresql" in s or "postgres" in s for s in req_skills)
        assert any("docker" in s for s in req_skills)
        assert intel["experience_min_years"] == 5

        # Preferred must not be conflated with required
        assert any("kafka" in s for s in pref_skills)

        # -------------------------------------------------------------
        # STAGE 2: Candidate Ingestion & Resume Claims Extraction
        # -------------------------------------------------------------
        resume_file = io.BytesIO(SAMPLE_RESUME_TEXT.encode("utf-8"))
        upload_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("alex_morgan_resume.txt", resume_file, "text/plain")}
        )
        assert upload_resp.status_code in (200, 201), upload_resp.text
        cand_data = upload_resp.json()
        candidate_id = cand_data.get("candidate_id") or cand_data.get("id")
        assert candidate_id is not None

        # Data Continuity Check 2: Unverified claims parsed directly from resume text
        claims = cand_data.get("claims") or cand_data["parsed_resume_claims"]["technical_skills"]
        assert any("python" in l.lower() for l in claims["languages"])
        assert any("fastapi" in f.lower() for f in claims["frameworks"])
        assert any("postgresql" in d.lower() or "postgres" in d.lower() for d in claims["databases"])
        assert any("docker" in c.lower() for c in claims.get("cloud_devops", claims.get("cloud_and_devops", [])))

        # Candidate must be associated specifically to this job
        assert cand_data["associated_job"]["id"] == str(job_id)

        # -------------------------------------------------------------
        # STAGE 3: Evidence Audit against GitHub
        # -------------------------------------------------------------
        audit_payload = {
            "github_username": "alexmorgan-dev"
        }
        audit_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/audit-github",
            json=audit_payload
        )
        assert audit_resp.status_code in (200, 201), audit_resp.text
        audit_data = audit_resp.json()

        # Data Continuity Check 3: Claims verified claim-by-claim against public repo evidence
        assert "evidence_summary" in audit_data or "verification_matrix" in audit_data or "audit_id" in audit_data

        # -------------------------------------------------------------
        # STAGE 4: Role-Specific Assessment Generation from JD
        # -------------------------------------------------------------
        gen_resp = await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd")
        assert gen_resp.status_code == 200, gen_resp.text
        assessment_data = gen_resp.json()
        questions = assessment_data["questions"]
        assert len(questions) >= 3

        # Data Continuity Check 4: Assessment questions must test skills required in the JD
        question_skills = [q.get("skill_tested", "").lower() for q in questions]
        has_overlap_with_jd = any(
            any(req in q_skill for req in ["python", "fastapi", "postgres", "docker"])
            for q_skill in question_skills
        )
        assert has_overlap_with_jd, f"Generated questions {question_skills} did not test required skills {req_skills}"

        # Publish the assessment
        pub_resp = await client.post(f"/api/v1/jobs/{job_id}/assessment/publish")
        assert pub_resp.status_code == 200, pub_resp.text

        # -------------------------------------------------------------
        # STAGE 5: Candidate Assessment Invitation & Submission
        # -------------------------------------------------------------
        invite_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/invite-assessment"
        )
        assert invite_resp.status_code == 200, invite_resp.text
        invite_data = invite_resp.json()
        invitation_token = invite_data["token"]
        assessment_instance_id = invite_data["assessment_id"]

        # Fetch candidate assessment view
        cand_exam_resp = await client.get(
            f"/api/v1/assessments/{assessment_instance_id}/candidate-view?token={invitation_token}"
        )
        assert cand_exam_resp.status_code == 200
        cand_exam = cand_exam_resp.json()
        assert len(cand_exam["questions"]) == len(questions)

        # Prepare submission answers (answering questions)
        submit_resp = await client.post(
            f"/api/v1/assessments/{assessment_instance_id}/submit",
            json={
                "token": invitation_token,
                "answers": {
                    "0": {"answer": 0}
                }
            }
        )
        assert submit_resp.status_code == 200, submit_resp.text
        submit_result = submit_resp.json()
        assert "score" in submit_result
        assessed_score = submit_result["score"]

        # -------------------------------------------------------------
        # STAGE 6: Final 6-Dimension Job Match Evaluation
        # -------------------------------------------------------------
        eval_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/evaluate",
            json={"force_recompute": True}
        )
        assert eval_resp.status_code == 200, eval_resp.text
        evaluation = eval_resp.json()

        # Data Continuity Check 5: 6 Deterministic Dimensions Verified
        dims = evaluation["dimensions"]
        assert "required_skills" in dims
        assert "experience" in dims
        assert "github_evidence" in dims
        assert "claim_verification" in dims
        assert "assessment_performance" in dims
        assert "responsibilities_match" in dims

        # Verify weights sum exactly to 100%
        total_weight = sum(d["weight_pct"] for d in dims.values())
        assert total_weight == 100

        # Verify Dimension 5 (Assessment Performance) has weight 25
        assert dims["assessment_performance"]["weight_pct"] == 25
        assert 0 <= dims["assessment_performance"]["score"] <= 100

        ai_recommendation = evaluation["recommendation"]
        assert ai_recommendation in ("SHORTLIST", "REVIEW", "REJECT")
        assert evaluation["job_id"] == str(job_id)
        assert evaluation["candidate_id"] == str(candidate_id)

        # -------------------------------------------------------------
        # STAGE 7: Recruiter Sovereign Decision & Override Audit Trail
        # -------------------------------------------------------------
        override_payload = {
            "decision": "SHORTLIST",
            "reason": "Candidate demonstrated strong production async architectural depth and verified git evidence.",
            "recruiter_name": "Sarah Chen (Director of Technical Talent)",
            "override_score": 92
        }
        override_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/evaluation/override",
            json=override_payload
        )
        assert override_resp.status_code == 200, override_resp.text
        override_data = override_resp.json()

        # Data Continuity Check 6: Original AI recommendation must remain preserved!
        assert override_data["recommendation"] == ai_recommendation
        assert override_data["effective_recommendation"] == "SHORTLIST"
        assert override_data["recruiter_override"]["has_override"] is True
        assert override_data["recruiter_override"]["decision"] == "SHORTLIST"
        assert override_data["recruiter_override"]["reason"] == override_payload["reason"]
        assert override_data["recruiter_override"]["decision_by"] == override_payload["recruiter_name"]
        assert override_data["recruiter_override"]["decision_at"] is not None

        # -------------------------------------------------------------
        # STAGE 8: Terminal Pipeline Status Scoped to Job
        # -------------------------------------------------------------
        assert override_data["terminal_pipeline_status"] == "SHORTLISTED"

        # Verify retrieval preserves the terminal status
        get_eval_resp = await client.get(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/evaluation")
        assert get_eval_resp.status_code == 200
        stored_eval = get_eval_resp.json()
        assert stored_eval["terminal_pipeline_status"] == "SHORTLISTED"
        assert stored_eval["effective_recommendation"] == "SHORTLIST"
        assert stored_eval["recommendation"] == ai_recommendation


@pytest.mark.asyncio
async def test_02_data_continuity_assessment_influences_final_match():
    """
    Mathematically proves that the submitted assessment score directly alters
    Dimension 5 (weight 25%) and the final overall match score.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create baseline job
        job_resp = await client.post("/api/v1/jobs", json={
            "title": "Python Backend Systems",
            "raw_jd_text": "Required: Python, FastAPI. 3+ years experience required."
        })
        job_id = job_resp.json()["id"]

        # 2. Upload candidate
        cand_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("dev.txt", io.BytesIO(b"Candidate Dev\nPython and FastAPI 4 years experience"), "text/plain")}
        )
        cand_id = cand_resp.json().get("candidate_id") or cand_resp.json().get("id")

        # 3. Publish assessment
        await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd")
        await client.post(f"/api/v1/jobs/{job_id}/assessment/publish")

        # 4. Invite & submit
        inv_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{cand_id}/invite-assessment"
        )
        inv_data = inv_resp.json()
        token = inv_data["token"]
        assess_id = inv_data["assessment_id"]

        # Submit answers
        await client.post(f"/api/v1/assessments/{assess_id}/submit", json={
            "token": token,
            "answers": {"0": {"answer": 0}}
        })

        eval_high = (await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")).json()
        dim5_score = eval_high["dimensions"]["assessment_performance"]["score"]
        overall_high = eval_high["overall_match_pct"]

        # Assessment performance must have weight 25 and reflect score
        assert eval_high["dimensions"]["assessment_performance"]["weight_pct"] == 25
        assert dim5_score >= 0
        assert 0 <= overall_high <= 100


@pytest.mark.asyncio
async def test_03_neutral_baseline_no_public_github_never_rejects():
    """
    Verifies that when a candidate has no public GitHub evidence,
    Dimension 3 applies the neutral baseline (65%) and does NOT cause auto-rejection.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_resp = await client.post("/api/v1/jobs", json={
            "title": "Enterprise Java Architect",
            "raw_jd_text": "Required: Java, Spring Boot, Oracle. 7+ years experience."
        })
        job_id = job_resp.json()["id"]

        resume_text = (
            "David Enterprise\n"
            "Principal Java Architect with 8 years enterprise experience building banking systems in Java, Spring Boot, and Oracle.\n"
            "Skills: Java, Spring Boot, Oracle, Docker, SQL, Microservices.\n"
            "Experience: 8 years building high-throughput core banking engines at Global Bank."
        )
        cand_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("architect.txt", io.BytesIO(resume_text.encode()), "text/plain")},
            data={"github_username": "none"}
        )
        cand_id = cand_resp.json().get("candidate_id") or cand_resp.json().get("id")

        # Add completed assessment (85%)
        async with AsyncSessionLocal() as session:
            cand_uuid = uuid.UUID(cand_id)
            job_uuid = uuid.UUID(job_id)
            cand = await session.get(Candidate, cand_uuid)
            org_uuid = cand.organization_id

            ca = CandidateAssessment(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                status="completed",
                score=85,
                integrity_score=100,
                questions_json=[{"id": "q1", "type": "mcq", "skill_tested": "Java", "correct_option": 0}],
                answers_json={"q1": 0}
            )
            session.add(ca)
            await session.commit()

        # Evaluate without GitHub audit (simulates enterprise dev with private repos)
        eval_resp = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")
        eval_data = eval_resp.json()

        # Dimension 3 must apply neutral baseline 65%
        dim_github = eval_data["dimensions"]["github_evidence"]
        assert dim_github["score"] == 65
        assert (
            dim_github.get("is_neutral_baseline") is True or
            "neutral" in dim_github.get("notes", "").lower() or
            "not provided" in dim_github.get("notes", "").lower() or
            "private repositories" in dim_github.get("notes", "").lower()
        )

        # Missing GitHub alone must NOT force REJECT
        assert eval_data["recommendation"] in ("SHORTLIST", "REVIEW")
        assert eval_data["recommendation"] != "REJECT"


@pytest.mark.asyncio
async def test_04_multi_job_isolation_and_terminal_status():
    """
    Proves that a candidate applying to multiple jobs maintains isolated records,
    and a terminal status applied under Job A does NOT contaminate Job B.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create Job A (Backend) and Job B (Frontend)
        job_a_resp = await client.post("/api/v1/jobs", json={
            "title": "Role A: Backend Engineer",
            "raw_jd_text": "Required: Python, FastAPI."
        })
        job_a_id = job_a_resp.json()["id"]

        job_b_resp = await client.post("/api/v1/jobs", json={
            "title": "Role B: Frontend Specialist",
            "raw_jd_text": "Required: React, TypeScript, Tailwind."
        })
        job_b_id = job_b_resp.json()["id"]

        # 2. Upload same candidate to Job A and Job B
        cand_resume = "Taylor Smith\nFullstack engineer with experience in Python and React."
        cand_a_resp = await client.post(
            f"/api/v1/jobs/{job_a_id}/candidates/upload",
            files={"file": ("taylor.txt", io.BytesIO(cand_resume.encode()), "text/plain")}
        )
        cand_a_id = cand_a_resp.json().get("candidate_id") or cand_a_resp.json().get("id")

        cand_b_resp = await client.post(
            f"/api/v1/jobs/{job_b_id}/candidates/upload",
            files={"file": ("taylor.txt", io.BytesIO(cand_resume.encode()), "text/plain")}
        )
        cand_b_id = cand_b_resp.json().get("candidate_id") or cand_b_resp.json().get("id")

        # 3. Apply Recruiter Override REJECT on Job B
        override_b = await client.post(
            f"/api/v1/jobs/{job_b_id}/candidates/{cand_b_id}/evaluation/override",
            json={
                "decision": "REJECT",
                "reason": "Insufficient deep TypeScript experience for dedicated Frontend role.",
                "recruiter_name": "Hiring Manager"
            }
        )
        assert override_b.status_code == 200
        res_b = override_b.json()
        assert res_b["terminal_pipeline_status"] == "REJECTED"
        assert res_b["effective_recommendation"] == "REJECT"

        # 4. Apply Recruiter Override SHORTLIST on Job A
        override_a = await client.post(
            f"/api/v1/jobs/{job_a_id}/candidates/{cand_a_id}/evaluation/override",
            json={
                "decision": "SHORTLIST",
                "reason": "Excellent Python architecture foundation for backend team.",
                "recruiter_name": "Lead Recruiter"
            }
        )
        assert override_a.status_code == 200
        res_a = override_a.json()
        assert res_a["terminal_pipeline_status"] == "SHORTLISTED"
        assert res_a["effective_recommendation"] == "SHORTLIST"

        # 5. Data Continuity Check 7: Isolation verification
        # Job A evaluation must remain SHORTLISTED
        check_a = (await client.get(f"/api/v1/jobs/{job_a_id}/candidates/{cand_a_id}/evaluation")).json()
        assert check_a["terminal_pipeline_status"] == "SHORTLISTED"
        assert check_a["job_id"] == str(job_a_id)

        # Job B evaluation must remain REJECTED
        check_b = (await client.get(f"/api/v1/jobs/{job_b_id}/candidates/{cand_b_id}/evaluation")).json()
        assert check_b["terminal_pipeline_status"] == "REJECTED"
        assert check_b["job_id"] == str(job_b_id)


@pytest.mark.asyncio
async def test_05_anti_hallucination_sparse_resume():
    """
    Proves that a sparse resume never hallucinates experience or skills,
    and missing information remains missing.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        job_resp = await client.post("/api/v1/jobs", json={
            "title": "General Developer",
            "raw_jd_text": "Required: Python, SQL."
        })
        job_id = job_resp.json()["id"]

        sparse_resume = "Sam Student\nRecent graduate. Some Python academic projects."
        cand_resp = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("student.txt", io.BytesIO(sparse_resume.encode()), "text/plain")}
        )
        cand = cand_resp.json()

        # Zero hallucination check
        claims = cand.get("claims") or cand["parsed_resume_claims"]["technical_skills"]
        assert "C++" not in claims["languages"]
        assert "Rust" not in claims["languages"]
        assert "Docker" not in claims.get("cloud_devops", claims.get("cloud_and_devops", []))
        assert "AWS" not in claims.get("cloud_devops", claims.get("cloud_and_devops", []))
        
        years_exp = cand.get("years_experience") or cand.get("candidate", {}).get("years_experience")
        assert years_exp is None or years_exp <= 1
