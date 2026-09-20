"""
Playwright E2E verification for Company JD Guide -> 'Use Template in Create Job' workflow.
"""
import asyncio
import os
import shutil
from playwright.async_api import async_playwright

ARTIFACTS_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3"

async def run_verification():
    print("=== STARTING COMPANY JD GUIDE E2E VERIFICATION ===")
    os.makedirs("tests/screenshots", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        page = await context.new_page()

        # 1. Navigate to application
        print("1. Loading AuditAgent.ai...")
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(1000)

        # 2. Open Company JD Guide from navigation/home button
        print("2. Opening Company JD Guide Modal...")
        guide_btn = page.locator("#btn-home-open-jd-guide")
        if not await guide_btn.is_visible():
            guide_btn = page.locator("#btn-jobs-view-jd-guide")
        await guide_btn.click()
        await page.wait_for_timeout(600)

        modal = page.locator("#modal-jd-requirements-guide")
        assert await modal.is_visible(), "Expected JD Guide Modal to be visible"

        # 3. Switch to Tab 4 (Ready-to-Use Authoritative JD Template)
        print("3. Switching to Tab 4: Authoritative Template...")
        tab4_btn = page.locator('button[data-jd-tab="jd-tab-template"]')
        await tab4_btn.click()
        await page.wait_for_timeout(400)

        template_panel = page.locator("#jd-tab-template")
        assert await template_panel.is_visible(), "Expected Tab 4 panel to be visible"

        use_btn = page.locator("#btn-use-authoritative-jd-template")
        assert await use_btn.is_visible(), "Expected 'Use Template in Create Job' button to be visible"

        # Capture screenshot of the Guide Tab 4 with the action button
        await page.screenshot(path="tests/screenshots/jd_guide_tab4_action_button.png")
        print("Saved tests/screenshots/jd_guide_tab4_action_button.png")

        # 4. Click 'Use Template in Create Job →'
        print("4. Clicking 'Use Template in Create Job →'...")
        await use_btn.click()
        await page.wait_for_timeout(800)

        # 5. Verify modal closed and Create Job form opened
        assert not await modal.is_visible(), "Expected JD Guide Modal to close after clicking Use Template"
        assert await page.is_visible("#card-create-job"), "Expected #card-create-job to be visible"

        # 6. Verify form fields populated
        title_val = await page.input_value("#job-create-title")
        dept_val = await page.input_value("#job-create-dept")
        loc_val = await page.input_value("#job-create-loc")
        work_val = await page.input_value("#job-create-work-model")
        exp_val = await page.input_value("#job-create-exp")
        jd_val = await page.input_value("#job-create-description")

        print(f"Loaded Title: {title_val}")
        print(f"Loaded Dept: {dept_val}")
        print(f"Loaded Location: {loc_val}")
        print(f"Loaded Work Model: {work_val}")
        print(f"Loaded Experience: {exp_val}")
        print(f"Loaded JD Length: {len(jd_val)} characters")

        assert title_val == "Senior Distributed Systems Engineer", f"Unexpected title: {title_val}"
        assert dept_val == "Core Platform Infrastructure", f"Unexpected dept: {dept_val}"
        assert loc_val == "San Francisco, CA / Remote", f"Unexpected loc: {loc_val}"
        assert work_val == "remote", f"Unexpected work model: {work_val}"
        assert exp_val == "4", f"Unexpected experience: {exp_val}"
        assert "Senior Distributed Systems Engineer" in jd_val, "Expected authoritative JD description"
        assert "50,000+ requests per second" in jd_val, "Expected key metrics in JD description"

        # Capture screenshot of populated form
        await page.screenshot(path="tests/screenshots/jd_template_loaded_in_create_job.png")
        print("Saved tests/screenshots/jd_template_loaded_in_create_job.png")

        # 7. Submit Create Job to verify full lifecycle
        print("5. Submitting Create Job form with Authoritative Template...")
        await page.click("#btn-submit-create-job")
        await page.wait_for_timeout(1500)

        # 8. Verify Success Card appears
        success_card = page.locator("#job-created-success-card")
        await page.wait_for_selector("#job-created-success-card", state="visible", timeout=10000)
        assert await success_card.is_visible(), "Expected Job Created Success Card to appear"
        created_job_title = await page.inner_text("#conf-job-title")
        print(f"Created Job Success Card Title: {created_job_title}")
        assert "Senior Distributed Systems Engineer" in created_job_title

        # Capture screenshot of success card
        await page.screenshot(path="tests/screenshots/jd_template_job_created.png")
        print("Saved tests/screenshots/jd_template_job_created.png")

        # Copy screenshots to artifact directory
        for img_name in ["jd_guide_tab4_action_button.png", "jd_template_loaded_in_create_job.png", "jd_template_job_created.png"]:
            src = os.path.join("tests/screenshots", img_name)
            dst = os.path.join(ARTIFACTS_DIR, img_name)
            if os.path.exists(src):
                shutil.copyfile(src, dst)
                print(f"Copied to artifact: {dst}")

        await browser.close()
        print("\n🎉 ALL CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_verification())
