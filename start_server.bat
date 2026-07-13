@echo off
chcp 65001 >nul
echo ============================================
echo    ClinicEase 医院管理系统 - 启动脚本
echo ============================================
echo.

:: 检查 MySQL 密码环境变量
if "%MYSQL_PASSWORD%"=="" (
    echo [WARNING] 未设置 MYSQL_PASSWORD 环境变量
    echo 请在启动前设置: set MYSQL_PASSWORD=你的MySQL密码
    set /p MYSQL_PASSWORD="请输入MySQL密码: "
)

echo.
echo [1/2] 安装后端依赖...
cd /d "%~dp0backend"
pip install -r requirements.txt -q

echo [2/2] 启动后端服务器...
echo.
echo 服务器启动后, 请在另一个终端运行客户端:
echo     python client/client.py
echo.
python app.py

pause
