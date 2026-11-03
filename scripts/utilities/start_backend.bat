@echo off
cd /d "D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\backend"
call .venv_py312\Scripts\activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file "D:\roopank\internship\infotact\EconoCausal_Fixed\econocausal\.env"
