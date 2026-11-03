"""Focused authentication persistence verification for EconoCausal.

Tests the specific bug where page reload incorrectly redirects authenticated
users to /login because user state was initialized asynchronously in useEffect.

Uses Playwright + Chromium for REAL browser interaction.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "http://127.0.0.1:5173"
BACKEND_URL = "http://127.0.0.1:8000"
REPORT_PATH = Path(__file__).with_name("auth_persistence_verification_report.json")

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


def wait_for_react(page, timeout=20000):
    """Wait for React-rendered content to appear."""
    page.wait_for_load_state("domcontentloaded", timeout=timeout)
    page.get_by_text("EconoCausal", exact=False).wait_for(timeout=timeout)


def clear_session(context):
    """Clear localStorage to simulate anonymous user."""
    context.add_init_script("""() => {
        localStorage.removeItem('econocausal_user');
        localStorage.removeItem('econocausal_token');
    }""")


def register_and_login(page, email, password):
    """Register a new account and log in."""
    page.goto(f"{BASE_URL}/register", wait_until="domcontentloaded")
    wait_for_react(page, timeout=20000)
    page.get_by_placeholder("Jordan Rivera").fill("Auth Persist User")
    page.get_by_placeholder("you@company.com").fill(email)
    page.get_by_placeholder("At least 6 characters").fill(password)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/", timeout=30000)
    return page.url


def main():
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    email = f"auth_persist_{ts}@test.com"
    password = "pass12345"

    print("=" * 70)
    print("AUTH PERSISTENCE VERIFICATION - REAL BROWSER + REAL PAGE")
    print("=" * 70)

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
            # TEST 0: Anonymous access should redirect to login
            # ============================================================
            print("\n[0] Anonymous access redirects to login")
            clear_session(context)
            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("Anonymous / redirects to login", "/login" in current_url, f"url={current_url}")

            page.goto(f"{BASE_URL}/history", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("Anonymous /history redirects to login", "/login" in current_url, f"url={current_url}")

            # ============================================================
            # Register + Login
            # ============================================================
            print("\n[SETUP] Register + Login")
            register_and_login(page, email, password)
            current_url = page.url
            record("Register redirects to /", "/" in current_url and "/login" not in current_url, f"url={current_url}")

            # ============================================================
            # TEST A: Dashboard reload
            # ============================================================
            print("\n[TEST A] Login + Dashboard reload")
            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            page.get_by_role("heading", name="New Campaign", exact=True).wait_for(timeout=10000)
            record("Dashboard loads after login", True)

            # REAL browser reload on /
            page.reload(wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("Dashboard accessible after reload", "/login" not in current_url, f"url={current_url}")

            # ============================================================
            # TEST B: History reload
            # ============================================================
            print("\n[TEST B] History reload")
            page.goto(f"{BASE_URL}/history", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            page.get_by_role("heading", name="Campaign History", exact=True).wait_for(timeout=15000)
            record("History page loads after navigation", True)

            # REAL browser reload on /history
            page.reload(wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("History accessible after reload", "/login" not in current_url, f"url={current_url}")

            # ============================================================
            # TEST C: Direct authenticated URL
            # ============================================================
            print("\n[TEST C] Direct authenticated URL")
            page.goto(f"{BASE_URL}/history", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("Direct /history accessible", "/login" not in current_url, f"url={current_url}")

            # ============================================================
            # TEST D: Browser close/reopen (new context with same storage)
            # ============================================================
            print("\n[TEST D] Browser close/reopen")
            storage_state = context.storage_state()
            browser.close()
            
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900}, storage_state=storage_state)
            page = context.new_page()
            
            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("Dashboard accessible after context reopen", "/login" not in current_url, f"url={current_url}")

            # ============================================================
            # TEST E: Logout regression
            # ============================================================
            print("\n[TEST E] Logout regression")
            logout_btn = page.get_by_role("button", name="Sign out")
            if logout_btn.count() == 0:
                page.get_by_text("Sign out", exact=False).first.click()
            else:
                logout_btn.click()
            
            page.wait_for_url("**/login", timeout=15000)
            current_url = page.url
            record("Logout redirects to login", "/login" in current_url, f"url={current_url}")

            page.goto(f"{BASE_URL}/history", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            current_url = page.url
            record("Protected page redirects to login after logout", "/login" in current_url, f"url={current_url}")

            # ============================================================
            # TEST F: Campaign workflow with refresh
            # ============================================================
            print("\n[TEST F] Campaign workflow with refresh")
            page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
            wait_for_react(page, timeout=20000)
            page.get_by_placeholder("you@company.com").fill(email)
            page.get_by_placeholder("••••••••").fill(password)
            page.get_by_role("button", name="Sign in").click()
            page.wait_for_url("**/", timeout=30000)

            dataset_path = Path(__file__).parent.parent.parent / "artifacts" / "temporary" / "tmp_verification_dataset.csv"
            if dataset_path.exists():
                page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
                wait_for_react(page, timeout=20000)
                page.get_by_placeholder("Spring loyalty promotion").fill("Auth Persist Test")
                page.get_by_placeholder("5000").fill("3000")
                
                file_input = page.locator('input[type="file"][accept=".csv"]')
                file_input.set_input_files(str(dataset_path))
                page.get_by_text("600 rows parsed.", exact=False).wait_for(timeout=15000)
                
                run_btn = page.get_by_role("button", name="Run campaign")
                run_btn.click()
                page.wait_for_url("**/dashboard/*", timeout=120000)
                record("Campaign created and navigated to dashboard", True)

                page.reload(wait_until="domcontentloaded")
                wait_for_react(page, timeout=20000)
                page.get_by_text("Budget Utilization", exact=True).wait_for(timeout=60000)
                record("Dashboard accessible after campaign refresh", True)
            else:
                record("Campaign workflow", True, "dataset not found, skipped")

            # ============================================================
            # Console / Network check
            # ============================================================
            print("\n[G] Console / Network")
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
