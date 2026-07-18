@echo off
call "%~dp0env.bat"
cd /d "%WEBDIR%"
echo ==========================================================
echo  SentinelleRx Web  -  http://localhost:3000
echo  (keep this window open; close it to stop the web app)
echo ==========================================================

rem Serve the production build, never `next dev`.
rem `next dev` and `next build` share the .next directory: running one while
rem the other is active wipes the compiled chunks, and the browser then gets
rem HTTP 400 for every script - a blank, dataless page. run.bat builds first,
rem so by here .next is ready; this is only a safety net for a direct launch.
if not exist "%WEBDIR%\.next\BUILD_ID" (
  echo No production build found - building now ^(~1 min^)...
  call npm run build || (echo [ERROR] build failed & pause & exit /b 1)
)

call npm run start
pause
