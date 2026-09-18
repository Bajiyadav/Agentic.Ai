import os
import time
from playwright.sync_api import sync_playwright

def main():
    artifact_dir = "/Users/bajiyadav/.gemini/antigravity-ide/brain/21404dcf-842e-4ffa-8785-faf139b71f40"
    os.makedirs(artifact_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop View (1440x900) - Light Mode
        context_desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context_desktop.new_page()
        page.goto("http://localhost:8000/", wait_until="networkidle")
        time.sleep(1.5)

        # Take HR Home View Screenshot
        page.screenshot(path=f"{artifact_dir}/hr_redesign_01_desktop_home.png", full_page=False)
        print("Captured hr_redesign_01_desktop_home.png")

        # Click on Jobs tab to see the 6-Stage Stepper & Pipeline
        page.click("#tab-jobs-btn")
        time.sleep(1.0)
        page.screenshot(path=f"{artifact_dir}/hr_redesign_02_desktop_jobs_pipeline.png", full_page=False)
        print("Captured hr_redesign_02_desktop_jobs_pipeline.png")

        # 2. Dark Mode Screenshot
        page.click("#btn-theme-toggle")
        time.sleep(0.5)
        page.screenshot(path=f"{artifact_dir}/hr_redesign_03_dark_mode_jobs.png", full_page=False)
        print("Captured hr_redesign_03_dark_mode_jobs.png")

        # Return to home in dark mode
        page.click("#tab-home-btn")
        time.sleep(0.8)
        page.screenshot(path=f"{artifact_dir}/hr_redesign_04_dark_mode_home.png", full_page=False)
        print("Captured hr_redesign_04_dark_mode_home.png")

        context_desktop.close()

        # 3. Mobile View (390x844)
        context_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        )
        page_m = context_mobile.new_page()
        page_m.goto("http://localhost:8000/", wait_until="networkidle")
        time.sleep(1.5)
        page_m.screenshot(path=f"{artifact_dir}/hr_redesign_05_mobile_home.png", full_page=False)
        print("Captured hr_redesign_05_mobile_home.png")

        # Open drawer on mobile
        page_m.click("#btn-sidebar-toggle")
        time.sleep(0.5)
        page_m.screenshot(path=f"{artifact_dir}/hr_redesign_06_mobile_drawer.png", full_page=False)
        print("Captured hr_redesign_06_mobile_drawer.png")

        context_mobile.close()
        browser.close()

if __name__ == "__main__":
    main()
