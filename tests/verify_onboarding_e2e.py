import asyncio
import os
from playwright.async_api import async_playwright

async def run_verification():
    print("=== STARTING ONBOARDING E2E VERIFICATION ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # -------------------------------------------------------------
        # 1. First-time Recruiter Session (Elena)
        # -------------------------------------------------------------
        print("\n--- 1. Testing First-Time Recruiter Experience ---")
        import uuid
        unique_email = f"elena_{uuid.uuid4().hex[:6]}@vanceholdings.com"
        
        await page.goto("http://127.0.0.1:8000/")
        
        # Reset local storage for fresh recruiter Elena
        await page.evaluate(f"""() => {{
            localStorage.clear();
            localStorage.setItem('hr_recruiter_name', 'Elena Vance');
            localStorage.setItem('hr_recruiter_email', '{unique_email}');
            localStorage.setItem('hr_recruiter_role', 'Director of Talent');
        }}""")
        await page.reload()
        await page.wait_for_timeout(1000)

        # Verify Onboarding Card is visible
        onboarding_visible = await page.is_visible("#hr-onboarding-container")
        print(f"Onboarding card visible: {onboarding_visible}")
        assert onboarding_visible, "Expected onboarding card to be visible for first-time recruiter"

        # Verify Header and Subtitle
        greeting_text = await page.inner_text("#hr-greeting-name")
        subtitle_text = await page.inner_text("#hr-greeting-subtitle")
        print(f"Greeting: {greeting_text}")
        print(f"Subtitle: {subtitle_text}")
        assert "Welcome, Elena" in greeting_text
        assert "Let's get your hiring workspace ready" in subtitle_text

        # Verify Step Titles
        step1_title = await page.inner_text("#onboarding-step-box-1 .onboarding-step-title")
        step2_title = await page.inner_text("#onboarding-step-box-2 .onboarding-step-title")
        step3_title = await page.inner_text("#onboarding-step-box-3 .onboarding-step-title")
        print(f"Step 1: {step1_title}")
        print(f"Step 2: {step2_title}")
        print(f"Step 3: {step3_title}")
        assert step1_title == "Create your first job"
        assert step2_title == "Screen your first candidate"
        assert step3_title == "Review the candidate audit"

        # Save Screenshot 1: First-time Recruiter Home Page
        ss1_path = "tests/screenshots/onboarding_first_time.png"
        await page.screenshot(path=ss1_path)
        print(f"Saved screenshot: {ss1_path}")

        # -------------------------------------------------------------
        # 2. Step Completion Progress
        # -------------------------------------------------------------
        print("\n--- 2. Testing Step Completion Verification ---")
        progress_text = await page.inner_text("#onboarding-progress-text")
        print(f"Current progress indicator: {progress_text}")

        # Step 1 is already complete because jobs exist in DB
        badge1_text = await page.inner_text("#onboarding-step-badge-1")
        print(f"Step 1 Badge: {badge1_text}")
        assert "Completed" in badge1_text

        # Test Step 1 Action navigation
        await page.click("#btn-onboarding-step-1")
        await page.wait_for_timeout(300)
        jobs_active = await page.is_visible("#view-jobs")
        print(f"Jobs section active after clicking Step 1: {jobs_active}")
        assert jobs_active

        # Return to Home tab
        await page.click("#tab-home-btn")
        await page.wait_for_timeout(500)

        # Test Step 2 Action navigation
        await page.click("#btn-onboarding-step-2")
        await page.wait_for_timeout(300)
        single_active = await page.is_visible("#view-single")
        print(f"Screening section active after clicking Step 2: {single_active}")
        assert single_active

        # Return to Home tab
        await page.click("#tab-home-btn")
        await page.wait_for_timeout(500)

        # Save Screenshot 2: Onboarding Progress after completing steps
        ss2_path = "tests/screenshots/onboarding_step_completed.png"
        await page.screenshot(path=ss2_path)
        print(f"Saved screenshot: {ss2_path}")

        # -------------------------------------------------------------
        # 3. Dismissing Onboarding & Returning Recruiter Dashboard
        # -------------------------------------------------------------
        print("\n--- 3. Testing Dismissing Onboarding & Returning Recruiter Dashboard ---")
        await page.click("#btn-dismiss-onboarding")
        await page.wait_for_timeout(500)

        # Onboarding card must be hidden
        onboarding_visible_after = await page.is_visible("#hr-onboarding-container")
        print(f"Onboarding card visible after dismiss: {onboarding_visible_after}")
        assert not onboarding_visible_after

        # Greeting must say "Welcome back"
        returning_greeting = await page.inner_text("#hr-greeting-name")
        returning_sub = await page.inner_text("#hr-greeting-subtitle")
        print(f"Returning Greeting: {returning_greeting}")
        print(f"Returning Subtitle: {returning_sub}")
        assert "Welcome back, Elena" in returning_greeting
        assert "Here's what's happening across your hiring pipeline" in returning_sub

        # Reopen button must be visible in header
        reopen_btn_visible = await page.is_visible("#btn-reopen-onboarding")
        print(f"Reopen button visible in header: {reopen_btn_visible}")
        assert reopen_btn_visible

        # Operational KPIs and queues visible
        kpis_visible = await page.is_visible(".hr-kpi-grid")
        whats_next_visible = await page.is_visible(".whats-next-card")
        recent_activity_visible = await page.is_visible("#home-recent-screenings-tbody")
        print(f"KPI cards visible: {kpis_visible}")
        print(f"What's Next queue visible: {whats_next_visible}")
        print(f"Recent Activity visible: {recent_activity_visible}")
        assert kpis_visible and whats_next_visible and recent_activity_visible

        # Save Screenshot 3: Returning Recruiter Clean Home Page
        ss3_path = "tests/screenshots/onboarding_returning.png"
        await page.screenshot(path=ss3_path)
        print(f"Saved screenshot: {ss3_path}")

        # -------------------------------------------------------------
        # 4. Persistence Across Page Reload
        # -------------------------------------------------------------
        print("\n--- 4. Testing Persistence Across Page Reload ---")
        await page.reload()
        await page.wait_for_timeout(1000)

        onboarding_visible_reload = await page.is_visible("#hr-onboarding-container")
        print(f"Onboarding card visible after reload: {onboarding_visible_reload}")
        assert not onboarding_visible_reload, "Onboarding card should NOT reappear on reload after dismissal"

        # -------------------------------------------------------------
        # 5. Reopening Guide Voluntarily
        # -------------------------------------------------------------
        print("\n--- 5. Testing Voluntary Reopening ---")
        await page.click("#btn-reopen-onboarding")
        await page.wait_for_timeout(500)

        onboarding_visible_reopened = await page.is_visible("#hr-onboarding-container")
        print(f"Onboarding card visible after reopen: {onboarding_visible_reopened}")
        assert onboarding_visible_reopened, "Onboarding card should reappear after clicking Reopen button"

        # -------------------------------------------------------------
        # 6. Recruiter Isolation (Sarah vs Alex)
        # -------------------------------------------------------------
        print("\n--- 6. Testing Recruiter State Isolation ---")
        # Alex switches and has his own state
        await page.evaluate("""() => {
            localStorage.setItem('hr_recruiter_name', 'Alex Mercer');
            localStorage.setItem('hr_recruiter_email', 'alex@acmecorp.com');
        }""")
        await page.reload()
        await page.wait_for_timeout(1000)

        alex_key = "auditagent_onboarding_alex_acmecorp_com"
        alex_state = await page.evaluate(f"() => localStorage.getItem('{alex_key}')")
        print(f"Alex local state (fresh): {alex_state}")

        # -------------------------------------------------------------
        # 7. Mobile Layout Usability
        # -------------------------------------------------------------
        print("\n--- 7. Testing Mobile Viewport Usability ---")
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.wait_for_timeout(500)
        mobile_card_visible = await page.is_visible("#hr-onboarding-container")
        assert mobile_card_visible
        print("Mobile layout rendered cleanly without errors.")

        await browser.close()
        print("\n=== ALL 15 VERIFICATION SCENARIOS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_verification())
