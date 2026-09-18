import asyncio
import os
import uuid
import httpx
from playwright.async_api import async_playwright
from src.db.session import AsyncSessionLocal
from src.db.models import (
    JobOpening, Candidate, CandidateJobEvidenceAudit,
    CandidateAssessment, JobAssessment
)

ARTIFACT_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/21404dcf-842e-4ffa-8785-faf139b71f40"

RESUME_TEXT = b"""
Candidate Name: Elena Rostova
Email: elena.rostova@techcorp.io
Phone: +1-555-0198
Current Role: Senior Backend Systems Engineer
Location: Seattle, WA

Summary:
Senior Backend Systems Engineer with 7 years experience building distributed microservices in Python, FastAPI, Docker, and PostgreSQL. Experienced with high-throughput stream processing and enterprise transactional databases.

Skills:
Languages: Python, SQL
Frameworks: FastAPI, Docker, PostgreSQL, Kafka
Tools: Git, Linux, Kubernetes

Experience:
Senior Infrastructure Engineer at DataFlow (2020 - Present)
Architected event-driven microservices processing 40M events daily using Python and PostgreSQL. Managed containerized deployments in Docker.
"""


async def setup_test_candidate_and_job():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Create Job
        job_res = await client.post("/api/v1/jobs", json={
            "title": "Senior Distributed Systems Engineer",
            "department": "Core Infrastructure",
            "experience_min_years": 5.0,
            "raw_jd_text": "We are seeking a Senior Distributed Systems Engineer with 5+ years experience in Python, FastAPI, PostgreSQL, and Docker. Preferred skills: Redis, Kafka. Responsibilities include building scalable REST and event-driven APIs, optimizing PostgreSQL query plans, and maintaining containerized deployment pipelines."
        })
        job_id = job_res.json()["id"]

        # 2. Upload Candidate
        cand_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/upload",
            files={"file": ("elena_rostova.txt", RESUME_TEXT, "text/plain")},
            data={"github_username": "erostova"}
        )
        cand_id = cand_res.json()["candidate_id"]

        # 3. Simulate GitHub Evidence & Assessment
        async with AsyncSessionLocal() as session:
            cand_uuid = uuid.UUID(cand_id)
            job_uuid = uuid.UUID(job_id)
            cand = await session.get(Candidate, cand_uuid)
            org_uuid = cand.organization_id

            # Add GitHub Audit with verified Python, PostgreSQL, Docker, and neutral Kubernetes
            ea = CandidateJobEvidenceAudit(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                github_username="erostova",
                status="Completed",
                audit_data={
                    "status": "Completed",
                    "github_username": "erostova",
                    "public_repos": 16,
                    "original_repos": 11,
                    "profile": {
                        "username": "erostova",
                        "total_public_repos": 16,
                        "original_repos_count": 11,
                        "total_stars": 42,
                        "documentation_ratio": 0.88,
                        "languages_detected": {"Python": 120000, "SQL": 35000, "Dockerfile": 8000}
                    },
                    "claim_verifications": [
                        {"claim_text": "Python microservices", "status": "Verified", "claim_type": "Skill", "confidence_rationale": "Direct repository evidence found in 5 active projects."},
                        {"claim_text": "PostgreSQL database", "status": "Strong Evidence", "claim_type": "Skill", "confidence_rationale": "Complex schema migrations and query optimizations verified in SQL files."},
                        {"claim_text": "Docker containerization", "status": "Verified", "claim_type": "Tool", "confidence_rationale": "Multi-stage Dockerfiles verified in repository manifests."},
                        {"claim_text": "Kubernetes orchestration", "status": "No Public Evidence", "claim_type": "Tool", "confidence_rationale": "No public Kubernetes manifests found; typical enterprise work is in private repositories."},
                        {"claim_text": "Kafka stream processing", "status": "Contradictory Evidence", "claim_type": "Skill", "confidence_rationale": "Candidate claims 5 years Kafka experience, but failed core event loop assessment challenge."}
                    ],
                    "repositories": [
                        {"name": "distributed-kv-store", "description": "High-availability key-value cache written in Python 3.12 with asyncio.", "stars": 28, "language": "Python"},
                        {"name": "fastapi-async-worker", "description": "Production boilerplate for FastAPI microservices.", "stars": 14, "language": "Python"}
                    ]
                }
            )
            session.add(ea)

            # Add Completed Assessment (Score 84%) with 1 failed question on Kafka to produce evidence conflict
            ca = CandidateAssessment(
                organization_id=org_uuid,
                job_id=job_uuid,
                candidate_id=cand_uuid,
                status="completed",
                score=84,
                integrity_score=98,
                questions_json=[
                    {"id": "q1", "type": "mcq", "title": "Python Asyncio Event Loop", "skill_tested": "Python", "correct_option": 1},
                    {"id": "q2", "type": "mcq", "title": "PostgreSQL Indexing & MVCC", "skill_tested": "PostgreSQL", "correct_option": 2},
                    {"id": "q3", "type": "coding", "title": "Docker Multi-stage Build & Service", "skill_tested": "Docker", "points": 30},
                    {"id": "q4", "type": "mcq", "title": "Kafka Partition Consumer Offsets", "skill_tested": "Kafka", "correct_option": 3}
                ],
                answers_json={"q1": 1, "q2": 2, "q4": 0},  # q4 answered incorrectly
                sandbox_results={"q3": {"passed": True}}
            )
            session.add(ca)
            await session.commit()

        # Run evaluation endpoint to persist and cache
        eval_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/{cand_id}/evaluate")
        print("Evaluation pre-calculated:", eval_res.json()["overall_match_pct"], eval_res.json()["recommendation"])

        return job_id, cand_id


async def capture_screenshots(job_id: str, cand_id: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # Go to app
        await page.goto(f"http://localhost:8000")
        await page.wait_for_timeout(1500)

        # Trigger candidate detail view in JS
        await page.evaluate(f"""async () => {{
            const res = await fetch('/api/v1/candidates/{cand_id}');
            const cand = await res.json();
            cand.job_id = '{job_id}';
            activeHiringJob = {{ id: '{job_id}', title: 'Senior Distributed Systems Engineer' }};
            document.querySelectorAll('.tab-view').forEach(v => v.style.display = 'none');
            const sv = document.getElementById('view-single');
            if (sv) sv.style.display = 'block';
            window.renderCandidateRecordCard(cand);
        }}""")
        await page.wait_for_timeout(2000)

        # 1. Desktop Final Scorecard (test7_01_final_scorecard_desktop.png)
        await page.evaluate("""() => {
            const el = document.getElementById('eval-hero-scorecard');
            if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
        }""")
        await page.wait_for_timeout(500)
        hero_card = page.locator("#eval-hero-scorecard")
        await hero_card.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_01_final_scorecard_desktop.png")
        )
        print("Captured test7_01_final_scorecard_desktop.png")

        # 2. Evidence Matrix (test7_02_evidence_matrix.png)
        matrix_card = page.locator("#eval-required-skills-matrix-card")
        await page.evaluate("""() => {
            const topbar = document.querySelector('.workspace-topbar');
            if (topbar) topbar.style.visibility = 'hidden';
            const el = document.getElementById('eval-required-skills-matrix-card');
            if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
        }""")
        await page.wait_for_timeout(500)
        await matrix_card.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_02_evidence_matrix.png")
        )
        await page.evaluate("""() => {
            const topbar = document.querySelector('.workspace-topbar');
            if (topbar) topbar.style.visibility = 'visible';
        }""")
        print("Captured test7_02_evidence_matrix.png")

        # 3. 6 Dimensions Breakdown (test7_03_score_explanation.png)
        dims_el = page.locator("#eval-dimensions-grid")
        await dims_el.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await dims_el.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_03_score_explanation.png")
        )
        print("Captured test7_03_score_explanation.png")

        # 4. Recommendation Reasons (Strengths & Gaps) (test7_04_recommendation_reasons.png)
        reasons_el = page.locator("#eval-strengths-list").locator("xpath=../..")
        await reasons_el.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await reasons_el.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_04_recommendation_reasons.png")
        )
        print("Captured test7_04_recommendation_reasons.png")

        # 5. Claims Requiring Verification (test7_05_claims_requiring_verification.png)
        probes_el = page.locator("#eval-claims-probe-list").locator("..")
        await probes_el.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await probes_el.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_05_claims_requiring_verification.png")
        )
        print("Captured test7_05_claims_requiring_verification.png")

        # 6. Assessment Conflict Detection (test7_06_assessment_conflict.png)
        conflict_el = page.locator("#eval-conflicts-container").locator("..")
        await conflict_el.scroll_into_view_if_needed()
        await page.wait_for_timeout(500)
        await conflict_el.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_06_assessment_conflict.png")
        )
        print("Captured test7_06_assessment_conflict.png")

        # 7. Recruiter Override Console with filled decision (test7_07_recruiter_override.png)
        override_section = page.locator("#recruiter-override-form").locator("..")
        await override_section.scroll_into_view_if_needed()
        await page.locator("#match-override-decision-select").select_option("REVIEW")
        await page.locator("#match-override-reason-input").fill("Strong hands-on Python/PostgreSQL performance (84%), but need follow-up interview on Kafka distributed offsets and enterprise Kubernetes architectures.")
        await page.locator("#match-override-score-input").fill("82")
        await page.locator("#match-override-recruiter-name").fill("Senior Talent Partner")
        await page.locator("#btn-submit-match-override").click()
        await page.wait_for_timeout(1000)
        await override_section.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_07_recruiter_override.png")
        )
        print("Captured test7_07_recruiter_override.png")

        # 8. Dark Mode (test7_08_dark_mode.png)
        await page.evaluate("""() => {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.body.setAttribute('data-theme', 'dark');
            const el = document.getElementById('eval-hero-scorecard');
            if (el) el.scrollIntoView({ block: 'center', behavior: 'instant' });
        }""")
        await page.wait_for_timeout(600)
        dark_hero = page.locator("#eval-hero-scorecard")
        await dark_hero.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_08_dark_mode.png")
        )
        print("Captured test7_08_dark_mode.png")

        # Revert dark mode
        await page.evaluate("""() => {
            document.documentElement.setAttribute('data-theme', 'light');
            document.body.setAttribute('data-theme', 'light');
        }""")

        # 9. Mobile Responsive Viewport (test7_09_mobile.png)
        await context.close()
        mobile_context = await browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://localhost:8000")
        await mobile_page.wait_for_timeout(1000)
        await mobile_page.evaluate(f"""async () => {{
            const res = await fetch('/api/v1/candidates/{cand_id}');
            const cand = await res.json();
            cand.job_id = '{job_id}';
            activeHiringJob = {{ id: '{job_id}', title: 'Senior Distributed Systems Engineer' }};
            document.querySelectorAll('.tab-view').forEach(v => v.style.display = 'none');
            const sv = document.getElementById('view-single');
            if (sv) sv.style.display = 'block';
            window.renderCandidateRecordCard(cand);
        }}""")
        await mobile_page.wait_for_timeout(1500)
        await mobile_page.evaluate("""() => {
            const el = document.getElementById('eval-hero-scorecard');
            if (el) el.scrollIntoView({ block: 'start', behavior: 'instant' });
        }""")
        await mobile_page.wait_for_timeout(500)
        await mobile_page.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_09_mobile.png"),
            full_page=False
        )
        print("Captured test7_09_mobile.png")
        await mobile_context.close()

        # 10. Error State (test7_10_error_state.png)
        err_context = await browser.new_context(viewport={"width": 1280, "height": 900})
        err_page = await err_context.new_page()
        await err_page.goto("http://localhost:8000")
        await err_page.wait_for_timeout(1000)
        await err_page.evaluate(f"""async () => {{
            const res = await fetch('/api/v1/candidates/{cand_id}');
            const cand = await res.json();
            cand.job_id = '{job_id}';
            activeHiringJob = {{ id: '{job_id}', title: 'Senior Distributed Systems Engineer' }};
            document.querySelectorAll('.tab-view').forEach(v => v.style.display = 'none');
            const sv = document.getElementById('view-single');
            if (sv) sv.style.display = 'block';
            window.renderCandidateRecordCard(cand);
        }}""")
        await err_page.wait_for_timeout(1500)

        # Trigger override without required reason
        override_form_el = err_page.locator("#recruiter-override-form")
        await override_form_el.scroll_into_view_if_needed()
        await err_page.locator("#match-override-reason-input").fill("")
        # Remove required attribute temporarily to test client validation error handling
        await err_page.evaluate("""() => {
            const input = document.getElementById('match-override-reason-input');
            if (input) input.removeAttribute('required');
        }""")
        await err_page.locator("#btn-submit-match-override").click()
        await err_page.wait_for_timeout(500)
        # Screenshot the recruiter override card with the validation error
        override_card = err_page.locator("#recruiter-override-form").locator("..")
        await override_card.screenshot(
            path=os.path.join(ARTIFACT_DIR, "test7_10_error_state.png")
        )
        print("Captured test7_10_error_state.png")

        await err_context.close()
        await browser.close()


async def main():
    job_id, cand_id = await setup_test_candidate_and_job()
    await capture_screenshots(job_id, cand_id)
    print("All 10 Test 7 screenshots successfully captured!")


if __name__ == "__main__":
    asyncio.run(main())
