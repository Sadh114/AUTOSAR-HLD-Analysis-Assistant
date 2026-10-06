# Single-command launcher (PowerShell): starts the FastAPI backend in a
# new window, waits for it, then launches the Streamlit frontend here.
Set-Location -Path $PSScriptRoot

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run setup first:" -ForegroundColor Red
    Write-Host "  python -m venv venv"
    Write-Host "  venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "Starting backend (FastAPI) in a new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

Write-Host "Waiting for backend to become ready..." -ForegroundColor Cyan
Start-Sleep -Seconds 6

Write-Host "Starting frontend (Streamlit)..." -ForegroundColor Cyan
venv\Scripts\python -m streamlit run frontend\app.py
