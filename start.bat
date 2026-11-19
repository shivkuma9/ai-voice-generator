@echo off
title Persona AI Voice Generator
cd /d "%~dp0"

echo =========================================================
echo       Starting Persona AI Female Voice Generator...
echo =========================================================
echo.

:: Launch browser in background after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5050"

:: Start the python FastAPI server
python app.py

pause
