@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo AI Teaching Assistant - Flask Setup
echo ============================================
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.12 from https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Python 3.12 was not found. If only Python 3.14 is installed, try manual setup as described in README.md.
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error
if not exist ".env" copy ".env.example" ".env" >nul
echo Setup complete. Add your Gemini API key to .env if you have not done so.
pause
exit /b 0
:error
echo Setup failed. Read README.md and check the installation error.
pause
exit /b 1
