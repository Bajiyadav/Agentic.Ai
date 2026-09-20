import asyncio
import os
import uuid
import httpx
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8000"

async def test_full_candidate_exam_flow():
    print("=== Starting Full Candidate Assessment End-to-End Test ===", flush=True)
    
    # Step 1: Generate Job & Candidate and create Assessment Invitation via API
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Create unique tenant/org
        org_id = str(uuid.uuid4())
        recruiter_email = f"lead.recruiter.{uuid.uuid4().hex[:6]}@example.com"
        headers = {
            "x-tenant-id": org_id,
            "x-user-email": recruiter_email
        }
        
        # 1. Create a Job Opening
        job_payload = {
            "title": "Senior Cloud Infrastructure Engineer",
            "department": "Platform Engineering",
            "location": "Remote",
            "employment_type": "Full-time",
            "experience_level": "Senior",
            "raw_jd_text": "We are seeking a Senior Cloud Infrastructure Engineer with 5+ years experience in AWS, Kubernetes, Terraform, Python, Docker, CI/CD pipelines, and distributed systems resilience."
        }
        job_res = await client.post("/api/v1/jobs", json=job_payload, headers=headers)
        assert job_res.status_code == 200, f"Create job failed: {job_res.text}"
        job_data = job_res.json()
        job_id = job_data["id"]
        print(f"✓ Created Job: {job_data['title']} (ID: {job_id})", flush=True)
        
        # 2. Generate Assessment from JD and Publish
        gen_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/generate-from-jd", headers=headers)
        assert gen_res.status_code == 200, f"Generate assessment failed: {gen_res.text}"
        pub_res = await client.post(f"/api/v1/jobs/{job_id}/assessment/publish", headers=headers)
        assert pub_res.status_code == 200, f"Publish assessment failed: {pub_res.text}"
        print("✓ Generated & Published Job Assessment from JD", flush=True)
        
        # 3. Add Candidate via Upload
        sample_resume = (
            "Devin Coder\n"
            "devin.coder@example.com | (555) 019-2834 | San Francisco, CA\n\n"
            "Summary: Senior Cloud Engineer with 6 years building Kubernetes platforms on AWS.\n\n"
            "Experience:\n"
            "Senior Cloud Engineer at CloudScale Inc (2021 - Present)\n"
            "- Architected Kubernetes clusters across 3 AWS regions using Terraform.\n"
            "- Automated deployments using GitHub Actions and ArgoCD.\n\n"
            "Skills: AWS, Kubernetes, Terraform, Docker, Python, Go, CI/CD, Prometheus, Grafana\n"
        )
        files = {"file": ("devin_coder_resume.txt", sample_resume.encode("utf-8"), "text/plain")}
        cand_res = await client.post(f"/api/v1/jobs/{job_id}/candidates/upload", files=files, headers=headers)
        assert cand_res.status_code == 201, f"Create candidate failed: {cand_res.text}"
        cand_data = cand_res.json()
        candidate_id = cand_data["candidate_id"]
        print(f"✓ Uploaded Candidate: {cand_data.get('name', 'Devin Coder')} (ID: {candidate_id})", flush=True)
        
        # 4. Trigger Assessment Invitation (Email Dispatch)
        invite_res = await client.post(
            f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/invite-assessment",
            headers=headers
        )
        assert invite_res.status_code == 200, f"Invite candidate failed: {invite_res.text}"
        invite_data = invite_res.json()
        assessment_id = invite_data["assessment_id"]
        invite_url = invite_data["invite_url"]
        access_token = invite_data["access_token"]
        otp_code = invite_data["otp_code"]
        email_delivery = invite_data.get("email_delivery", {})
        
        print(f"✓ Assessment Invitation Generated:", flush=True)
        print(f"  - Assessment ID: {assessment_id}", flush=True)
        print(f"  - Invite URL: {invite_url}", flush=True)
        print(f"  - 6-Digit OTP: {otp_code}", flush=True)
        print(f"  - Email Provider: {email_delivery.get('provider')} (Delivered: {email_delivery.get('delivered')})", flush=True)
        assert len(otp_code) == 6, "OTP code must be 6 digits"
        assert "/assessment.html?id=" in invite_url, "Invite URL must target assessment.html"

    # Step 2: Browser Simulation of Candidate Taking the Exam
    os.makedirs("tests/screenshots", exist_ok=True)
    os.makedirs("/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream"
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=["camera", "microphone"]
        )
        page = await context.new_page()
        
        # Proper async dialog handler for window.confirm / alert
        async def on_dialog(dialog):
            print(f"  [Browser Dialog Handled]: {dialog.message}", flush=True)
            await dialog.accept()
            
        page.on("dialog", on_dialog)
            
        print(f"\nCandidate navigating to invitation link: {invite_url}", flush=True)
        await page.goto(invite_url, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        
        # Check current screen state
        auth_visible = await page.is_visible("#screen-auth.active")
        preflight_visible = await page.is_visible("#screen-preflight.active")
        active_notice_visible = await page.is_visible("#student-active-notice")
        
        print(f"Screen state on load: auth={auth_visible}, preflight={preflight_visible}, active_notice={active_notice_visible}", flush=True)
        
        if auth_visible:
            print(f"Candidate entering 6-digit OTP ({otp_code})...", flush=True)
            otp_inputs = await page.query_selector_all(".otp-input-field")
            if len(otp_inputs) == 6:
                for idx, digit in enumerate(otp_code):
                    await otp_inputs[idx].fill(digit)
            await page.click("#btn-verify-otp")
            await page.wait_for_timeout(1500)
        elif active_notice_visible and not preflight_visible:
            print("Candidate clicking active notice start...", flush=True)
            await page.click("#btn-start-active-notice")
            await page.wait_for_timeout(1000)
            
        # Ensure we are now on the preflight screen
        await page.wait_for_selector("#screen-preflight.active", timeout=10000)
        print("✓ Preflight hardware & proctoring check screen active", flush=True)
        
        # Click to skip playbook and enter exam workspace
        start_btn = await page.wait_for_selector("#btn-start-test", timeout=5000)
        assert start_btn is not None
        await start_btn.click()
        await page.wait_for_timeout(2000)
        
        # Confirm live assessment room is active
        await page.wait_for_selector("#screen-assessment.active", timeout=10000)
        print("✓ Entered Live Assessment Workspace (#screen-assessment)", flush=True)
        
        # Answer Question: MCQ option card or Coding
        mcq_cards = await page.query_selector_all(".mcq-option-card")
        if mcq_cards:
            print(f"Found {len(mcq_cards)} MCQ options. Selecting option 1...", flush=True)
            await mcq_cards[0].click()
            await page.wait_for_timeout(500)
        else:
            print("Coding question currently active. Injecting answer...", flush=True)
            await page.evaluate("""() => {
                if (window.editor) {
                    window.editor.setValue('def solution(): return True');
                }
            }""")
            
        # Try running code in live sandbox if run button is visible
        btn_run_code = await page.query_selector("#btn-run-code")
        if btn_run_code and await btn_run_code.is_visible():
            print("Running code in live sandbox (#btn-run-code)...", flush=True)
            await btn_run_code.click()
            await page.wait_for_timeout(1500)
            
        # Check next question
        btn_next = await page.query_selector("#btn-next-question")
        if btn_next and await btn_next.is_visible():
            print("Navigating to Question 2...", flush=True)
            await btn_next.click()
            await page.wait_for_timeout(500)
            if await page.is_visible("#mcq-panel"):
                mcq_cards_2 = await page.query_selector_all(".mcq-option-card")
                if mcq_cards_2:
                    await mcq_cards_2[min(1, len(mcq_cards_2)-1)].click()
                    await page.wait_for_timeout(500)
            else:
                await page.evaluate("""() => {
                    if (window.editor) {
                        window.editor.setValue('def solution(): return True');
                    }
                }""")
                await page.wait_for_timeout(500)
                
        # Candidate submits the completed exam
        print("Candidate clicking Submit Assessment (#btn-submit-assessment)...", flush=True)
        btn_submit = await page.wait_for_selector("#btn-submit-assessment", timeout=5000)
        await btn_submit.click()
        await page.wait_for_timeout(3000)
        
        # Confirm results scorecard screen is displayed
        await page.wait_for_selector("#screen-results.active", timeout=15000)
        tech_score = await page.inner_text("#final-tech-score")
        integrity_score = await page.inner_text("#final-integrity-score")
        print(f"✓ Exam Submitted Successfully!", flush=True)
        print(f"  - Technical Score: {tech_score}", flush=True)
        print(f"  - Integrity Score: {integrity_score}", flush=True)
        
        # Save screenshot
        results_screenshot = "tests/screenshots/candidate_exam_results.png"
        await page.screenshot(path=results_screenshot, full_page=True)
        artifact_screenshot = "/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3/candidate_exam_results.png"
        await page.screenshot(path=artifact_screenshot, full_page=True)
        print(f"✓ Screenshot captured: {results_screenshot}", flush=True)
        
        await browser.close()
        
    # Step 3: Recruiter Verification via Backend Audit API
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        headers = {
            "x-tenant-id": org_id,
            "x-user-email": recruiter_email
        }
        audit_res = await client.get(f"/api/v1/assessments/{assessment_id}/proctor/audit", headers=headers)
        assert audit_res.status_code == 200, f"Recruiter proctor audit failed: {audit_res.text}"
        audit_data = audit_res.json()
        print("\n✓ Recruiter Proctoring & Score Audit:", flush=True)
        print(f"  - Candidate: {audit_data.get('candidate_name')}", flush=True)
        print(f"  - Assessment Status: {audit_data.get('status')}", flush=True)
        print(f"  - Final Score: {audit_data.get('score')}", flush=True)
        print(f"  - Integrity Score: {audit_data.get('integrity_score')}%", flush=True)
        print(f"  - Strike Count: {audit_data.get('strike_count')}", flush=True)
        assert audit_data.get("status") in ("completed", "submitted"), f"Expected completed status, got {audit_data.get('status')}"
        
    print("\n=== ALL CANDIDATE EXAM FLOW TESTS PASSED 100% ===", flush=True)

if __name__ == "__main__":
    asyncio.run(test_full_candidate_exam_flow())
