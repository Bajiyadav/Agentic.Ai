import os
import sys
import asyncio
from playwright.async_api import async_playwright
import io
from reportlab.pdfgen import canvas

ARTIFACTS_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/21404dcf-842e-4ffa-8785-faf139b71f40"

def generate_test_resume() -> str:
    path = "/tmp/alex_mercer_resume.pdf"
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Alex Mercer")
    c.drawString(100, 735, "alex.mercer@example.com | 555-0199 | San Francisco, CA")
    c.drawString(100, 720, "Role: Senior Backend Systems Engineer")
    c.drawString(100, 700, "github.com/tiangolo")
    c.drawString(100, 680, "Technical Skills:")
    c.drawString(100, 665, "Languages: Python, Go, Rust")
    c.drawString(100, 650, "Frameworks: FastAPI, SQLAlchemy, Gin")
    c.drawString(100, 635, "Databases: PostgreSQL, Redis")
    c.drawString(100, 620, "Cloud & DevOps: Docker, Kubernetes, AWS")
    c.drawString(100, 600, "Work Experience:")
    c.drawString(100, 585, "Lead Backend Engineer at CloudScale (2021-Present)")
    c.drawString(100, 570, "Built microservices in Go, Python, FastAPI, PostgreSQL, Kubernetes")
    c.save()
    buf.seek(0)
    with open(path, "wb") as f:
        f.write(buf.read())
    return path

async def run_verification():
    resume_path = generate_test_resume()
    console_errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("[1] Navigating to http://localhost:8000...", flush=True)
        await page.goto("http://localhost:8000", wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        # Ensure active job context banner is visible
        print("[2] Checking active job context...", flush=True)
        job_banner = page.locator("#active-job-context-banner")
        if not await job_banner.is_visible():
            await page.click("#tab-jobs-btn")
            await asyncio.sleep(0.8)
            first_job_card = page.locator(".job-opening-card").first
            if await first_job_card.is_visible():
                await first_job_card.click()
                await asyncio.sleep(0.8)
            await page.click("#tab-single-btn")
            await asyncio.sleep(0.8)

        # Upload candidate resume
        print("[3] Uploading candidate resume PDF...", flush=True)
        file_input = page.locator("#resume-input")
        await file_input.set_input_files(resume_path)
        await asyncio.sleep(0.8)

        # Click the dedicated Test 4 button: "Upload & Parse Resume Claims (Test 4)"
        btn_parse = page.locator("#btn-parse-claims-only")
        await btn_parse.wait_for(state="visible", timeout=5000)
        await btn_parse.click()

        # Wait for Candidate Record card to appear
        print("[4] Waiting for Candidate Record Card...", flush=True)
        cand_card = page.locator("#candidate-record-card")
        await cand_card.wait_for(state="visible", timeout=15000)
        await asyncio.sleep(1)

        # Check GitHub Audit section is visible
        audit_sec = page.locator("#github-evidence-audit-section")
        assert await audit_sec.is_visible(), "GitHub Evidence Audit Section is not visible!"

        # Input GitHub URL and trigger audit
        print("[5] Auditing GitHub evidence for tiangolo...", flush=True)
        github_input = page.locator("#github-audit-input")
        await github_input.fill("https://github.com/tiangolo")
        await asyncio.sleep(0.5)

        btn_audit = page.locator("#btn-audit-github")
        await btn_audit.click()

        # Wait for audit results
        print("[6] Waiting for GitHub audit results...", flush=True)
        audit_results = page.locator("#github-audit-results")
        await audit_results.wait_for(state="visible", timeout=20000)
        await asyncio.sleep(1.5)

        # Screenshot 1: Desktop Audited Profile & Claim Verification Table
        shot1 = f"{ARTIFACTS_DIR}/test5_01_desktop_evidence_audit.png"
        await page.screenshot(path=shot1, full_page=True)
        print(f"Captured: {shot1}", flush=True)

        # Open inspect drawer for a claim
        print("[7] Inspecting evidence drawer for a claim...", flush=True)
        inspect_btn = page.locator(".btn-inspect-claim").first
        if await inspect_btn.is_visible():
            await inspect_btn.click()
            await asyncio.sleep(0.8)
            drawer = page.locator("#evidence-inspect-drawer")
            assert await drawer.is_visible(), "Inspect drawer did not open!"
            shot2 = f"{ARTIFACTS_DIR}/test5_02_evidence_inspect_drawer.png"
            await page.screenshot(path=shot2)
            print(f"Captured: {shot2}", flush=True)

        # Switch to Dark Mode
        print("[8] Toggling Dark Mode...", flush=True)
        theme_btn = page.locator("#btn-theme-toggle")
        if await theme_btn.is_visible():
            await theme_btn.click()
            await asyncio.sleep(0.8)
            shot3 = f"{ARTIFACTS_DIR}/test5_03_dark_mode_evidence_audit.png"
            await page.screenshot(path=shot3, full_page=True)
            print(f"Captured: {shot3}", flush=True)
            # Switch back to light
            await theme_btn.click()
            await asyncio.sleep(0.4)

        # Mobile Viewport Test (375x667)
        print("[9] Testing mobile responsive layout (375x667)...", flush=True)
        await page.set_viewport_size({"width": 375, "height": 667})
        await asyncio.sleep(0.8)
        shot4 = f"{ARTIFACTS_DIR}/test5_04_mobile_evidence_audit.png"
        await page.screenshot(path=shot4, full_page=True)
        print(f"Captured: {shot4}", flush=True)

        # Reset Viewport & Test Invalid GitHub URL
        print("[10] Testing invalid GitHub URL error state...", flush=True)
        await page.set_viewport_size({"width": 1440, "height": 900})
        await asyncio.sleep(0.5)
        await page.locator("#github-audit-input").fill("https://gitlab.com/invalid-profile")
        await page.locator("#btn-audit-github").click()
        await asyncio.sleep(1)

        err_banner = page.locator("#github-audit-error-banner")
        await err_banner.wait_for(state="visible", timeout=5000)
        shot5 = f"{ARTIFACTS_DIR}/test5_05_invalid_github_url_error.png"
        await page.screenshot(path=shot5)
        print(f"Captured: {shot5}", flush=True)

        print("\nAll browser verifications completed successfully!", flush=True)
        print("Console errors count:", len(console_errors), flush=True)
        if console_errors:
            print("Console errors:", console_errors, flush=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_verification())
