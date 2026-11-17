@echo off
title Tactical AI Surveillance Dashboard
echo ========================================================
echo Membuka Tactical AI Surveillance Dashboard...
echo ========================================================
if exist ".\.venv\Scripts\streamlit.exe" (
    ".\.venv\Scripts\streamlit.exe" run app.py
) else if exist "..\venv_ai\Scripts\streamlit.exe" (
    "..\venv_ai\Scripts\streamlit.exe" run app.py
) else (
    streamlit run app.py
)
pause
