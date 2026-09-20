import asyncio
import uuid
import httpx
from playwright.async_api import async_playwright
from src.db.session import async_session_factory
from src.db.models import Organization, User, Membership, JobOpening, Candidate, CandidateAssessment
from src.security import hash_password, create_access_token

async def seed_e2e_data():
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    async with async_session_factory() as db:
        org = Organization(
            id=org_id,
            name="Apex Horizon Technologies",
            slug=f"apex-{org_id.hex[:6]}",
            plan_tier="enterprise",
            is_active=True
        )
        db.add(org)

        user = User(
            id=user_id,
            email=f"hiring.lead-{user_id.hex[:6]}@apexhorizon.io",
            hashed_password=hash_password("ApexSecure2026!"),
            full_name="Sarah Jenkins (VP Talent)",
            is_active=True
        )
        db.add(user)

        mem = Membership(
            user_id=user.id,
            organization_id=org.id,
            role="recruiter"
        )
        db.add(mem)

        job = JobOpening(
            id=job_id,
            organization_id=org_id,
            title="Senior Distributed Systems Architect",
            raw_jd_text="Build distributed stream-processing engines in Go and Python.",
            status="active"
        )
        db.add(job)

        candidate = Candidate(
            id=candidate_id,
            organization_id=org_id,
            job_id=job_id,
            name="Dr. Elena Rostova",
            email="elena.rostova@distributed-systems.org",
            current_title="Lead Distributed Systems Engineer",
            years_experience=8.5,
            raw_summary="Architect specializing in consensus protocols, Raft, Paxos, and Kafka."
        )
        db.add(candidate)

        assessment = CandidateAssessment(
            id=assessment_id,
            organization_id=org_id,
            candidate_id=candidate_id,
            job_id=job_id,
            duration_minutes=30,
            status="completed",
            score=94,
            integrity_score=91,
            strike_count=1,
            max_strikes=3,
            strengths=[
                "Exceptional O(1) time complexity design using OrderedDict and thread-safe locking",
                "Thread-safe locking mechanisms and edge-condition resilience",
                "100% test coverage on sandbox boundary cases"
            ],
            weaknesses=[
                "Could optimize memory footprint for eviction queue metadata",
                "Minor formatting omission in parameter type hints"
            ],
            feedback="Elena demonstrated master-level mastery of concurrency and memory efficiency. Recommended strongly for final onsite round.",
            questions_json=[
                {
                    "id": "q1",
                    "title": "High-Throughput LRU Eviction Cache",
                    "type": "code",
                    "description": "Implement a thread-safe, high-concurrency LRU Cache with capacity N, supporting get(key) and put(key, val) in strict O(1) runtime.",
                    "starter_code": "class HighThroughputLRU:\n    def __init__(self, capacity: int):\n        pass",
                    "test_cases": [
                        {"input": "put(1, 100), get(1)", "expected": "100"},
                        {"input": "put(2, 200), put(3, 300), get(1)", "expected": "-1"}
                    ]
                },
                {
                    "id": "q2",
                    "title": "Raft Log Compaction & Snapshotting",
                    "type": "code",
                    "description": "Write the state machine checkpointing method that truncates Raft log entries up to last_included_index.",
                    "starter_code": "def compact_log(entries, last_included_index):\n    pass",
                    "test_cases": [
                        {"input": "compact_log([0, 1, 2, 3], 2)", "expected": "[2, 3]"}
                    ]
                }
            ],
            answers_json={
                "q1": 'from collections import OrderedDict\nimport threading\n\nclass HighThroughputLRU:\n    def __init__(self, capacity: int):\n        self.capacity = capacity\n        self.cache = OrderedDict()\n        self.lock = threading.RLock()\n\n    def get(self, key: int) -> int:\n        with self.lock:\n            if key not in self.cache:\n                return -1\n            self.cache.move_to_end(key)\n            return self.cache[key]\n\n    def put(self, key: int, value: int) -> None:\n        with self.lock:\n            if key in self.cache:\n                self.cache.move_to_end(key)\n            self.cache[key] = value\n            if len(self.cache) > self.capacity:\n                self.cache.popitem(last=False)',
                "q2": 'def compact_log(entries, last_included_index):\n    return [entry for entry in entries if entry >= last_included_index]'
            },
            sandbox_results={
                "q1": {
                    "tests_passed": 5,
                    "tests_total": 5,
                    "success": True,
                    "duration_ms": 14,
                    "stdout": "✓ Test 1: Baseline get/put (0.2ms)\n✓ Test 2: Concurrency under 50 workers (4.1ms)\n✓ Test 3: Eviction order verification (0.8ms)\n✓ Test 4: Capacity limit strictness (0.3ms)\n✓ Test 5: Negative keys and boundary edge cases (0.1ms)\n\nAll 5 test cases verified successfully."
                },
                "q2": {
                    "tests_passed": 2,
                    "tests_total": 2,
                    "success": True,
                    "duration_ms": 6,
                    "stdout": "✓ Test 1: Log compaction boundary (0.2ms)\n✓ Test 2: Out of order indexing guard (0.4ms)"
                }
            },
            proctoring_logs=[
                {"timestamp": "2026-09-20T21:00:00Z", "event_type": "assessment_started", "details": {"ip": "74.125.21.18", "browser": "Chrome 128 / macOS"}, "strike_added": False},
                {"timestamp": "2026-09-20T21:05:12Z", "event_type": "fullscreen_enabled", "details": {"display": "2560x1440 Retina"}, "strike_added": False},
                {"timestamp": "2026-09-20T21:18:42Z", "event_type": "tab_blur", "details": {"duration_seconds": 3.8, "target": "external_window"}, "strike_added": True},
                {"timestamp": "2026-09-20T21:18:46Z", "event_type": "fullscreen_restored", "details": {"strikes_total": 1}, "strike_added": False},
                {"timestamp": "2026-09-20T21:28:10Z", "event_type": "code_sandbox_run", "details": {"question_id": "q1", "passed": 5, "total": 5}, "strike_added": False},
                {"timestamp": "2026-09-20T21:29:55Z", "event_type": "final_submission", "details": {"duration_minutes": 29.9, "total_strikes": 1}, "strike_added": False}
            ]
        )
        db.add(assessment)
        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "email": user.email})
    return {
        "token": token,
        "org_id": str(org_id),
        "user_id": str(user_id),
        "candidate_id": str(candidate_id),
        "assessment_id": str(assessment_id),
        "user_email": user.email
    }


async def main():
    print("🌱 Seeding E2E test data...")
    data = await seed_e2e_data()
    print(f"Data seeded: Candidate {data['candidate_id']}, Assessment {data['assessment_id']}")

    # 1. Verify API responds correctly with PDF
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as http_client:
        pdf_res = await http_client.get(
            f"/api/v1/assessments/{data['assessment_id']}/proctor/audit/pdf",
            headers={"Authorization": f"Bearer {data['token']}", "X-Organization-Id": data["org_id"]}
        )
        assert pdf_res.status_code == 200, f"PDF export failed: {pdf_res.text}"
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")
        print(f"✓ PDF export endpoint verified via HTTP ({len(pdf_res.content)} bytes)")

    # 2. Verify UI with Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        # Set auth credentials in localStorage
        await page.goto("http://127.0.0.1:8000/")
        await page.evaluate(f"""() => {{
            localStorage.setItem("auditagent_token", "{data['token']}");
            localStorage.setItem("auditagent_org_id", "{data['org_id']}");
            localStorage.setItem("auditagent_user", JSON.stringify({{
                id: "{data['user_id']}",
                email: "{data['user_email']}",
                full_name: "Sarah Jenkins (VP Talent)",
                role: "recruiter"
            }}));
        }}""")

        # Reload dashboard
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(1500)

        # Open Candidate Assessment Audit Modal directly via app controller
        print("Opening Candidate Assessment Audit Modal...")
        await page.evaluate(f"""async () => {{
            await window.openCandidateAssessmentAuditModal("{data['assessment_id']}", "Dr. Elena Rostova");
        }}""")
        await page.wait_for_timeout(2000)

        # Verify modal visibility
        is_visible = await page.locator("#modal-candidate-assessment-audit").is_visible()
        assert is_visible, "Assessment audit modal should be visible"
        print("✓ Modal is visible on screen")

        # Verify candidate name and assessment title in modal header
        header_name = await page.locator("#audit-modal-candidate-name").inner_text()
        print(f"Header: {header_name}")
        assert "Dr. Elena Rostova" in header_name or "Assessment Dossier" in header_name

        score_text = await page.locator("#audit-kpi-score").inner_text()
        print(f"Score KPI: {score_text}")
        assert "94" in score_text

        integrity_text = await page.locator("#audit-kpi-integrity").inner_text()
        print(f"Integrity KPI: {integrity_text}")
        assert "91%" in integrity_text

        strikes_text = await page.locator("#audit-kpi-strikes").inner_text()
        print(f"Strikes KPI: {strikes_text}")
        assert "1 of 3" in strikes_text or "1" in strikes_text

        # Tab 1: Challenges & Code Review
        screenshot_code_tab = "/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3/candidate_assessment_dossier_modal.png"
        await page.screenshot(path=screenshot_code_tab)
        print(f"✓ Saved code tab screenshot to {screenshot_code_tab}")

        # Tab 2: Anti-Cheat & Continuous Proctoring Timeline
        print("Switching to Anti-Cheat Timeline tab...")
        await page.click("#tab-audit-proctoring")
        await page.wait_for_timeout(1000)
        screenshot_proctor_tab = "/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3/candidate_proctoring_timeline_tab.png"
        await page.screenshot(path=screenshot_proctor_tab)
        print(f"✓ Saved proctoring tab screenshot to {screenshot_proctor_tab}")

        # Tab 3: AI Synthesis & Competencies
        print("Switching to AI Synthesis tab...")
        await page.click("#tab-audit-evaluation")
        await page.wait_for_timeout(1000)
        screenshot_synth_tab = "/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3/candidate_ai_synthesis_tab.png"
        await page.screenshot(path=screenshot_synth_tab)
        print(f"✓ Saved AI synthesis tab screenshot to {screenshot_synth_tab}")

        await browser.close()
        print("🎉 All E2E checks passed with flying colors!")

if __name__ == "__main__":
    asyncio.run(main())
