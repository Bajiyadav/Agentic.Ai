import asyncio
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/21404dcf-842e-4ffa-8785-faf139b71f40"

async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Viewport
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()
        await page.goto("http://localhost:8000/", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Capture Home workspace with showcase launcher
        await page.screenshot(path=f"{ARTIFACT_DIR}/recruiter_showcase_01_home_launcher.png")
        print("Captured recruiter_showcase_01_home_launcher.png")

        # Click tab-showcase-btn to navigate to Progress Dashboard
        await page.click("#tab-showcase-btn")
        await page.wait_for_timeout(1000)

        # Scroll to dashboard and capture
        await page.locator("#view-showcase").scroll_into_view_if_needed()
        await page.screenshot(path=f"{ARTIFACT_DIR}/recruiter_showcase_02_progress_dashboard_desktop.png")
        print("Captured recruiter_showcase_02_progress_dashboard_desktop.png")

        # Open Edit Profile modal
        await page.click("#btn-edit-pd-profile")
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{ARTIFACT_DIR}/recruiter_showcase_03_profile_modal.png")
        print("Captured recruiter_showcase_03_profile_modal.png")

        # Close modal
        await page.click("#btn-close-pd-modal")
        await page.wait_for_timeout(500)

        await context.close()

        # 2. Mobile Viewport
        context_mobile = await browser.new_context(viewport={"width": 390, "height": 844})
        page_mobile = await context_mobile.new_page()
        await page_mobile.goto("http://localhost:8000/", wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)

        # Click hamburger or directly trigger showcase tab
        await page_mobile.evaluate("() => document.getElementById('tab-showcase-btn').click()")
        await page_mobile.wait_for_timeout(800)

        await page_mobile.screenshot(path=f"{ARTIFACT_DIR}/recruiter_showcase_04_mobile.png")
        print("Captured recruiter_showcase_04_mobile.png")

        await context_mobile.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture())
