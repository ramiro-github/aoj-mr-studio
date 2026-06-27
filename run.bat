@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m aoj_mr_studio
) else (
    python -m aoj_mr_studio
)
