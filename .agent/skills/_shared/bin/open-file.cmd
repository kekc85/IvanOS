@echo off
:: open-file.cmd - cross-platform 'open this artifact' for native Windows shells.
:: Usage: open-file <path-or-url>  -> opens with the default app via START.
:: POSIX (mac/Linux) counterpart is the sibling 'open-file' sh script.
if "%~1"=="" (
  echo usage: open-file ^<path-or-url^>>&2
  exit /b 2
)
start "" "%~1"
exit /b %errorlevel%
