@echo off
setlocal

echo Starting text converter project
echo ================================

REM Temporarily remove LibreOffice path to avoid conflicts
set "ORIGINAL_PATH=%PATH%"
set "PATH=%PATH:C:\Program Files\LibreOffice\program;=%"

echo Changing to project directory...
cd /d "%~dp0extract_web"
if errorlevel 1 goto restore

echo Checking Django...
python manage.py check
if errorlevel 1 (
    echo [ERROR] Django check failed. Run install_dependencies.py first.
    goto restore
)

echo Starting development server...
echo URL: http://127.0.0.1:8000/
echo Admin credentials: admin/admin
echo Press Ctrl+C to stop the server.
echo.

python manage.py runserver 8080

:restore
set "PATH=%ORIGINAL_PATH%"
endlocal
pause