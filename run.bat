@echo off
setlocal
call "%~dp0scripts\win\env.bat"

echo ================================================================
echo   SentinelleRx - La meteo des medicaments de Tunisie
echo ================================================================

rem ── Auto-run setup on first launch (or if runtime is incomplete) ──
if not exist "%PY%"               goto :needsetup
if not exist "%DBFILE%"           goto :needsetup
if not exist "%WEBDIR%\node_modules" goto :needsetup
goto :launch

:needsetup
echo First run detected - running one-time setup...
echo.
call "%~dp0setup.bat"
if errorlevel 1 (echo Setup did not complete. & pause & exit /b 1)

:launch
rem Stop anything still listening from a previous run. Two servers sharing the
rem .next directory corrupt each other's chunks and the app loads blank.
echo Stopping any previous SentinelleRx processes...
call "%~dp0stop.bat" >nul 2>&1

echo Syncing frontend source...
robocopy "%ROOT%\frontend" "%WEBDIR%" /E /XD node_modules .next /XF .env.local /NFL /NDL /NJH /NJS /NP >nul
> "%WEBDIR%\.env.local" echo NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

rem Build here, in ONE place, while nothing else is serving. Doing it inside
rem the web window instead would race the dev/prod server against the compiler.
echo Building the web app (this takes ~1 min)...
pushd "%WEBDIR%"
call npm run build || (popd & echo [ERROR] Web build failed. & pause & exit /b 1)
popd

echo Launching API window  (http://localhost:8000/docs)...
start "SentinelleRx API" cmd /k call "%~dp0scripts\win\api.bat"

echo Launching Web window  (http://localhost:3000)...
start "SentinelleRx Web" cmd /k call "%~dp0scripts\win\web.bat"

echo Waiting for the web server to start...
timeout /t 12 /nobreak >nul
start "" http://localhost:3000

echo.
echo ================================================================
echo   SentinelleRx is starting in two new windows:
echo     Web  ^> http://localhost:3000   (opens automatically)
echo     API  ^> http://localhost:8000/docs
echo.
echo   Demo login: pick a role from the dropdown (top-right).
echo   To stop: close those two windows, or run  stop.bat
echo ================================================================
echo.
pause
endlocal
