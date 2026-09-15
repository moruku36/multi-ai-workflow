@echo off
cd /d "%~dp0"
if exist "venv\Scripts\activate.bat" (
    call .\venv\Scripts\activate.bat
)
set OLLAMA_BASE_URL=http://127.0.0.1:11434
open-webui serve