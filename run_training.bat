@echo off
title Pelatihan Model YOLOv8 (Transfer Learning)
echo ========================================================
echo Memulai Training YOLOv8 pada data/unified_dataset...
echo ========================================================
if exist ".\.venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" scripts\train_yolo.py
) else if exist "..\venv_ai\Scripts\python.exe" (
    "..\venv_ai\Scripts\python.exe" scripts\train_yolo.py
) else (
    python scripts\train_yolo.py
)
pause
