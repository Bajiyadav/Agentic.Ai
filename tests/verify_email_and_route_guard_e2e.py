"""
Playwright End-to-End Verification for:
1. Strict Authentication Route Guard (unauthenticated -> /landing.html)
2. Recruiter Sign In -> Workspace Entry
3. Candidate Assessment Email Dispatch UI & Resend Email Button
4. Sign Out and Session Purge
"""
import asyncio
import os
import shutil
from playwright.async_api import async_playwright

ARTIFACTS_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/f1888d8f-131c-4dcd-98e6-39b7bafe91e3"

async def run_verification():
    print("=== STARTING AUTH ROUTE GUARD & EMAIL DISPATCH E2E VERIFICATION ===")
    os.makedirs("tests/screenshots", exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        page = await context.new_page()

        # -------------------------------------------------------------
        # 1. Unauthenticated Route Guard Verification
        # -------------------------------------------------------------
        print("\n1. Testing Strict Route Guard: Unauthenticated Visit to / ...")
        # Ensure clean state
        await page.goto("http://127.0.0.1:8000/landing.html")
        await page.evaluate("() => localStorage.clear()")

        # Try to visit root workspace in strict auth mode without credentials
        await page.goto("http://127.0.0.1:8000/?auth=strict")
        await page.wait_for_timeout(1000)

        current_url = page.url
        print(f"Current URL after visiting /?auth=strict unauthenticated: {current_url}")
        assert "landing.html" in current_url, f"Expected redirect to landing.html, got: {current_url}"
        await page.screenshot(path="tests/screenshots/auth_guard_redirected_to_landing.png")
        print("Saved tests/screenshots/auth_guard_redirected_to_landing.png")

        # -------------------------------------------------------------
        # 2. Sign In via Persona -> Workspace Entry
        # -------------------------------------------------------------
        print("\n2. Testing Persona Sign In -> Workspace Entry...")
        # Click Sarah Jenkins persona login on landing page
        sarah_btn = page.locator("#btn-login-sarah")
        if not await sarah_btn.is_visible():
            # Open sign in modal
            await page.click("#btn-open-sign-in")
            await page.wait_for_timeout(400)
        await page.click("#btn-login-sarah")
        await page.wait_for_timeout(1500)

        workspace_url = page.url
        print(f"Current URL after Sarah sign in: {workspace_url}")
        assert "landing.html" not in workspace_url, "Expected entry into workspace"

        # Check topbar profile display
        topbar_name = await page.inner_text("#topbar-user-name")
        print(f"Active recruiter in workspace: {topbar_name}")
        assert "Sarah" in topbar_name
        await page.screenshot(path="tests/screenshots/auth_workspace_logged_in.png")
        print("Saved tests/screenshots/auth_workspace_logged_in.png")

        # -------------------------------------------------------------
        # 3. Assessment Email Dispatch UI & Resend Verification
        # -------------------------------------------------------------
        print("\n3. Testing Assessment Invitation Email Delivery Bar & Resend...")
        # Navigate to Single Candidate Screening
        await page.click("#tab-single-btn")
        await page.wait_for_timeout(1000)

        # Ensure candidate assessment section has email delivery bar
        email_bar = page.locator("#candidate-email-delivery-bar")
        btn_resend = page.locator("#btn-resend-candidate-email")

        # Check if candidate invite info box exists in DOM
        assert await page.locator("#candidate-invite-info-box").count() > 0
        assert await email_bar.count() > 0
        assert await btn_resend.count() > 0
        print("Candidate email delivery status bar and Resend Email button verified in DOM!")

        # -------------------------------------------------------------
        # 4. Sign Out and Session Purge
        # -------------------------------------------------------------
        print("\n4. Testing Sign Out...")
        await page.click("#btn-topbar-user-badge")
        await page.wait_for_timeout(300)

        signout_btn = page.locator("#btn-topbar-signout")
        assert await signout_btn.is_visible(), "Expected Sign Out button to be visible in dropdown"
        await signout_btn.click()
        await page.wait_for_timeout(1200)

        after_signout_url = page.url
        print(f"URL after Sign Out: {after_signout_url}")
        assert "landing.html" in after_signout_url, "Expected redirect to landing.html after sign out"

        # Verify localStorage was purged
        jwt_in_storage = await page.evaluate("() => localStorage.getItem('auditagent_jwt')")
        user_in_storage = await page.evaluate("() => localStorage.getItem('hr_recruiter_name')")
        logged_out_flag = await page.evaluate("() => sessionStorage.getItem('auditagent_logged_out')")
        print(f"Stored JWT after logout: {jwt_in_storage}")
        print(f"Stored recruiter name after logout: {user_in_storage}")
        print(f"Logged out session flag: {logged_out_flag}")
        assert jwt_in_storage is None
        assert user_in_storage is None
        assert logged_out_flag == "true"

        # Test revisiting / after explicit logout -> MUST redirect to landing.html
        print("Testing revisit to / after explicit logout...")
        await page.goto("http://127.0.0.1:8000/")
        await page.wait_for_timeout(800)
        revisit_url = page.url
        print(f"URL after attempting to revisit / while logged out: {revisit_url}")
        assert "landing.html" in revisit_url, "Expected route guard to block logged-out session from /"

        # Copy screenshots to artifact directory
        for img_name in ["auth_guard_redirected_to_landing.png", "auth_workspace_logged_in.png"]:
            src = os.path.join("tests/screenshots", img_name)
            dst = os.path.join(ARTIFACTS_DIR, img_name)
            if os.path.exists(src):
                shutil.copyfile(src, dst)
                print(f"Copied to artifact: {dst}")

        await browser.close()
        print("\n🎉 ALL AUTH GUARD & EMAIL E2E VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_verification())
