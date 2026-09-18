import asyncio
import os
from playwright.async_api import async_playwright

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ARTIFACTS_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/21404dcf-842e-4ffa-8785-faf139b71f40"

TEST_JD = """About the Role:
We are looking for a Senior Site Reliability Engineer to oversee our multi-region Kubernetes clusters.

Responsibilities:
• Architect, deploy, and scale high-availability Kubernetes infrastructure on AWS.
• Implement automated incident response workflows and chaos engineering practices.
• Maintain Prometheus, Grafana, and OpenTelemetry observability stacks.
• Partner with software engineering squads to ensure 99.99% service availability.

Required Qualifications:
• 6+ years of systems engineering experience in high-scale production environments.
• Expert proficiency in Go and Python for automation and tooling.
• Deep operational mastery of Kubernetes, Docker, and Linux kernel tuning.
• Hands-on production experience with AWS and Terraform.

Preferred Qualifications:
• Experience with Istio service mesh and eBPF kernel tracing.
• Bachelor of Science in Computer Science or Software Engineering.
• Certified Kubernetes Administrator (CKA)."""

async def run_verification():
    print("🚀 Launching Chrome for Test 3 JD Intelligence Browser Verification...")
    errors = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_BIN if os.path.exists(CHROME_BIN) else None,
            headless=True
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 960}
        )
        page = await context.new_page()

        # Capture console errors
        page.on("console", lambda msg: errors.append(f"CONSOLE {msg.type}: {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(f"PAGEERROR: {exc}"))

        # Step 1: Open app
        print("1. Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000", wait_until="networkidle")

        # Step 2: Switch to Jobs tab
        print("2. Switching to Jobs view...")
        await page.click("#tab-jobs-btn")
        await page.wait_for_selector("#view-jobs", state="visible")
        await page.wait_for_timeout(1000)

        # Step 3: Check Active Job Openings list
        print("3. Checking directory list for Requirements Intel button...")
        await page.wait_for_selector(".btn-view-job-intel", state="visible")
        
        # Step 4: Click Requirements Intel on existing job
        print("4. Opening Job Intelligence modal...")
        await page.click(".btn-view-job-intel >> nth=0")
        await page.wait_for_selector("#modal-job-intelligence", state="visible")
        await page.wait_for_selector("#modal-jd-intelligence", state="visible")
        await page.wait_for_timeout(1000)

        # Screenshot 1: Requirements Intelligence Modal
        modal_screenshot_path = os.path.join(ARTIFACTS_DIR, "test3_01_requirements_modal.png")
        await page.screenshot(path=modal_screenshot_path)
        print(f"📸 Saved: {modal_screenshot_path}")

        # Step 5: Close Modal
        print("5. Closing modal...")
        await page.click("#btn-close-job-intel-modal-btn")
        await page.wait_for_selector("#modal-job-intelligence", state="hidden")
        await page.wait_for_timeout(500)

        # Step 6: Create new job to verify inline confirmation intelligence
        print("6. Submitting new job with full JD...")
        await page.fill("#job-create-title", "Senior Site Reliability Engineer")
        await page.fill("#job-create-dept", "Cloud Infrastructure")
        await page.fill("#job-create-loc", "Seattle, WA / Remote")
        await page.select_option("#job-create-work-model", "remote")
        # Leave experience input empty to verify zero hallucination extraction
        await page.fill("#job-create-exp", "")
        await page.fill("#job-create-description", TEST_JD)
        await page.wait_for_timeout(500)

        await page.click("#btn-submit-create-job")
        await page.wait_for_selector("#job-created-success-card", state="visible", timeout=10000)
        await page.wait_for_selector("#conf-jd-intelligence", state="visible")
        await page.wait_for_timeout(1500)

        # Verify extracted intelligence content
        req_count = await page.inner_text("#conf-intel-req-count")
        pref_count = await page.inner_text("#conf-intel-pref-count")
        summary_text = await page.inner_text("#conf-intel-summary")
        exp_badge_text = await page.inner_text("#conf-intel-exp-badge")

        print(f"   - Extracted Required Skills Count: {req_count}")
        print(f"   - Extracted Preferred Skills Count: {pref_count}")
        print(f"   - Extracted Summary: {summary_text[:60]}...")
        print(f"   - Extracted Experience Badge: {exp_badge_text}")

        assert int(req_count) >= 4, f"Expected at least 4 required skills, got {req_count}"
        assert "6" in exp_badge_text, f"Expected 6+ years in experience badge, got {exp_badge_text}"

        # Screenshot 2: Inline Structured Hiring Intelligence Confirmation
        inline_screenshot_path = os.path.join(ARTIFACTS_DIR, "test3_02_created_job_intelligence.png")
        await page.screenshot(path=inline_screenshot_path)
        print(f"📸 Saved: {inline_screenshot_path}")

        # Screenshot 3: Dark Mode Verification
        print("7. Testing Dark Mode appearance...", flush=True)
        await page.click("#btn-theme-toggle")
        await page.wait_for_timeout(800)
        dark_screenshot_path = os.path.join(ARTIFACTS_DIR, "test3_03_dark_mode_intelligence.png")
        await page.screenshot(path=dark_screenshot_path)
        print(f"📸 Saved: {dark_screenshot_path}", flush=True)

        # Screenshot 4: Mobile Viewport
        print("8. Testing Mobile viewport...", flush=True)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(800)
        mobile_screenshot_path = os.path.join(ARTIFACTS_DIR, "test3_04_mobile_intelligence.png")
        await page.screenshot(path=mobile_screenshot_path)
        print(f"📸 Saved: {mobile_screenshot_path}", flush=True)

        await browser.close()

    print("\n================== VERIFICATION SUMMARY ==================")
    print(f"Console Errors: {len(errors)}")
    if errors:
        for err in errors:
            print(f"  ❌ {err}")
    else:
        print("  ✅ ZERO CONSOLE ERRORS!")
    print("==========================================================")
    assert len(errors) == 0, f"Encountered {len(errors)} console errors."

if __name__ == "__main__":
    asyncio.run(run_verification())
