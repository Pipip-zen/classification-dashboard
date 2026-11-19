@echo off
title Tactical AI Reconnaissance GCS
echo =======================================================
echo   MEMULAI TACTICAL AI GROUND CONTROL STATION (GCS)
echo =======================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)
pause
