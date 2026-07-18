@echo off
rem ── Shared environment for SentinelleRx local run (called by other scripts) ──
rem Runtime lives in %LOCALAPPDATA% (OUTSIDE OneDrive) to avoid sync corruption.
for %%I in ("%~dp0..\..") do set "ROOT=%%~fI"

rem RUNTIME can be pre-set to keep a second checkout isolated from the first
rem (they would otherwise share one venv, database and node_modules):
rem     set "SENTINELLE_RUNTIME=%LOCALAPPDATA%\SentinelleRx-fork"  &  run.bat
if defined SENTINELLE_RUNTIME (
  set "RUNTIME=%SENTINELLE_RUNTIME%"
) else (
  set "RUNTIME=%LOCALAPPDATA%\SentinelleRx"
)
set "VENV=%RUNTIME%\venv"
set "PY=%VENV%\Scripts\python.exe"
set "WEBDIR=%RUNTIME%\frontend"
set "DBFILE=%RUNTIME%\sentinellerx.db"
set "DBURL=%DBFILE:\=/%"

rem ── Application configuration (local dev mode) ──
set "DATABASE_URL=sqlite:///%DBURL%"
set "KEYCLOAK_ENABLED=false"
set "SECRET_KEY=dev-secret-change-me-in-production"
set "PROMETHEUS_ENABLED=false"
set "PYTHONIOENCODING=utf-8"
set "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000"
