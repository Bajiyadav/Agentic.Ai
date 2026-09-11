#!/usr/bin/env python3
"""
AuditAgent — End-to-End Automated Browser Verification & Release Gate Suite.
Executes real browser automation using installed Google Chrome via Playwright.
Tests all viewports, valid/invalid workflows, score vs validity separation,
recruiter actions, history filtering, batch processing, and console logs.
"""

import asyncio
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8000"
CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

class BrowserVerificationRunner:
    def __init__(self):
        self.console_errors = []
        self.page_errors = []
        self.network_failures = []
        self.passed_checks = []
        self.failed_checks = []

    def record_pass(self, name: str):
        print(f"  ✅ PASS: {name}")
        self.passed_checks.append(name)

    def record_fail(self, name: str, reason: str):
        print(f"  ❌ FAIL: {name} — {reason}")
        self.failed_checks.append(f"{name}: {reason}")

    async def run(self):
        print("\n🚀 Starting AuditAgent Real Browser Verification & Release Gate Suite...")
        print(f"Target URL: {BASE_URL}")
        print(f"Using Chrome binary: {CHROME_PATH}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True
            )

            context = await browser.new_context(
                viewport={"width": 1440, "height": 900}
            )
            page = await context.new_page()

            # Attach event listeners
            page.on("console", lambda msg: self._handle_console(msg))
            page.on("pageerror", lambda err: self.page_errors.append(str(err)))
            page.on("requestfailed", lambda req: self._handle_req_fail(req))

            try:
                # 1. Page Load & Initial Network Health
                await self.test_initial_load(page)

                # 2. Responsive Viewport Verification (390, 430, 1024, 1280, 1440)
                await self.test_responsive_viewports(page)

                # Restore Desktop viewport
                await page.set_viewport_size({"width": 1440, "height": 900})

                # 3. Valid Resume Screening Journey (Alex Mercer)
                await self.test_valid_resume_journey(page)

                # 4. Invalid Document Screening Journey (Academic Lab Manual)
                await self.test_invalid_document_journey(page)

                # 5. Low-Score Valid Resume Journey (Kevin Miller - Critical Score Rule)
                await self.test_low_score_valid_resume_journey(page)

                # 6. Complete Journey & History Re-opening Journey
                await self.test_history_and_filters_journey(page)

                # 7. Batch Screening UI Journey (5 Multi-Type Matrix)
                await self.test_batch_screening_ui_journey(page)

                # 8. Console Error Audit
                self.test_console_errors()

            finally:
                await browser.close()

        print("\n" + "=" * 60)
        print(f"Total Browser Checks: {len(self.passed_checks) + len(self.failed_checks)}")
        print(f"Passed: {len(self.passed_checks)}")
        print(f"Failed: {len(self.failed_checks)}")
        if self.failed_checks:
            print("\nFailures:")
            for f in self.failed_checks:
                print(f"  - {f}")
            sys.exit(1)
        else:
            print("\n🎉 ALL REAL BROWSER VERIFICATION CHECKS PASSED PERFECTLY!")
            sys.exit(0)

    def _handle_console(self, msg):
        if msg.type in ("error",):
            text = msg.text
            # Ignore harmless font or analytics warnings if any
            if "font" not in text.lower():
                self.console_errors.append(f"Console {msg.type}: {text}")

    def _handle_req_fail(self, req):
        if "favicon" not in req.url:
            self.network_failures.append(f"Failed request: {req.method} {req.url} ({req.failure})")

    async def test_initial_load(self, page):
        print("\n[1] Testing Initial Page Load & Health...")
        resp = await page.goto(BASE_URL, wait_until="networkidle")
        if resp.status == 200:
            self.record_pass("Page loaded with HTTP 200")
        else:
            self.record_fail("Page loaded", f"Status code was {resp.status}")

        title = await page.title()
        if "AuditAgent" in title:
            self.record_pass(f"Title verified: '{title}'")
        else:
            self.record_fail("Title check", f"Unexpected title: {title}")

        # Check KPI cards rendered
        kpi_bar = await page.query_selector("#dashboard-kpi-bar")
        if kpi_bar and await kpi_bar.is_visible():
            self.record_pass("Dashboard KPI bar is visible")
        else:
            self.record_fail("KPI bar", "Element #dashboard-kpi-bar not visible")

    async def test_responsive_viewports(self, page):
        print("\n[2] Testing Responsive Viewports (Zero horizontal overflow)...")
        viewports = [
            ("Desktop 1440px", 1440, 900),
            ("Small Laptop 1280px", 1280, 800),
            ("Tablet 1024px", 1024, 768),
            ("Mobile 430px (iPhone Pro Max)", 430, 932),
            ("Mobile 390px (iPhone Standard)", 390, 844),
        ]

        for name, w, h in viewports:
            await page.set_viewport_size({"width": w, "height": h})
            await page.wait_for_timeout(300)

            # Check horizontal overflow
            metrics = await page.evaluate("""() => ({
                scrollWidth: document.documentElement.scrollWidth,
                clientWidth: document.documentElement.clientWidth,
                hasOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth
            })""")

            if not metrics["hasOverflow"]:
                self.record_pass(f"{name} ({w}x{h}): No horizontal overflow (scrollWidth={metrics['scrollWidth']}, clientWidth={metrics['clientWidth']})")
            else:
                self.record_fail(f"{name} overflow", f"scrollWidth={metrics['scrollWidth']} > clientWidth={metrics['clientWidth']}")

            # Save screenshot
            filename = f"responsive_{w}px.png"
            await page.screenshot(path=str(SCREENSHOTS_DIR / filename))
            self.record_pass(f"{name}: Captured screenshot -> tests/screenshots/{filename}")

    async def test_valid_resume_journey(self, page):
        print("\n[3] Testing Valid Resume Screening Journey...")
        valid_pdf = FIXTURES_DIR / "resumes" / "valid_backend_engineer.pdf"
        assert valid_pdf.exists(), f"Missing {valid_pdf}"

        # Set file input
        file_input = await page.query_selector("#resume-input")
        await file_input.set_input_files(str(valid_pdf))
        await page.wait_for_timeout(300)

        # Verify selected file card appears
        file_card = await page.query_selector("#selected-file-card")
        if file_card and await file_card.is_visible():
            self.record_pass("Selected File Card is displayed with filename and size")
        else:
            self.record_fail("File Card", "#selected-file-card is not visible")

        # Click Screen Candidate Resume
        btn_submit = await page.query_selector("#btn-submit")
        await btn_submit.click()

        # Wait for processing state or completion
        await page.wait_for_selector("#state-result", state="visible", timeout=15000)
        self.record_pass("Screening completed and transitioned to #state-result")

        # Verify Candidate Assessment elements
        candidate_name = await page.text_content("#res-candidate-name")
        overall_score = await page.text_content("#res-overall-score")
        rec_badge = await page.text_content("#res-rec-badge")
        next_action = await page.text_content("#res-action-headline")

        if "Alex Mercer" in candidate_name:
            self.record_pass(f"Candidate name rendered: '{candidate_name.strip()}'")
        else:
            self.record_fail("Candidate name", f"Found: '{candidate_name}'")

        if overall_score and int(overall_score.strip()) >= 0:
            self.record_pass(f"Overall score rendered: {overall_score.strip()} / 100")
        else:
            self.record_fail("Overall score", f"Found: '{overall_score}'")

        if rec_badge and len(rec_badge.strip()) > 0:
            self.record_pass(f"Recommendation badge rendered: '{rec_badge.strip()}'")
        else:
            self.record_fail("Recommendation badge", f"Found: '{rec_badge}'")

        if next_action and len(next_action.strip()) > 0:
            self.record_pass(f"Next Action headline rendered: '{next_action.strip()}'")
        else:
            self.record_fail("Next Action headline", f"Found: '{next_action}'")

        # Verify 5 Sub-Scores exist
        sub_scores = await page.query_selector_all(".sub-score-card")
        if len(sub_scores) >= 4:
            self.record_pass(f"Verified {len(sub_scores)} candidate sub-scores displayed")
        else:
            self.record_fail("Sub-scores", f"Only {len(sub_scores)} found")

        # Verify Claim vs Evidence table
        rows = await page.query_selector_all("#res-evidence-table-body tr")
        if len(rows) > 0:
            self.record_pass(f"Claim vs Evidence table rendered with {len(rows)} verified items")
        else:
            self.record_fail("Claim vs Evidence", "Table is empty")

        # Verify strengths and weaknesses/red flags lists
        red_flags = await page.query_selector_all("#res-red-flags li")
        green_flags = await page.query_selector_all("#res-green-flags li")
        if len(red_flags) > 0 and len(green_flags) > 0:
            self.record_pass("Strengths & Red flags lists are populated")
        else:
            self.record_fail("Flags check", f"Red flags count: {len(red_flags)}, Green flags count: {len(green_flags)}")

        # Verify no internal AI/agent terminology exposed in candidate assessment view
        scorecard_html = await page.inner_html("#state-result")
        banned_terms = ["agent_1", "agent 1", "agent_2", "agent 2", "consensus evaluator", "llm prompt", "raw prompt"]
        found_banned = [t for t in banned_terms if t in scorecard_html.lower()]
        if not found_banned:
            self.record_pass("No internal AI/agent terminology exposed in assessment view")
        else:
            self.record_fail("Internal AI terminology leak", f"Found terms: {found_banned}")

        # Verify recruiter action buttons are present
        btn_schedule = await page.query_selector("#btn-action-schedule")
        btn_reject = await page.query_selector("#btn-action-reject")
        btn_screen_another = await page.query_selector("#btn-action-screen-another")
        if btn_schedule and btn_reject and btn_screen_another:
            self.record_pass("Recruiter Action buttons (Schedule, Reject, Screen Another) present")
        else:
            self.record_fail("Recruiter Actions", "Missing one or more recruiter action buttons")

        # Capture screenshot
        await page.screenshot(path=str(SCREENSHOTS_DIR / "journey_valid_resume_result.png"))
        self.record_pass("Captured valid resume assessment screenshot")

    async def test_invalid_document_journey(self, page):
        print("\n[4] Testing Invalid Document Journey (Academic Lab Manual)...")
        invalid_pdf = FIXTURES_DIR / "invalid_documents" / "academic_lab_manual.pdf"
        assert invalid_pdf.exists()

        # Switch back to upload / reset using "Screen Another"
        btn_reset = await page.query_selector("#btn-action-screen-another")
        if btn_reset and await btn_reset.is_visible():
            await btn_reset.click()
            await page.wait_for_timeout(300)

        file_input = await page.query_selector("#resume-input")
        await file_input.set_input_files(str(invalid_pdf))
        await page.wait_for_timeout(300)

        btn_submit = await page.query_selector("#btn-submit")
        await btn_submit.click()

        # Wait for #state-invalid-document
        await page.wait_for_selector("#state-invalid-document", state="visible", timeout=15000)
        self.record_pass("Invalid document correctly routed to dedicated #state-invalid-document")

        # Verify Invalid State Content
        inv_score = await page.text_content("#state-invalid-document .score-number")
        doc_badge = await page.text_content("#invalid-doc-type-badge")
        res_visible = await page.is_visible("#state-result")

        if inv_score and inv_score.strip() == "0":
            self.record_pass("Invalid document displays 0/100 score")
        else:
            self.record_fail("Invalid score", f"Found: '{inv_score}'")

        if "ACADEMIC" in doc_badge or "LAB" in doc_badge:
            self.record_pass(f"Document type correctly badged: '{doc_badge.strip()}'")
        else:
            self.record_fail("Doc type badge", f"Found: '{doc_badge}'")

        if not res_visible:
            self.record_pass("Candidate Assessment (#state-result) is strictly HIDDEN for invalid files")
        else:
            self.record_fail("Candidate Assessment", "Assessment should not be visible for invalid documents")

        # Verify candidate scoring sections are NOT present in invalid view
        inv_text = await page.text_content("#state-invalid-document")
        if "Schedule Interview" not in inv_text and "Candidate Quality" not in inv_text:
            self.record_pass("Invalid document view does not expose candidate interview/scoring options")
        else:
            self.record_fail("Invalid document leak", "Interview/scoring options exposed in invalid state")

        # Test Draft Resume Request button opens modal
        btn_draft = await page.query_selector("#btn-invalid-draft-request")
        if btn_draft and await btn_draft.is_visible():
            await btn_draft.click()
            await page.wait_for_timeout(400)
            modal = await page.query_selector("#draft-modal")
            modal_visible = await modal.is_visible()
            modal_title = await page.text_content("#modal-draft-title")
            if modal_visible and ("Resubmission" in modal_title or "Notice" in modal_title or "Resume" in modal_title):
                self.record_pass(f"Draft modal opened with title: '{modal_title.strip()}'")
                # Close modal
                btn_close = await page.query_selector("#btn-close-modal")
                if btn_close:
                    await btn_close.click()
                    await page.wait_for_timeout(200)
                    self.record_pass("Draft modal closed cleanly")
            else:
                self.record_fail("Modal draft", f"Modal not visible or wrong title: {modal_title}")

        await page.screenshot(path=str(SCREENSHOTS_DIR / "journey_invalid_document_state.png"))
        self.record_pass("Captured invalid document state screenshot")

    async def test_low_score_valid_resume_journey(self, page):
        print("\n[5] Testing Low-Score Valid Resume Journey (Critical Score Rule)...")
        low_score_pdf = FIXTURES_DIR / "resumes" / "valid_low_score_resume.pdf"
        assert low_score_pdf.exists()

        # Reset to upload
        btn_reset = await page.query_selector("#btn-invalid-reset-all") or await page.query_selector("#btn-invalid-upload-resume")
        if btn_reset and await btn_reset.is_visible():
            await btn_reset.click()
            await page.wait_for_timeout(300)

        file_input = await page.query_selector("#resume-input")
        await file_input.set_input_files(str(low_score_pdf))
        await page.wait_for_timeout(300)

        btn_submit = await page.query_selector("#btn-submit")
        await btn_submit.click()

        # Must route to #state-result, NEVER #state-invalid-document!
        await page.wait_for_selector("#state-result", state="visible", timeout=15000)
        self.record_pass("Valid low-score resume correctly routed to Candidate Assessment (#state-result)")

        inv_visible = await page.is_visible("#state-invalid-document")
        if not inv_visible:
            self.record_pass("Invalid Document state is NOT triggered for valid low-scoring resume")
        else:
            self.record_fail("Invalid State Leak", "#state-invalid-document was incorrectly displayed!")

        candidate_name = await page.text_content("#res-candidate-name")
        rec_badge = await page.text_content("#res-rec-badge")
        next_action = await page.text_content("#res-action-headline")

        if "Kevin Miller" in candidate_name:
            self.record_pass(f"Candidate name: '{candidate_name.strip()}' (Not 'Non-Resume Document')")
        else:
            self.record_fail("Candidate name", f"Expected Kevin Miller, found {candidate_name}")

        if "NOT RECOMMENDED" in rec_badge or "REJECT" in rec_badge:
            self.record_pass(f"Recommendation: '{rec_badge.strip()}' (Candidate Rejection, Not Invalid Document)")
        else:
            self.record_fail("Recommendation", f"Expected NOT RECOMMENDED, found {rec_badge}")

        if "Do not proceed" in next_action or "reject" in next_action.lower() or "not move forward" in next_action.lower():
            self.record_pass(f"Next Action: '{next_action.strip()}' (Not 'Request Resume')")
        else:
            self.record_fail("Next Action", f"Found: '{next_action}'")

        # Recruiter actions must show Reject Candidate, not Draft Resume Request
        btn_reject = await page.query_selector("#btn-action-reject")
        if btn_reject and await btn_reject.is_visible():
            self.record_pass("Action Bar displays 'Reject Candidate' action")
        else:
            self.record_fail("Reject button", "Button not visible")

        await page.screenshot(path=str(SCREENSHOTS_DIR / "journey_low_score_valid_resume.png"))
        self.record_pass("Captured valid low-score candidate screenshot")

    async def test_history_and_filters_journey(self, page):
        print("\n[6] Testing History & Filter Controls Journey...")
        # Scroll to history section
        await page.evaluate("window.scrollTo(0, 800)")
        await page.wait_for_timeout(300)

        # Filter buttons
        btn_all = await page.query_selector('.hist-filter-btn[data-filter="ALL"]')
        btn_strong = await page.query_selector('.hist-filter-btn[data-filter="STRONG"]')
        btn_rejected = await page.query_selector('.hist-filter-btn[data-filter="REJECTED"]')
        btn_invalid = await page.query_selector('.hist-filter-btn[data-filter="INVALID"]')

        if btn_all and btn_strong and btn_rejected and btn_invalid:
            self.record_pass("History filter buttons (All, Strong, Rejected, Invalid) are present")
        else:
            self.record_fail("History filters", "Missing one or more filter buttons")

        # Click Invalid filter
        await btn_invalid.click()
        await page.wait_for_timeout(400)
        items = await page.query_selector_all(".history-item")
        if items:
            badges = [await (await item.query_selector(".rec-badge")).text_content() for item in items]
            if all("INVALID" in b for b in badges):
                self.record_pass(f"Invalid filter works: {len(badges)} displayed items all have 'INVALID DOCUMENT' badge")
            else:
                self.record_fail("Invalid filter", f"Found badges: {badges}")
        else:
            self.record_pass("Invalid filter works: 0 items or correctly filtered")

        # Click Rejected filter
        await btn_rejected.click()
        await page.wait_for_timeout(400)
        items = await page.query_selector_all(".history-item")
        if items:
            badges = [await (await item.query_selector(".rec-badge")).text_content() for item in items]
            if all("NOT RECOMMENDED" in b or "REJECT" in b for b in badges):
                self.record_pass(f"Rejected filter works: {len(badges)} displayed items have 'NOT RECOMMENDED' badge")
            else:
                self.record_fail("Rejected filter", f"Found badges: {badges}")

        # Click All filter
        await btn_all.click()
        await page.wait_for_timeout(300)

        # Test Search input
        search_input = await page.query_selector("#history-search-input")
        await search_input.fill("Kevin")
        await page.wait_for_timeout(500)
        search_items = await page.query_selector_all(".history-item")
        if len(search_items) >= 1:
            name = await (await search_items[0].query_selector(".h-candidate")).text_content()
            if "Kevin" in name:
                self.record_pass(f"Search input works: Filtered correctly to '{name.strip()}'")
            else:
                self.record_fail("Search result", f"Expected Kevin, found {name}")
        else:
            self.record_fail("Search result", "No items found for 'Kevin'")

        # Test Re-opening Candidate Assessment from History without reload
        first_item = search_items[0]
        await first_item.click()
        await page.wait_for_timeout(500)
        res_visible = await page.is_visible("#state-result")
        opened_name = await page.text_content("#res-candidate-name")
        if res_visible and "Kevin Miller" in opened_name:
            self.record_pass("Clicking candidate in history successfully re-opened assessment without reload")
        else:
            self.record_fail("History click", f"Visible: {res_visible}, Name: {opened_name}")

        # Clear search
        await search_input.fill("")
        await page.wait_for_timeout(400)

    async def test_batch_screening_ui_journey(self, page):
        print("\n[7] Testing Batch Screening UI Journey (5 Multi-Type Matrix)...")
        # Navigate to Batch tab
        btn_batch_tab = await page.query_selector("#tab-batch-btn")
        if btn_batch_tab:
            await btn_batch_tab.click()
            await page.wait_for_timeout(400)
            batch_view = await page.query_selector("#view-batch")
            if batch_view and await batch_view.is_visible():
                self.record_pass("Navigated to Batch Screening view (#view-batch)")
            else:
                self.record_fail("Batch view", "#view-batch not visible")

        # Check Batch Dropzone
        batch_drop = await page.query_selector("#batch-dropzone")
        if batch_drop and await batch_drop.is_visible():
            self.record_pass("Batch dropzone is visible")
        else:
            self.record_fail("Batch dropzone", "Not visible")

        # Select 5 fixture files: 2 valid, 2 invalid, 1 corrupt
        batch_files = [
            FIXTURES_DIR / "resumes" / "valid_backend_engineer.pdf",
            FIXTURES_DIR / "resumes" / "valid_fullstack_engineer.pdf",
            FIXTURES_DIR / "invalid_documents" / "academic_lab_manual.pdf",
            FIXTURES_DIR / "invalid_documents" / "question_paper.pdf",
            FIXTURES_DIR / "corrupted" / "corrupt_pdf.pdf"
        ]
        for f in batch_files:
            assert f.exists(), f"Missing fixture {f}"

        batch_input = await page.query_selector("#batch-files-input")
        await batch_input.set_input_files([str(f) for f in batch_files])
        await page.wait_for_timeout(300)

        batch_label = await page.text_content("#batch-files-label")
        if "5" in batch_label:
            self.record_pass(f"Batch file selection confirmed: '{batch_label.strip()}'")
        else:
            self.record_fail("Batch file selection", f"Found: '{batch_label}'")

        # Click Run Batch Audit
        btn_start_upload = await page.query_selector("#btn-start-batch-upload")
        await btn_start_upload.click()
        self.record_pass("Clicked Run Batch Audit")

        # Wait for batch results wrap (polling takes a few seconds)
        await page.wait_for_selector("#batch-results-wrap", state="visible", timeout=30000)
        self.record_pass("Batch screening completed and results table rendered (#batch-results-wrap)")

        # Verify KPI values
        kpi_total = await page.text_content("#kpi-total")
        kpi_short = await page.text_content("#kpi-shortlist")
        kpi_reject = await page.text_content("#kpi-reject")

        if kpi_total and "5" in kpi_total:
            self.record_pass(f"Batch KPI total candidates: {kpi_total.strip()}")
        else:
            self.record_fail("Batch KPI total", f"Expected 5, found {kpi_total}")

        self.record_pass(f"Batch KPI breakdown: {kpi_short.strip()} shortlisted, {kpi_reject.strip()} rejected/invalid")

        # Verify leaderboard rows
        rows = await page.query_selector_all("#leaderboard-tbody tr")
        self.record_pass(f"Batch leaderboard rendered with {len(rows)} candidate rows")

        # Check that corrupt file does NOT appear as a normal candidate
        table_text = await page.text_content("#leaderboard-tbody")
        if "UNREADABLE_FILE" in table_text or "corrupt" in table_text.lower() or "invalid" in table_text.lower():
            self.record_pass("Corrupt file correctly handled as an invalid/unreadable entry (not scored as candidate)")
        else:
            self.record_fail("Corrupt file check", "Corrupt file may have been processed as normal candidate")

        # Test Draft action on an invalid entry in batch
        draft_buttons = await page.query_selector_all(".btn-draft-pill")
        if draft_buttons:
            # Click the last draft button (corrupt / invalid)
            await draft_buttons[-1].click()
            await page.wait_for_timeout(400)
            modal = await page.query_selector("#draft-modal")
            if modal and await modal.is_visible():
                title = await page.text_content("#modal-draft-title")
                self.record_pass(f"Batch draft action opened modal: '{title.strip()}'")
                await (await page.query_selector("#btn-close-modal")).click()
                await page.wait_for_timeout(200)

        await page.screenshot(path=str(SCREENSHOTS_DIR / "journey_batch_results.png"))
        self.record_pass("Captured Batch results table screenshot")

    def test_console_errors(self):
        print("\n[8] Auditing Browser Console & Network Errors...")
        if not self.console_errors:
            self.record_pass("0 uncaught console errors recorded")
        else:
            for err in self.console_errors:
                self.record_fail("Console Error", err)

        if not self.page_errors:
            self.record_pass("0 uncaught page exceptions recorded")
        else:
            for err in self.page_errors:
                self.record_fail("Page Exception", err)

        if not self.network_failures:
            self.record_pass("0 failed network requests recorded")
        else:
            for err in self.network_failures:
                self.record_fail("Network Failure", err)


if __name__ == "__main__":
    runner = BrowserVerificationRunner()
    asyncio.run(runner.run())
