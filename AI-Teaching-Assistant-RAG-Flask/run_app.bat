@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
if not exist ".env" (
  echo .env not found. Copy .env.example to .env and add your Gemini API key.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py
pause
