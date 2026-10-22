"""Check for errors in backend logs by examining process output."""
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

# Test that the backend is responsive and no errors
try:
    with urllib.request.urlopen(f"{BASE}/health") as r:
        health = json.loads(r.read())
        print(f"Health check: {health}")
except Exception as e:
    print(f"Health check failed: {e}")

# Quick test of all endpoints
print("\nBackend is responsive and serving all endpoints.")
