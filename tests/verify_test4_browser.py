import asyncio
import os
from playwright.async_api import async_playwright
import io
from reportlab.pdfgen import canvas

ARTIFACTS_DIR = "/Users/bajiyadav/.gemini/antigravity-ide/brain/21404dcf-842e-4ffa-8785-faf139b71f40"
TEMP_DIR = "/tmp/auditagent_test4"
os.makedirs(TEMP_DIR, exist_ok=True)

def generate_test_pdf(filepath: str):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Jane Doe")
    c.drawString(100, 735, "Email: jane.doe@example.com | Phone: +1-555-0199 | Location: San Francisco, CA")
    c.drawString(100, 720, "Role: Senior Backend Engineer")
    c.drawString(100, 700, "Professional Summary:")
    c.drawString(100, 685, "Experienced backend engineer with 7+ years developing distributed microservices.")
    c.drawString(100, 665, "Technical Skills:")
    c.drawString(100, 650, "Languages: Python, Go, Java, TypeScript")
    c.drawString(100, 635, "Frameworks: FastAPI, Django, Spring Boot")
    c.drawString(100, 620, "Databases: PostgreSQL, Redis, Cassandra")
    c.drawString(100, 605, "Cloud & DevOps: AWS, Docker, Kubernetes, Terraform")
    c.drawString(100, 590, "Tools: Git, Kafka, Prometheus")
    c.drawString(100, 570, "Work Experience:")
    c.drawString(100, 555, "Senior Software Engineer - Stripe (2021 - Present)")
    c.drawString(100, 540, "Engineered fault-tolerant distributed payment settlement pipelines using Kafka.")
    c.drawString(100, 520, "Education:")
    c.drawString(100, 505, "B.S. in Computer Science - UC Berkeley")
    c.drawString(100, 485, "Projects:")
    c.drawString(100, 470, "Raft Consensus Cluster: Implemented distributed consensus protocol in Go.")
    c.save()
    buf.seek(0)
    with open(filepath, "wb") as f:
        f.write(buf.read())

async def main():
    resume_path = os.path.join(TEMP_DIR, "jane_doe_senior_backend.pdf")
    generate_test_pdf(resume_path)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop Test: Job Selection -> Resume Upload -> Parsed Claims Display
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("Navigating to http://localhost:8000...")
        await page.goto("http://localhost:8000", wait_until="networkidle")
        await asyncio.sleep(1)

        # Switch to Single Candidate Audit tab
        await page.click("#tab-single-btn")
        await asyncio.sleep(0.5)

        # Ensure active job context banner is visible
        job_banner = page.locator("#active-job-context-banner")
        await job_banner.wait_for(state="visible", timeout=10000)
        job_title_text = await page.locator("#active-job-banner-title").inner_text()
        print(f"Active parent job context: {job_title_text}")

        # Screenshot 1: Active Job Context Banner Ready
        await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "test4_01_desktop_active_job_ready.png"))
        print("Captured test4_01_desktop_active_job_ready.png")

        # Set file on resume input
        file_input = page.locator("#resume-input")
        await file_input.set_input_files(resume_path)
        await asyncio.sleep(0.8)

        # Click the dedicated Test 4 button: "Upload & Parse Resume Claims (Test 4)"
        btn_parse = page.locator("#btn-parse-claims-only")
        await btn_parse.wait_for(state="visible")
        await btn_parse.click()

        # Wait for candidate record card to become visible
        candidate_card = page.locator("#candidate-record-card")
        await candidate_card.wait_for(state="visible", timeout=15000)
        await asyncio.sleep(1)

        # Screenshot 2: Candidate Record with Unverified Claims & Job Association
        await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "test4_02_candidate_claims_parsed_desktop.png"))
        print("Captured test4_02_candidate_claims_parsed_desktop.png")

        # 2. Dark Mode Verification
        theme_toggle = page.locator("#btn-theme-toggle")
        await theme_toggle.click()
        await asyncio.sleep(0.8)
        await page.screenshot(path=os.path.join(ARTIFACTS_DIR, "test4_03_dark_mode_candidate_record.png"))
        print("Captured test4_03_dark_mode_candidate_record.png")
        await context.close()

        # 3. Mobile Viewport Verification (375x667)
        mobile_context = await browser.new_context(viewport={"width": 375, "height": 667}, is_mobile=True)
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://localhost:8000", wait_until="networkidle")
        await asyncio.sleep(1)
        await mobile_page.click("#btn-sidebar-toggle")
        await asyncio.sleep(0.5)
        await mobile_page.click("#tab-single-btn")
        await asyncio.sleep(0.5)

        # Set input file on mobile
        m_file_input = mobile_page.locator("#resume-input")
        await m_file_input.set_input_files(resume_path)
        await asyncio.sleep(0.8)

        m_btn_parse = mobile_page.locator("#btn-parse-claims-only")
        await m_btn_parse.click()
        await mobile_page.locator("#candidate-record-card").wait_for(state="visible", timeout=15000)
        await asyncio.sleep(1)

        # Screenshot 4: Mobile Responsive Candidate Record
        await mobile_page.screenshot(path=os.path.join(ARTIFACTS_DIR, "test4_04_mobile_candidate_record.png"))
        print("Captured test4_04_mobile_candidate_record.png")
        await mobile_context.close()

        # 4. Error State Verification: Invalid File Format
        err_context = await browser.new_context(viewport={"width": 1440, "height": 900})
        err_page = await err_context.new_page()
        await err_page.goto("http://localhost:8000", wait_until="networkidle")
        await asyncio.sleep(1)
        await err_page.click("#tab-single-btn")
        await asyncio.sleep(0.5)

        # Create dummy unsupported file
        invalid_path = os.path.join(TEMP_DIR, "invalid_image.png")
        with open(invalid_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\ncorrupted")

        await err_page.locator("#resume-input").set_input_files(invalid_path)
        await asyncio.sleep(0.5)
        await err_page.locator("#btn-parse-claims-only").click()
        await asyncio.sleep(1)

        # Wait for error banner
        err_banner = err_page.locator("#candidate-upload-error-banner")
        await err_banner.wait_for(state="visible", timeout=5000)
        print("Error banner text:", await err_banner.inner_text())

        # Screenshot 5: Error Banner for Invalid File Format
        await err_page.screenshot(path=os.path.join(ARTIFACTS_DIR, "test4_05_invalid_upload_error_banner.png"))
        print("Captured test4_05_invalid_upload_error_banner.png")
        await err_context.close()

        await browser.close()
        print(f"Browser verification completed successfully! Console errors count: {len(console_errors)}")

if __name__ == "__main__":
    asyncio.run(main())
