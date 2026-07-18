@echo off
call "%~dp0env.bat"
cd /d "%ROOT%\backend"
echo ==========================================================
echo  SentinelleRx API  -  http://localhost:8000/docs
echo  (keep this window open; close it to stop the API)
echo ==========================================================
"%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
