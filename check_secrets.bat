@echo off
REM Windows Batch Script for Sensitive File Protection
REM Run this before any git operations

echo ======================================
echo [SECURITY] Sensitive File Protection
echo ======================================
echo.

REM Run Python script if available
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Running Python security scan...
    python tools/check_secrets.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Security scan failed!
        echo Please fix the issues before committing.
        pause
        exit /b 1
    )
) else (
    echo Python not found, using alternative checks...
    echo.
    echo Checking for sensitive files in git...
    git ls-files --error-unmatch .env gmail_credentials.json service_account.json 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [ALERT] Sensitive files are tracked by git!
        pause
        exit /b 1
    ) else (
        echo [SUCCESS] No sensitive files in git tracking
    )
)

echo.
echo [SUCCESS] Security checks passed
echo You can safely proceed with git operations
echo.
pause
