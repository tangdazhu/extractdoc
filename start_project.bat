@echo off
echo 🚀 启动文本转换器项目
echo ================================

REM 临时移除LibreOffice路径避免冲突
set "ORIGINAL_PATH=%PATH%"
set "PATH=%PATH:C:\Program Files\LibreOffice\program;=%"

echo 📂 进入项目目录...
cd /d "%~dp0extract_web"

echo 🔍 检查Django...
C:\Python\Python312\python.exe manage.py check
if errorlevel 1 (
    echo ❌ Django检查失败，请先运行 install_dependencies.py
    pause
    exit /b 1
)

echo 🌐 启动开发服务器...
echo 📋 访问地址: http://127.0.0.1:8000/
echo 👤 管理员账户: admin/admin
echo ⚠️  按 Ctrl+C 停止服务器
echo.

C:\Python\Python312\python.exe manage.py runserver

REM 恢复原始PATH
set "PATH=%ORIGINAL_PATH%"
pause 