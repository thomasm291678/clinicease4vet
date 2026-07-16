@echo off
chcp 65001 >nul
title PetCare 宠物医院管理系统

echo.
echo ======================================================
echo   PetCare 宠物医院管理系统 v2.1
echo ======================================================
echo.

cd /d "%~dp0"

::: 1. 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

::: 2. 安装依赖
echo [1/3] 检查 Python 依赖库...
pip install -r requirements.txt -q 2>nul
if %errorlevel% neq 0 (
    echo [警告] pip 安装可能失败，尝试继续...
)

::: 3. 启动服务
echo [2/3] 正在初始化数据库 (SQLite)...
echo [3/3] 启动服务器...
echo.
echo   >>> 浏览器将自动打开 http://localhost:5000
echo   >>> 如未自动打开，请手动访问: http://localhost:5000
echo.

start "" http://localhost:5000

python app.py

pause
