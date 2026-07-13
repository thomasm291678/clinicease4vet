@echo off
chcp 65001 >nul
echo ============================================
echo    ClinicEase 医院管理系统 - 客户端启动
echo ============================================
echo.

cd /d "%~dp0client"
pip install -r requirements.txt -q
python client.py %*

pause
