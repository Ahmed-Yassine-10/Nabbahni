@echo off
echo Stopping SentinelleRx...

rem Close the launcher windows first.
taskkill /FI "WINDOWTITLE eq SentinelleRx API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq SentinelleRx Web*" /T /F >nul 2>&1

rem Then kill whatever still holds the ports. Window-title matching alone
rem misses servers started outside run.bat, and a leftover process on :3000
rem will corrupt the next build's .next directory.
for %%P in (3000 8000) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:"LISTENING" ^| findstr ":%%P "') do (
    taskkill /PID %%A /F >nul 2>&1
  )
)

echo Done.
rem `ping`, not `timeout`: timeout aborts with "Input redirection is not
rem supported" when this script is called with its streams redirected, which
rem is exactly how run.bat invokes it.
ping -n 3 127.0.0.1 >nul 2>&1
