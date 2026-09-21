@echo off
REM run_tutor.bat - double-click launcher for Hangul Tutor (offline default).
REM Pass extra args through, e.g.:  run_tutor.bat --lesson 3
REM For the optional Ollama enrichments:  run_tutor.bat --use-llm
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py hangul_cli.py %*
) else (
    python hangul_cli.py %*
)
echo.
pause
