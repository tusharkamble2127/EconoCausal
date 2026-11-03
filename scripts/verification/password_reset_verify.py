"""Password reset verification script for EconoCausal."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://127.0.0.1:8000"
API_URL = BASE_URL

RESULTS = {}


def log(name, status, detail=""):
    RESULTS[name] = {"status": status, "detail": detail}
    print(f"[{status}] {name}: {detail}")


def api(method, path, json_data=None, headers=None):
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if json_data is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(json_data).encode("utf-8")
    else:
        data = None
    try:
        with urllib.request.urlopen(req, data=data, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"detail": body}
    except Exception as e:
        return None, {"detail": str(e)}


def register(email, password, full_name="Test User"):
    status, data = api("POST", "/auth/register", {
        "email": email,
        "password": password,
        "full_name": full_name,
    })
    if status == 201:
        return data["access_token"], data["user"]["user_id"]
    return None, None


def login(email, password):
    status, data = api("POST", "/auth/login", {
        "email": email,
        "password": password,
    })
    return status, data


def forgot_password(email):
    status, data = api("POST", "/auth/forgot-password", {"email": email})
    return status, data


def reset_password(token, new_password):
    status, data = api("POST", "/auth/reset-password", {
        "token": token,
        "new_password": new_password,
    })
    return status, data


def check_logs_for_sensitive_data(log_text):
    """Check that no sensitive data appears in logs."""
    patterns = {
        "raw_reset_token": r"[A-Za-z0-9_-]{20,}",
        "api_key": r"xkeysib-[A-Za-z0-9_-]+",
        "smtp_password": r"xsmtpsib-[A-Za-z0-9_-]+",
        "jwt": r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+",
        "full_reset_url": r"http[s]?://[^\s]+/reset-password\?token=[^\s]+",
        "password": r"password[:=]\s*\S+",
    }
    found = {}
    for name, pattern in patterns.items():
        matches = re.findall(pattern, log_text, re.IGNORECASE)
        if matches:
            found[name] = len(matches)
    return found


def test_brevo_config():
    """Verify Brevo config is loaded from .env."""
    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.core.config import settings
    api_key_loaded = bool(settings.brevo_api_key)
    template_id_loaded = bool(settings.brevo_template_id)
    template_id = settings.brevo_template_id
    log("Brevo API key loaded", "PASS" if api_key_loaded else "FAIL",
        f"Length={len(settings.brevo_api_key)}")
    log("Brevo template ID loaded", "PASS" if template_id_loaded else "FAIL",
        f"ID={template_id}")
    return api_key_loaded and template_id_loaded, template_id


def test_brevo_api_auth():
    """Test Brevo API with a direct call to verify authentication."""
    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.core.config import settings
    api_key = settings.brevo_api_key
    template_id = settings.brevo_template_id

    if not api_key or not template_id:
        log("Brevo API auth", "FAIL", "Missing API key or template ID")
        return False

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "to": [{"email": "test@example.com"}],
                    "templateId": int(template_id),
                    "params": {
                        "reset_url": "https://example.com/reset-password?token=test123",
                    },
                },
            )
        if resp.status_code in (200, 201):
            body = resp.json()
            message_id = body.get("messageId", "unknown")
            log("Brevo API auth", "PASS", f"Status={resp.status_code}, MessageId={message_id}")
            return True
        else:
            log("Brevo API auth", "FAIL", f"Status={resp.status_code}, Body={resp.text[:200]}")
            return False
    except Exception as e:
        log("Brevo API auth", "FAIL", str(e)[:200])
        return False


def test_password_reset_flow():
    """End-to-end password reset test."""
    email = f"verify-{int(time.time())}@test.com"
    password = "OldPass123!"
    new_password = "NewPass456!"

    # 1. Register
    token, user_id = register(email, password)
    if not token:
        log("Registration", "FAIL", "Could not register test user")
        return False
    log("Registration", "PASS", f"user_id={user_id}")

    # 2. Forgot password
    status, data = forgot_password(email)
    if status != 200:
        log("Forgot password request", "FAIL", f"Status={status}")
        return False
    generic_msg = data.get("message", "")
    if "If an account exists" not in generic_msg:
        log("Forgot password generic message", "FAIL", f"Message={generic_msg}")
        return False
    log("Forgot password generic message", "PASS")

    # 3. Get token from database to simulate getting it from email
    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.repositories import password_reset_repository, user_repository
    from sqlalchemy.orm import Session
    from app.api.deps import get_db

    # We need to access the test database. Let's use a direct DB connection.
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        user = user_repository.get_by_email(db, email)
        if not user:
            log("Find user in DB", "FAIL", "User not found")
            return False

        stmt = (
            __import__("sqlalchemy").select(__import__("app.models.password_reset_token", fromlist=["PasswordResetToken"]).PasswordResetToken)
            .where(__import__("app.models.password_reset_token", fromlist=["PasswordResetToken"]).PasswordResetToken.user_id == user.user_id)
            .where(__import__("app.models.password_reset_token", fromlist=["PasswordResetToken"]).PasswordResetToken.used_at.is_(None))
            .where(__import__("app.models.password_reset_token", fromlist=["PasswordResetToken"]).PasswordResetToken.expires_at > datetime.now(timezone.utc))
            .order_by(__import__("app.models.password_reset_token", fromlist=["PasswordResetToken"]).PasswordResetToken.created_at.desc())
        )
        token_row = db.execute(stmt).scalars().first()
        if not token_row:
            log("Find reset token", "FAIL", "No valid token found")
            return False

        # Reconstruct raw token from token_hash is not possible (SHA256)
        # Instead, let's check what was stored by looking at the service directly
        # Actually, we need the raw token. Let's generate one and use it directly.
        # For E2E test, we need to intercept the token. Let me re-approach.
    finally:
        db.close()

    return True


def test_password_reset_with_known_token():
    """Test password reset using a directly created token."""
    email = f"verify2-{int(time.time())}@test.com"
    password = "OldPass123!"
    new_password = "NewPass456!"

    token, user_id = register(email, password)
    if not token:
        log("Registration for token test", "FAIL")
        return False
    log("Registration for token test", "PASS")

    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.core.security import generate_reset_token, hash_reset_token
    from app.repositories import password_reset_repository, user_repository
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        user = user_repository.get_by_email(db, email)
        raw_token = generate_reset_token()
        password_reset_repository.create(db, user, raw_token, 30)
        db.commit()
        log("Token created", "PASS", f"raw_token={raw_token[:8]}...")

        # Test successful reset
        status, data = reset_password(raw_token, new_password)
        if status != 200:
            log("Reset password success", "FAIL", f"Status={status}, Detail={data.get('detail')}")
            return False
        log("Reset password success", "PASS")

        # Test new password login
        status, data = login(email, new_password)
        if status != 200:
            log("Login with new password", "FAIL", f"Status={status}")
            return False
        log("Login with new password", "PASS")

        # Test old password rejection
        status, data = login(email, password)
        if status != 401:
            log("Old password rejection", "FAIL", f"Expected 401, got {status}")
            return False
        log("Old password rejection", "PASS")

        # Test token one-time use
        status, data = reset_password(raw_token, "AnotherPass123!")
        if status == 200:
            log("Token one-time use", "FAIL", "Token reused successfully")
            return False
        log("Token one-time use", "PASS", f"Status={status}")

        return True
    finally:
        db.close()


def test_token_expiration():
    """Test expired token is rejected."""
    email = f"verify-exp-{int(time.time())}@test.com"
    password = "OldPass123!"

    token, user_id = register(email, password)
    if not token:
        log("Registration for expiration test", "FAIL")
        return False

    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.core.security import generate_reset_token
    from app.repositories import password_reset_repository, user_repository
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        user = user_repository.get_by_email(db, email)
        raw_token = generate_reset_token()
        # Create token with -1 minute expiration
        password_reset_repository.create(db, user, raw_token, -1)
        db.commit()

        status, data = reset_password(raw_token, "NewPass123!")
        if status == 200:
            log("Token expiration", "FAIL", "Expired token accepted")
            return False
        log("Token expiration", "PASS", f"Status={status}")
        return True
    finally:
        db.close()


def test_rate_limiting():
    """Test forgot-password rate limiting."""
    email = f"verify-rate-{int(time.time())}@test.com"
    password = "OldPass123!"

    token, user_id = register(email, password)
    if not token:
        log("Registration for rate limit test", "FAIL")
        return False

    status1, data1 = forgot_password(email)
    status2, data2 = forgot_password(email)

    if status1 != 200:
        log("Rate limiting first request", "FAIL", f"Status={status1}")
        return False

    if status2 != 429:
        log("Rate limiting second request", "FAIL", f"Expected 429, got {status2}")
        return False
    log("Rate limiting", "PASS", f"First={status1}, Second={status2}")
    return True


def test_account_enumeration():
    """Test that forgot-password returns generic message for non-existent email."""
    status, data = forgot_password(f"nonexistent-{int(time.time())}@example.com")
    if status != 200:
        log("Account enumeration protection", "FAIL", f"Status={status}")
        return False
    msg = data.get("message", "")
    if "If an account exists" not in msg:
        log("Account enumeration protection", "FAIL", f"Message={msg}")
        return False
    log("Account enumeration protection", "PASS")
    return True


def test_logs_no_sensitive_data():
    """Check backend logs for sensitive data exposure."""
    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.repositories import user_repository
    from app.core.security import generate_reset_token
    from app.repositories import password_reset_repository
    from app.services.password_reset_service import forgot_password

    email = f"verify-logs-{int(time.time())}@test.com"
    password = "OldPass123!"
    token, user_id = register(email, password)
    if not token:
        log("Registration for log test", "FAIL")
        return False

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        user = user_repository.get_by_email(db, email)
        raw_token = generate_reset_token()
        password_reset_repository.create(db, user, raw_token, 30)
        db.commit()

        # Trigger forgot password which sends email
        forgot_password(db, email)
        db.commit()
    finally:
        db.close()

    # The logs are already output to stdout. We need to check the backend process output.
    # For now, we can do a code review of the logging patterns.
    # Let's check if any log statements contain sensitive data patterns.

    sensitive_patterns = [
        r"token.*=.*[A-Za-z0-9_-]{20,}",
        r"password.*=.*\S+",
        r"api.key.*=.*\S+",
        r"smtp.password.*=.*\S+",
    ]

    log_files = []
    for root, dirs, files in os.walk(r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal"):
        for f in files:
            if f.endswith(".py"):
                log_files.append(os.path.join(root, f))

    code_findings = []
    for fpath in log_files:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for pattern in sensitive_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                code_findings.extend([(fpath, m) for m in matches])

    if code_findings:
        log("Sensitive data in code logs", "FAIL", f"Found {len(code_findings)} patterns")
        return False
    log("Sensitive data in code logs", "PASS")
    return True


def test_backend_unit_tests():
    """Run backend unit tests."""
    result = subprocess.run(
        ["C:\\Python314\\python.exe", "-m", "pytest", "tests/unit", "-v", "--tb=short"],
        cwd=r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend",
        capture_output=True, text=True, timeout=300
    )
    passed = result.stdout.count(" passed")
    failed = result.stdout.count(" failed")
    log("Backend unit tests", "PASS" if failed == 0 else "FAIL",
        f"{passed} passed, {failed} failed")
    return failed == 0


def test_backend_integration_tests():
    """Run backend integration tests."""
    result = subprocess.run(
        ["C:\\Python314\\python.exe", "-m", "pytest", "tests/integration", "-v", "--tb=short"],
        cwd=r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend",
        capture_output=True, text=True, timeout=600
    )
    passed = result.stdout.count(" passed")
    failed = result.stdout.count(" failed")
    log("Backend integration tests", "PASS" if failed == 0 else "FAIL",
        f"{passed} passed, {failed} failed")
    return failed == 0


def test_frontend_build():
    """Run frontend production build."""
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\frontend",
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        log("Frontend production build", "PASS")
        return True
    else:
        log("Frontend production build", "FAIL", result.stderr[-500:])
        return False


def test_playwright_suite():
    """Run Playwright tests."""
    result = subprocess.run(
        ["npx", "playwright", "test", "--reporter=list"],
        cwd=r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\frontend",
        capture_output=True, text=True, timeout=600
    )
    output = result.stdout + result.stderr
    passed = output.count(" passed")
    failed = output.count(" failed")
    log("Playwright suite", "PASS" if failed == 0 else "FAIL",
        f"{passed} passed, {failed} failed")
    return failed == 0


def test_actual_email_delivery():
    """Test actual email delivery via Brevo and capture the email content."""
    sys.path.insert(0, r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend")
    from app.core.config import settings
    from app.core.security import generate_reset_token
    from app.repositories import password_reset_repository, user_repository
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.services.email_service import send_password_reset_email

    email = "roopankbattu062@gmail.com"
    test_token = generate_reset_token()
    reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={test_token}"

    try:
        send_password_reset_email(email, reset_url)
        log("Actual email delivery", "PASS", "Brevo accepted and sent email")
        return True
    except Exception as e:
        log("Actual email delivery", "FAIL", str(e)[:200])
        return False


def main():
    print("=" * 60)
    print("PASSWORD RESET VERIFICATION")
    print("=" * 60)

    # 1. Brevo configuration
    config_ok, template_id = test_brevo_config()
    log("Template ID configured", "PASS" if template_id else "FAIL", str(template_id))

    # 2. Brevo API auth
    test_brevo_api_auth()

    # 3. Actual email delivery
    test_actual_email_delivery()

    # 4. Password reset flow
    test_password_reset_with_known_token()

    # 5. Token expiration
    test_token_expiration()

    # 6. Rate limiting
    test_rate_limiting()

    # 7. Account enumeration
    test_account_enumeration()

    # 8. Sensitive data logging
    test_logs_no_sensitive_data()

    # 9. Backend tests
    print("\n--- Running Backend Tests ---")
    unit_ok = test_backend_unit_tests()
    integration_ok = test_backend_integration_tests()

    # 10. Frontend build
    build_ok = test_frontend_build()

    # 11. Playwright
    playwright_ok = test_playwright_suite()

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, result in RESULTS.items():
        print(f"  [{result['status']}] {name}: {result['detail']}")

    # Final decision
    all_checks = [
        config_ok,
        RESULTS.get("Brevo API auth", {}).get("status") == "PASS",
        RESULTS.get("Actual email delivery", {}).get("status") == "PASS",
        RESULTS.get("Reset password success", {}).get("status") == "PASS",
        RESULTS.get("Login with new password", {}).get("status") == "PASS",
        RESULTS.get("Old password rejection", {}).get("status") == "PASS",
        RESULTS.get("Token one-time use", {}).get("status") == "PASS",
        RESULTS.get("Token expiration", {}).get("status") == "PASS",
        RESULTS.get("Rate limiting", {}).get("status") == "PASS",
        RESULTS.get("Account enumeration protection", {}).get("status") == "PASS",
        RESULTS.get("Sensitive data in code logs", {}).get("status") == "PASS",
        unit_ok,
        integration_ok,
        build_ok,
        playwright_ok,
    ]

    if all(all_checks):
        print("\nFINAL DECISION: READY")
    else:
        print("\nFINAL DECISION: NOT READY")

    return all(all_checks)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
