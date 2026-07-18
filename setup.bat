@echo off
setlocal
call "%~dp0scripts\win\env.bat"

echo ================================================================
echo   SentinelleRx - One-time Setup  (SQLite, no Docker required)
echo ================================================================
echo   Runtime folder: %RUNTIME%
echo.
echo   This takes 8-12 minutes the first time. Model training is
echo   skipped: trained champions ship with the repository.
echo   Later runs skip everything already done.
echo.

where python >nul 2>&1 || (echo [ERROR] Python not found on PATH. Install Python 3.12+ from python.org & pause & exit /b 1)
where node   >nul 2>&1 || (echo [ERROR] Node.js not found on PATH. Install Node 20+ from nodejs.org & pause & exit /b 1)

if not exist "%RUNTIME%" mkdir "%RUNTIME%"

echo [1/7] Creating Python virtual environment...
if not exist "%PY%" python -m venv "%VENV%" || (echo [ERROR] venv creation failed & pause & exit /b 1)

echo [2/7] Installing Python packages (a few minutes on first run)...
"%PY%" -m pip install --upgrade pip >nul
"%PY%" -m pip install -r "%ROOT%\requirements-local.txt" || (echo [ERROR] pip install failed & pause & exit /b 1)

echo [3/7] Creating database schema...
pushd "%ROOT%\backend"
"%PY%" -c "import app.models; from app.core.database import Base, engine; Base.metadata.create_all(engine); print('  schema ready')" || (popd & pause & exit /b 1)
popd

rem NOTE: use an explicit marker file, NOT the .db file - step 3 above creates
rem the .db, so checking for it would wrongly skip seeding on a fresh install.
if exist "%RUNTIME%\.seeded" (
  echo [4/7] Data already seeded - skipping.
) else (
  echo [4/7] Seeding synthetic Tunisian dataset ^(~1 min^)...
  pushd "%ROOT%\data-generator"
  "%PY%" -m generator.seed --seed 42 --days 540 --pharmacies 60 || (popd & echo [ERROR] seeding failed & pause & exit /b 1)
  popd
  echo seeded > "%RUNTIME%\.seeded"
)

rem Trained champions ship with the repository, so this normally skips. Delete
rem ml\artifacts\ to force a full retrain on your own data.
if exist "%ROOT%\ml\artifacts\shortage.joblib" (
  echo [5/7] Trained models found - skipping training.
) else (
  echo [5/7] Training demand + shortage models ^(10-20 min - go get a coffee^)...
  pushd "%ROOT%\ml"
  "%PY%" -m ml.train_all || (popd & echo [ERROR] training failed & pause & exit /b 1)
  popd
)

echo [6/7] Scoring predictions, recommendations, alerts...
pushd "%ROOT%\ml"
"%PY%" -m ml.score || (popd & echo [ERROR] scoring failed & pause & exit /b 1)
popd

echo [7/7] Preparing frontend ^(installed outside OneDrive for reliability^)...
robocopy "%ROOT%\frontend" "%WEBDIR%" /E /XD node_modules .next /XF .env.local /NFL /NDL /NJH /NJS /NP >nul
> "%WEBDIR%\.env.local" echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
pushd "%WEBDIR%"
call npm install || (popd & echo [ERROR] npm install failed & pause & exit /b 1)
echo       Building the web app...
call npm run build || (popd & echo [ERROR] web build failed & pause & exit /b 1)
popd

echo.
echo ================================================================
echo   Setup complete!  Double-click  run.bat  to launch the app.
echo ================================================================
endlocal
