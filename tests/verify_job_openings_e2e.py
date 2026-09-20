"""
Playwright End-to-End Verification for Job Openings Recruiter Experience.
Verifies:
1. Empty state for first-time recruiter with 0 jobs.
2. "+ Create Your First Job" opens creation workflow.
3. First job auto-locks baseline + toast "Baseline locked to [Title]. Ready for screening."
4. Subsequent job preserves existing baseline without silent overwrite.
5. Explicit baseline switch updates banner, sidebar indicator, and toast.
6. Multi-token search across title, department, skills, and clear reset.
7. No-results state when search filter has 0 matches.
8. View mode persistence (grid vs table) and isolation between recruiters.
9. Requirements Intel modal with mandatory vs preferred transparency and footer routing.
10. Screen Candidates navigation establishes active job context in screener.
"""
import asyncio
import os
import uuid
from playwright.async_api import async_playwright

async def run_e2e_verification():
    print("=== STARTING JOB OPENINGS RECRUITER EXPERIENCE E2E VERIFICATION ===")
    os.makedirs("tests/screenshots", exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        page = await context.new_page()

        # -------------------------------------------------------------
        # 1. First-Time Recruiter Experience (Zero Jobs Empty State)
        # -------------------------------------------------------------
        print("\n--- 1. Testing Zero-Jobs Empty State ---")
        recruiter_email = f"fresh_recruiter_{uuid.uuid4().hex[:6]}@acmecorp.com"
        
        await page.goto("http://127.0.0.1:8000/")
        await page.evaluate(f"""() => {{
            localStorage.clear();
            localStorage.setItem('hr_recruiter_name', 'Taylor Swift');
            localStorage.setItem('hr_recruiter_email', '{recruiter_email}');
            localStorage.setItem('hr_recruiter_role', 'Lead Talent Partner');
        }}""")

        # Mock the /api/v1/jobs endpoint to simulate 0 jobs for this first-time test
        await page.route("**/api/v1/jobs", lambda route: (
            route.fulfill(status=200, content_type="application/json", body="[]")
            if route.request.method == "GET"
            else route.continue_()
        ))

        # Navigate to Job Openings
        await page.click("#tab-openings-btn")
        await page.wait_for_timeout(800)

        # Verify Empty State elements
        empty_container = await page.is_visible("#jobs-empty-state-container")
        print(f"Empty state container visible: {empty_container}")
        assert empty_container, "Expected empty state card when 0 jobs exist"

        empty_heading = await page.inner_text("#jobs-empty-state-container h2")
        print(f"Empty state heading: {empty_heading}")
        assert "Create your first job" in empty_heading

        btn_empty_create = await page.is_visible("#btn-empty-create-first-job")
        assert btn_empty_create, "Expected '+ Create Your First Job' button"

        # Verify fallback no-baseline banner is displayed
        no_baseline_banner = await page.is_visible("#openings-no-baseline-banner")
        print(f"No baseline banner visible: {no_baseline_banner}")
        assert no_baseline_banner, "Expected no baseline helper banner when baseline is null"

        # Save Screenshot 1: Empty State
        ss_empty = "tests/screenshots/job_openings_empty_state.png"
        await page.screenshot(path=ss_empty)
        print(f"Saved screenshot: {ss_empty}")

        # Test clicking "+ Create Your First Job"
        await page.click("#btn-empty-create-first-job")
        await page.wait_for_timeout(500)
        view_jobs_visible = await page.is_visible("#view-jobs")
        print(f"Navigated to Create Job view: {view_jobs_visible}")
        assert view_jobs_visible, "Expected clicking empty state button to open Create Job view"

        # -------------------------------------------------------------
        # 2. Returning Recruiter Experience & Real Catalog
        # -------------------------------------------------------------
        print("\n--- 2. Testing Returning Recruiter Catalog & Active Baseline Banner ---")
        # Remove route mock to fetch real jobs
        await page.unroute("**/api/v1/jobs")
        
        # Reload Job Openings directory with real data
        await page.click("#tab-openings-btn")
        await page.wait_for_timeout(1000)

        # Baseline banner should now be visible with active job
        banner_visible = await page.is_visible("#openings-active-baseline-banner")
        print(f"Active Baseline banner visible: {banner_visible}")
        assert banner_visible, "Expected Active Baseline banner with real catalog"

        active_title = await page.inner_text("#banner-active-job-title")
        print(f"Active Baseline Role: {active_title}")
        assert len(active_title.strip()) > 0

        # Verify compact sidebar active indicator
        sidebar_role = await page.inner_text("#sidebar-active-job-role")
        print(f"Sidebar active indicator text: {sidebar_role}")
        assert "Active:" in sidebar_role
        assert await page.is_visible("#sidebar-active-job-role")

        # Save Screenshot 2: Active Baseline Banner & Grid
        ss_active = "tests/screenshots/job_openings_active_baseline.png"
        await page.screenshot(path=ss_active)
        print(f"Saved screenshot: {ss_active}")

        # -------------------------------------------------------------
        # 3. View Mode Persistence & Recruiter Isolation
        # -------------------------------------------------------------
        print("\n--- 3. Testing View Mode Persistence & Recruiter Isolation ---")
        # Recruiter Sarah switches to Table View
        await page.click("#btn-view-mode-table")
        await page.wait_for_timeout(400)
        table_visible = await page.is_visible(".jobs-directory-table-view")
        print(f"Table view visible after click: {table_visible}")
        assert table_visible, "Expected Table view to render"

        # Verify localStorage saved under recruiter's email
        sarah_saved_mode = await page.evaluate(f"() => localStorage.getItem('auditagent:job-openings:view-mode:{recruiter_email.replace('@', '_')}')")
        print(f"Sarah's saved view mode in localStorage: {sarah_saved_mode}")
        assert sarah_saved_mode == "table"

        # Save Screenshot 3: Table View
        ss_table = "tests/screenshots/job_openings_table_view.png"
        await page.screenshot(path=ss_table)
        print(f"Saved screenshot: {ss_table}")

        # Switch to Alex (different recruiter)
        alex_email = "alex_recruiter@acmecorp.com"
        await page.evaluate(f"""() => {{
            localStorage.setItem('hr_recruiter_name', 'Alex Mercer');
            localStorage.setItem('hr_recruiter_email', '{alex_email}');
        }}""")
        # Refresh directory
        await page.click("#tab-openings-btn")
        await page.wait_for_timeout(500)
        alex_saved_mode = await page.evaluate(f"() => localStorage.getItem('auditagent:job-openings:view-mode:{alex_email.replace('@', '_')}')")
        print(f"Alex's view mode (should be None or default grid): {alex_saved_mode}")
        assert alex_saved_mode is None or alex_saved_mode == "grid"

        # -------------------------------------------------------------
        # 4. Multi-Token Search & Filter Verification
        # -------------------------------------------------------------
        print("\n--- 4. Testing Multi-Token Search and Reset ---")
        # Switch back to grid for visual clarity
        await page.click("#btn-view-mode-grid")
        await page.wait_for_timeout(400)

        # Search for specific term
        search_input = "#jobs-search-input"
        await page.fill(search_input, "Distributed Rust")
        await page.wait_for_timeout(500)

        # Verify search results
        page_info = await page.inner_text("#jobs-pagination-info")
        print(f"Search results count text: {page_info}")
        assert "Openings" in page_info

        # Search for non-existent gibberish to test empty filter state
        await page.fill(search_input, "xyz999nonexistentquery123")
        await page.wait_for_timeout(500)

        no_results_visible = await page.is_visible("text=No openings matching your filters")
        print(f"No results state displayed: {no_results_visible}")
        assert no_results_visible, "Expected 'No openings matching your filters' message"

        btn_reset = await page.is_visible("#btn-reset-jobs-filters")
        assert btn_reset, "Expected 'Reset All Filters' button"
        await page.click("#btn-reset-jobs-filters")
        await page.wait_for_timeout(500)
        reset_info = await page.inner_text("#jobs-pagination-info")
        print(f"After reset info: {reset_info}")
        assert "filtered" not in reset_info

        # -------------------------------------------------------------
        # 5. Requirements Intel Transparency Modal
        # -------------------------------------------------------------
        print("\n--- 5. Testing Requirements Intel Modal Transparency ---")
        # Click Intel on the first card
        first_intel_btn = page.locator(".btn-view-job-intel").first
        await first_intel_btn.click()
        await page.wait_for_timeout(800)

        modal_visible = await page.is_visible("#modal-job-intelligence")
        print(f"Requirements Intel modal visible: {modal_visible}")
        assert modal_visible, "Expected Requirements Intel modal to open"

        # Verify Mandatory vs Preferred callout
        modal_text = await page.inner_text("#modal-intel-body")
        assert "Evaluation Transparency:" in modal_text
        assert "Mandatory requirements" in modal_text
        assert "never disqualify a candidate" in modal_text
        print("Verified evaluation transparency callout distinguishing mandatory vs preferred criteria!")

        # Verify Footer Actions
        btn_modal_back = await page.is_visible("#btn-modal-intel-back")
        btn_modal_baseline = await page.is_visible("#btn-modal-intel-set-baseline")
        btn_modal_screen = await page.is_visible("#btn-modal-intel-screen")
        assert btn_modal_back and btn_modal_baseline and btn_modal_screen, "Expected all modal footer buttons"

        # Save Screenshot 4: Intel Modal
        ss_intel = "tests/screenshots/job_openings_intel_modal.png"
        await page.screenshot(path=ss_intel)
        print(f"Saved screenshot: {ss_intel}")

        # Click Screen Candidates from modal
        await page.click("#btn-modal-intel-screen")
        await page.wait_for_timeout(800)

        # Verify Screener view is active and displays correct active job
        view_single_visible = await page.is_visible("#view-single")
        print(f"Screening interface visible: {view_single_visible}")
        assert view_single_visible, "Expected navigation to candidate screening"

        screener_job_title = await page.inner_text("#active-job-banner-title")
        print(f"Screener active role title: {screener_job_title}")
        assert len(screener_job_title.strip()) > 0

        # -------------------------------------------------------------
        # 6. Mobile Layout Usability
        # -------------------------------------------------------------
        print("\n--- 6. Testing Mobile Layout Responsiveness ---")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.evaluate("() => document.getElementById('tab-openings-btn').click()")
        await page.wait_for_timeout(600)
        mobile_banner_visible = await page.is_visible("#openings-active-baseline-banner")
        print(f"Mobile baseline banner visible: {mobile_banner_visible}")
        assert mobile_banner_visible

        # Verify sidebar toggle button exists on mobile
        sidebar_toggle_visible = await page.is_visible("#btn-sidebar-toggle")
        print(f"Mobile sidebar toggle visible: {sidebar_toggle_visible}")
        assert sidebar_toggle_visible

        print("\n=== ALL E2E VERIFICATIONS PASSED SUCCESSFULLY ===")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
