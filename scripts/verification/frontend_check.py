"""Test frontend routing and UI structure via HTTP."""
from __future__ import annotations
import urllib.request
import json

BASE = "http://localhost:5173"

def fetch(path):
    try:
        req = urllib.request.Request(f"{BASE}{path}")
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except Exception as e:
        return None, str(e)

endpoints = ["/", "/login", "/register", "/history", "/dashboard/1"]
for ep in endpoints:
    status, content = fetch(ep)
    if status:
        has_root = 'id="root"' in content
        has_script = "src=" in content
        print(f"  {ep}: status={status}, root_div={has_root}, has_script={has_script}, len={len(content)}")
    else:
        print(f"  {ep}: ERROR - {content[:100]}")

# Check that the frontend's main JS bundle is accessible
status, content = fetch("/")
if status:
    # Find the script src
    import re
    scripts = re.findall(r'src="([^"]+)"', content)
    print(f"\n  Script sources: {scripts}")
    for s in scripts:
        if s.startswith("/"):
            full = f"{BASE}{s}"
            try:
                req = urllib.request.Request(full)
                with urllib.request.urlopen(req) as resp:
                    print(f"    {s}: {resp.status} ({len(resp.read())} bytes)")
            except Exception as e:
                print(f"    {s}: ERROR - {e}")

print("\nFrontend routing check complete.")
