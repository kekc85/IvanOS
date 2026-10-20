@echo off
REM ============================================================================
REM IvanOS python3 shim (Windows). python.org ships only `python`, not `python3`,
REM so skills that call `python3 X.py` would break. Order: `py -3` first (Python
REM Launcher is installed by python.org by default and is never the Microsoft
REM Store stub), then real `python` filtered against WindowsApps (the Store stub
REM lives there and fakes success) and against this shim's own directory (the
REM shim dir is PREPENDED to PATH by install.ps1, so `where python` finds the
REM shim itself first - skipping %~dp0 prevents a self-loop). Args pass through
REM 1:1; bare `exit /b` keeps the interpreter's real exit code (exit /b
REM %ERRORLEVEL% inside a block expands BEFORE the run = stale code).
REM ============================================================================
setlocal EnableExtensions
py -3 -c "import sys" >nul 2>&1
if %ERRORLEVEL%==0 (
  py -3 %*
  exit /b
)
for /f "delims=" %%P in ('where python 2^>nul') do (
  if /i not "%%~dpP"=="%~dp0" (
    echo %%P | find /i "WindowsApps" >nul || (
      "%%P" %*
      exit /b
    )
  )
)
echo [IvanOS] Python 3 not found. Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH". 1>&2
exit /b 2
