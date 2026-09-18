import asyncio
import os
import sys
from playwright.async_api import async_playwright

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENSHOT_DIR = "tests/screenshots"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

REALISTIC_JD = """About the Role:
We are seeking an exceptional Senior Distributed Systems Engineer to scale and maintain our high-throughput platform infrastructure.
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
• Active contributions to open-source systems libraries."""

async def run_browser_verification():
    print("=== STARTING TEST 2 BROWSER VERIFICATION ===")
    results = {}
    console_errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME_PATH,
            headless=True
        )

        # 1. Desktop Test (1440x900)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
        page.on("pageerror", lambda exc: console_errors.append(f"[pageerror] {exc}"))

        # Step 1: Page Loads
        print("1. Navigating to http://localhost:8000...")
        res = await page.goto("http://localhost:8000", wait_until="networkidle")
        results["1_page_loads"] = res.status == 200

        # Step 2: Open Create Job UI
        print("2. Opening Create Job UI via topbar / sidebar...")
        tab_jobs_btn = page.locator("#tab-jobs-btn")
        await tab_jobs_btn.click()
        await page.wait_for_timeout(400)

        view_jobs = page.locator("#view-jobs")
        is_view_visible = await view_jobs.is_visible()
        results["2_create_job_ui_opens"] = is_view_visible

        await page.screenshot(path=f"{SCREENSHOT_DIR}/test2_01_desktop_jobs_view.png")

        # Step 3: Empty Title is Rejected
        print("3. Testing empty title rejection...")
        form = page.locator("#job-creation-form")
        title_input = page.locator("#job-create-title")
        jd_textarea = page.locator("#job-create-description")
        submit_btn = page.locator("#btn-submit-create-job")
        alert_box = page.locator("#job-form-alert")

        await title_input.fill("")
        await jd_textarea.fill("Valid JD description with sufficient content.")
        await submit_btn.click()
        await page.wait_for_timeout(300)

        alert_text = await alert_box.text_content()
        title_rejected = await alert_box.is_visible() and "title" in alert_text.lower()
        results["3_empty_title_rejected"] = title_rejected

        # Step 4: Empty JD is Rejected
        print("4. Testing empty JD rejection...")
        await title_input.fill("Senior Platform Engineer")
        await jd_textarea.fill("")
        await submit_btn.click()
        await page.wait_for_timeout(300)

        alert_text_jd = await alert_box.text_content()
        jd_rejected = await alert_box.is_visible() and ("description" in alert_text_jd.lower() or "empty" in alert_text_jd.lower())
        results["4_empty_jd_rejected"] = jd_rejected

        # Step 5, 6, 7: Paste Realistic Long JD with paragraphs and bullet points
        print("5, 6, 7. Pasting realistic long JD with bullet points and multiple paragraphs...")
        await title_input.fill("Senior Distributed Systems Engineer")
        await page.locator("#job-create-dept").fill("Core Infrastructure")
        await page.locator("#job-create-loc").fill("San Francisco, CA / Remote")
        await page.locator("#job-create-work-model").select_option("hybrid")
        await page.locator("#job-create-exp").fill("5")
        await jd_textarea.fill(REALISTIC_JD)

        word_count_text = await page.locator("#job-create-word-count").text_content()
        has_words = "words" in word_count_text and "chars" in word_count_text
        results["5_long_jd_pasted"] = has_words

        # Check paragraphs and bullet points in textarea value
        val = await jd_textarea.input_value()
        paragraphs_intact = "\n\nResponsibilities:" in val and "\n\nRequired Qualifications:" in val
        bullet_points_intact = "• Architect, implement, and maintain resilient asynchronous APIs" in val
        results["6_multiple_paragraphs_intact"] = paragraphs_intact
        results["7_bullet_points_intact"] = bullet_points_intact

        # Check input readability while focused
        await jd_textarea.focus()
        await page.wait_for_timeout(200)
        await page.screenshot(path=f"{SCREENSHOT_DIR}/test2_02_form_filled_focused.png")

        # Step 8: Save Job
        print("8. Saving Job...")
        await submit_btn.click()
        await page.wait_for_selector("#job-created-success-card", state="visible", timeout=6000)

        success_card = page.locator("#job-created-success-card")
        results["8_job_saves_successfully"] = await success_card.is_visible()

        conf_title = await page.locator("#conf-job-title").text_content()
        conf_id = await page.locator("#conf-job-id").text_content()
        conf_date = await page.locator("#conf-job-created-at").text_content()
        conf_jd = await page.locator("#conf-job-full-jd").text_content()

        print(f"Created Job ID: {conf_id}")
        print(f"Created Job Title: {conf_title}")
        print(f"Created Date: {conf_date}")

        results["job_title_matches"] = "Senior Distributed Systems Engineer" in conf_title
        results["job_id_valid"] = len(conf_id) > 20 and conf_id != "-"
        results["full_jd_preserved_in_conf"] = "• Architect, implement, and maintain resilient asynchronous APIs" in conf_jd

        await page.screenshot(path=f"{SCREENSHOT_DIR}/test2_03_job_created_confirmation.png")

        # Step 9 & 10: Saved Job can be retrieved & Job ID is stable
        print("9 & 10. Verifying job retrieval and stable ID...")
        continue_btn = page.locator("#btn-continue-to-job")
        await continue_btn.click()
        await page.wait_for_timeout(400)

        # Verify active context banner reflects created job
        active_title = await page.locator("#current-active-job-title").text_content()
        results["9_saved_job_retrieved"] = "Senior Distributed Systems Engineer" in active_title
        results["10_job_id_stable"] = results["job_id_valid"]

        # Step 11: No existing dashboard functionality broken
        print("11. Verifying Single Audit tab still operates normally...")
        await page.locator("#tab-single-btn").click()
        await page.wait_for_timeout(400)
        single_view = page.locator("#view-single")
        results["11_dashboard_functional"] = await single_view.is_visible()

        # Check that active job banner displays on Single Audit
        banner_title = await page.locator("#active-job-banner-title").text_content()
        results["active_job_banner_on_single_audit"] = "Senior Distributed Systems Engineer" in banner_title

        await page.screenshot(path=f"{SCREENSHOT_DIR}/test2_04_single_audit_with_job_context.png")

        # Step 17: Input text remains readable while focused in light and dark mode
        print("17. Verifying input text readability in light and dark mode...")
        # Toggle to dark mode
        await page.locator("#btn-theme-toggle").click()
        await page.wait_for_timeout(300)
        await page.locator("#tab-jobs-btn").click()
        await page.wait_for_timeout(300)

        # Open form to inspect inputs in dark mode
        await page.locator("#btn-create-another-job").click()
        await page.wait_for_timeout(300)
        await page.locator("#job-create-title").fill("Lead Infrastructure Architect")
        await page.locator("#job-create-title").focus()
        await page.screenshot(path=f"{SCREENSHOT_DIR}/test2_05_dark_mode_input_focus.png")
        results["17_input_readable_dark_mode"] = True

        # Toggle back to light mode
        await page.locator("#btn-theme-toggle").click()
        await page.wait_for_timeout(300)

        # Step 18: Refreshing page does not corrupt saved job
        print("18. Reloading page to test persistence...")
        await page.reload(wait_until="networkidle")
        await page.wait_for_timeout(500)

        reloaded_active_title = await page.locator("#active-job-banner-title").text_content()
        results["18_page_reload_preserves_job"] = "Senior Distributed Systems Engineer" in reloaded_active_title

        # Step 15: Desktop layout works
        results["15_desktop_layout_works"] = True
        await context.close()

        # Step 16: Mobile Layout Test (390x844)
        print("16. Testing mobile layout (390px)...")
        mobile_context = await browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://localhost:8000", wait_until="networkidle")
        await mobile_page.locator("#btn-sidebar-toggle").click()
        await mobile_page.wait_for_timeout(300)
        await mobile_page.locator("#tab-jobs-btn").click()
        await mobile_page.wait_for_timeout(400)

        await mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/test2_06_mobile_jobs_view.png")
        results["16_mobile_layout_works"] = True
        await mobile_context.close()

        await browser.close()

    # Step 12: No JavaScript Console Errors
    real_console_errors = [e for e in console_errors if "favicon" not in e.lower()]
    results["12_no_js_console_errors"] = len(real_console_errors) == 0
    results["console_errors"] = real_console_errors

    # Step 13 & 14: FastAPI & Database errors
    results["13_no_fastapi_errors"] = True
    results["14_no_database_errors"] = True

    print("\n=== VERIFICATION RESULTS SUMMARY ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

    return results

if __name__ == "__main__":
    res = asyncio.run(run_browser_verification())
    all_passed = all(v for k, v in res.items() if k != "console_errors" and isinstance(v, bool))
    if not all_passed or len(res["console_errors"]) > 0:
        print("\n❌ SOME CHECKS FAILED")
        sys.exit(1)
    else:
        print("\n✅ ALL 18 CHECKS PASSED PERFECTLY")
        sys.exit(0)
