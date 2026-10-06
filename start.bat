@echo off
REM Single-command launcher: starts the FastAPI backend in a new window,
REM waits for it to come up, then launches the Streamlit frontend here.
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Run setup first:
    echo   python -m venv venv
    echo   venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo Starting backend (FastAPI) in a new window...
start "AUTOSAR-HLD-Backend" cmd /k "venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

echo Waiting for backend to become ready...
timeout /t 6 /nobreak >nul

echo Starting frontend (Streamlit)...
venv\Scripts\python -m streamlit run frontend\app.py
