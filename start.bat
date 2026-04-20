@echo off
title PKOS - Personal Knowledge OS
color 0A

echo.
echo  ========================================
echo    PKOS - Personal Knowledge OS
echo    Starting backend + frontend...
echo  ========================================
echo.

:: Get the directory where this batch file lives
set "PROJECT_DIR=%~dp0"

:: ── Start Backend ──────────────────────────────────────
echo [1/2] Starting Backend (FastAPI)...
cd /d "%PROJECT_DIR%backend"

:: Activate venv and start uvicorn in a new window
start "PKOS Backend" cmd /k "call venv\Scripts\activate.bat && echo. && echo  [BACKEND] Virtual environment activated && echo  [BACKEND] Starting uvicorn on http://localhost:8000 && echo. && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Give the backend a few seconds to start
echo [1/2] Backend starting on http://localhost:8000
timeout /t 10 /nobreak >nul

:: ── Start Frontend ─────────────────────────────────────
echo [2/2] Starting Frontend (Vite)...
cd /d "%PROJECT_DIR%frontend"

:: Start npm dev server in a new window
start "PKOS Frontend" cmd /k "echo. && echo  [FRONTEND] Starting Vite dev server... && echo. && npm run dev"

:: Wait for frontend to be ready
echo [2/2] Frontend starting on http://localhost:5173
timeout /t 5 /nobreak >nul

:: ── Open Browser ───────────────────────────────────────
echo.
echo  ========================================
echo    Both servers are starting!
echo.
echo    Frontend:  http://localhost:5173
echo    Backend:   http://localhost:8000
echo    API Docs:  http://localhost:8000/api/docs
echo  ========================================
echo.
echo  Opening browser...
start "" "http://localhost:5173"

echo.
echo  Press any key to close this launcher window.
echo  (The servers will keep running in their own windows)
pause >nul
