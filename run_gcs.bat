@echo off
title Tactical AI Reconnaissance GCS
echo =======================================================
echo   MEMULAI TACTICAL AI GROUND CONTROL STATION (GCS)
echo =======================================================
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python run.py
pause
