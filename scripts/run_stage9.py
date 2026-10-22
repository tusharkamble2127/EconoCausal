import subprocess, sys
exe = r"D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend\.venv_py312\Scripts\python.exe"
r = subprocess.run([exe, "scripts/validate_stage9_leakage_confidence.py"], capture_output=True, text=True)
for l in (r.stdout + r.stderr).splitlines()[-12:]:
    print(l)
print("RC", r.returncode)