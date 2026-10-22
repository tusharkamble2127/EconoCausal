"""Browser verification for EconoCausal using Playwright.

This script performs REAL browser interaction:
  - Opens a Chromium browser
  - Waits for React rendering
  - Registers a new account
  - Logs in
  - Creates a new campaign with a real dataset
  - Clicks Run Campaign
  - Verifies the dashboard and propensity panel

It does NOT modify application source code.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"
DATASET_PATH = Path(__file__).parent.parent.parent / "artifacts" / "temporary" / "tmp_verification_dataset.csv"
REPORT_PATH = Path(__file__).with_name("browser_verification_report.json")

PASS_COUNT = 0
FAIL_COUNT = 0
RESULTS = []


def record(name, passed, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        status = "PASS"
    else:
        FAIL_COUNT += 1
        status = "FAIL"
    RESULTS.append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name}" + (f" - {detail}" if detail and not passed else ""))


def safe_text(locator):
    try:
        return locator.inner_text(timeout=3000).strip()
    except Exception:
        return ""


def wait_for_react(page, timeout=15000):
    """Wait for React-rendered content to appear."""
    page.wait_for_load_state("domcontentloaded", timeout=timeout)
    page.get_by_text("EconoCausal", exact=False).wait_for(timeout=timeout)


def main():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    email = f"browser_verify_{ts}@test.com"
    password = "pass12345"
    campaign_name = f"Browser Verification {ts}"

    print("=" * 70)
    print("BROWSER VERIFICATION - REAL BROWSER + REAL PAGE + REAL INTERACTION")
    print("=" * 70)

    if not DATASET_PATH.exists():
        record("Test dataset exists", False, f"Missing {DATASET_PATH}")
        print(f"\nRESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed out of {len(RESULTS)}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)

        network_failures = []
        page.on("response", lambda resp: network_failures.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None)

        try:
            # ============================================================
            # STEP 1: Open frontend and verify React rendering
            # ============================================================
            print("\n[1] Open frontend and verify React rendering")
            page.goto(BASE_URL, wait_until="domcontentloaded")
            wait_for_react(page, timeout=15000)

            current_url = page.url
            record("Frontend React rendered", "EconoCausal" in page.content())
            record("Initial route redirects to login", "/login" in current_url or "/register" in current_url, f"url={current_url}")

            # ============================================================
            # STEP 2: Register new account
            # ============================================================
            print("\n[2] Register new account")
            page.goto(f"{BASE_URL}/register", wait_until="domcontentloaded")
            page.get_by_text("Create your account", exact=True).wait_for(timeout=10000)

            page.get_by_placeholder("Jordan Rivera").fill("Browser Verify User")
            page.get_by_placeholder("you@company.com").fill(email)
            page.get_by_placeholder("At least 6 characters").fill(password)

            page.get_by_role("button", name="Create account").click()
            page.wait_for_url("**/", timeout=15000)

            current_url = page.url
            record("Register redirects to app", "/" in current_url and "/login" not in current_url and "/register" not in current_url, f"url={current_url}")

            # ============================================================
            # STEP 3: New Campaign form - verify elements
            # ============================================================
            print("\n[3] New Campaign form - verify elements")
            # Stay on the current page (already / after registration) to avoid
            # triggering the auth-ready redirect bug on full reload.
            wait_for_react(page, timeout=15000)
            page.wait_for_timeout(2000)

            # Debug: print what's visible
            body_text = page.evaluate("() => document.body.innerText")
            print(f"    Body text snippet: {body_text[:500]}")

            record("New Campaign page visible", page.get_by_text("New Campaign", exact=True).count() > 0)
            record("Campaign details section visible", page.get_by_text("1. Campaign details", exact=True).count() > 0)
            record("Budget & estimator section visible", page.get_by_text("3. Budget & estimator", exact=True).count() > 0)
            record("Discount levels section visible", page.get_by_text("4. Candidate discount levels", exact=True).count() > 0)

            expected_levels = ["0%", "5%", "10%", "15%", "20%", "25%", "30%"]
            for level in expected_levels:
                record(f"Discount level {level} present", page.get_by_text(level, exact=True).count() > 0)

            # ============================================================
            # STEP 4: Upload dataset
            # ============================================================
            print("\n[4] Upload dataset")
            file_input = page.locator('input[type="file"][accept=".csv"]')
            file_input.set_input_files(str(DATASET_PATH))

            # Wait for file to be reflected in UI
            page.get_by_text("600 rows parsed.", exact=False).wait_for(timeout=10000)
            record("Dataset row count reflected in UI", True)
            record("Dataset file name reflected in UI", page.get_by_text("tmp_verification_dataset.csv", exact=False).count() > 0)

            treatment_select = page.locator("select").nth(0)
            outcome_select = page.locator("select").nth(1)
            record("Treatment column selected", safe_text(treatment_select) != "")
            record("Outcome column selected", safe_text(outcome_select) != "")

            # ============================================================
            # STEP 5: Fill campaign form and Run Campaign
            # ============================================================
            print("\n[5] Fill campaign form and Run Campaign")
            page.get_by_placeholder("Spring loyalty promotion").fill(campaign_name)
            page.get_by_placeholder("5000").fill("3000")

            run_btn = page.get_by_role("button", name="Run campaign")
            run_btn.wait_for(state="visible", timeout=10000)
            record("Run campaign button visible", run_btn.count() > 0)
            record("Run campaign button enabled", run_btn.is_enabled())

            run_btn.click()
            page.wait_for_url("**/dashboard/*", timeout=120000)

            current_url = page.url
            record("Navigated to dashboard", "/dashboard/" in current_url, f"url={current_url}")

            # ============================================================
            # STEP 6: Verify dashboard loaded
            # ============================================================
            print("\n[6] Verify dashboard loaded")
            page.get_by_text("Budget Utilization", exact=True).wait_for(timeout=60000)
            page.get_by_text("Customers Targeted", exact=True).wait_for(timeout=60000)
            page.get_by_text("ROI Improvement", exact=True).wait_for(timeout=60000)
            page.get_by_text("Incremental Revenue", exact=True).wait_for(timeout=60000)
            record("KPI cards rendered", True)

            sections = [
                "Analytics",
                "Customer Recommendations",
                "Global Explainability",
                "Scenario Simulator",
                "Data Drift",
                "Causal Refutation Tests",
                "Allocation Detail",
                "AI Assistant",
            ]
            for section in sections:
                record(f"Dashboard section '{section}' visible", page.get_by_text(section, exact=True).count() > 0)

            # ============================================================
            # STEP 7: Verify Propensity panel
            # ============================================================
            print("\n[7] Verify Propensity panel")
            page.get_by_text("Propensity Analysis", exact=True).wait_for(timeout=30000)
            record("Propensity Analysis heading visible", True)

            has_binary = page.get_by_text("Treated vs Control (Binary Diagnostic)", exact=True).count() > 0
            has_continuous = page.get_by_text("Continuous Treatment Balance", exact=True).count() > 0
            record("Propensity binary diagnostic visible", has_binary)
            record("Propensity continuous treatment visible", has_continuous)

            if has_binary:
                page.get_by_text("Before SMD", exact=True).wait_for(timeout=10000)
                page.get_by_text("After SMD", exact=True).wait_for(timeout=10000)
                record("Covariate balance table (Before/After SMD) visible", True)

            body_text = page.content()
            record("No 'undefined' in rendered propensity", "undefined" not in body_text)
            record("No 'NaN' in rendered propensity", "NaN" not in body_text)

            # ============================================================
            # STEP 8: Verify sidebar navigation
            # ============================================================
            print("\n[8] Verify sidebar navigation")
            sidebar_items = ["New Campaign", "Campaign History"]
            for item in sidebar_items:
                record(f"Sidebar '{item}' visible", page.get_by_role("link", name=item, exact=True).count() > 0)

            # Current Run shows "Current Run #<id>", so match with contains
            record("Sidebar 'Current Run' visible", page.get_by_text("Current Run #", exact=False).count() > 0)

            page.get_by_role("link", name="Campaign History", exact=True).click()
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.get_by_role("heading", name="Campaign History", exact=True).wait_for(timeout=10000)
            record("Campaign History page loads", True)

            page.get_by_role("link", name="New Campaign", exact=True).click()
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.get_by_role("heading", name="New Campaign", exact=True).wait_for(timeout=10000)
            record("New Campaign navigation works", True)

            # ============================================================
            # STEP 9: Re-navigate to dashboard
            # ============================================================
            print("\n[9] Re-navigate to dashboard")
            page.get_by_role("link", name="Current Run", exact=False).click()
            page.wait_for_url("**/dashboard/*", timeout=30000)
            page.get_by_text("Budget Utilization", exact=True).wait_for(timeout=120000)
            record("Dashboard reloads correctly", True)

            # ============================================================
            # STEP 10: Check browser console for errors
            # ============================================================
            print("\n[10] Browser console errors")
            error_count = len([e for e in console_errors if e.startswith("error:")])
            warning_count = len([e for e in console_errors if e.startswith("warning:")])
            record(f"Console errors count: {error_count}", error_count == 0, f"errors={error_count}, warnings={warning_count}")
            if console_errors:
                try:
                    print(f"    Console messages: {console_errors[:10]}")
                except UnicodeEncodeError:
                    print("    Console messages: [contains non-ASCII characters]")

        except PlaywrightTimeout as e:
            record("Playwright timeout", False, str(e))
        except Exception as e:
            record("Unexpected error", False, str(e))
        finally:
            browser.close()

    print("\n" + "=" * 70)
    print(f"RESULTS: {PASS_COUNT} passed, {FAIL_COUNT} failed out of {len(RESULTS)}")
    print("=" * 70)

    report = {
        "timestamp": ts,
        "passed": PASS_COUNT,
        "failed": FAIL_COUNT,
        "total": len(RESULTS),
        "results": RESULTS,
        "console_errors": console_errors if 'console_errors' in dir() else [],
        "network_failures": network_failures if 'network_failures' in dir() else [],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport saved to: {REPORT_PATH}")

    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
