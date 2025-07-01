@echo off
chcp 65001 >nul
echo =================================================
echo     VDA5050 虚拟AGV测试系统停止脚本
echo =================================================
echo.

echo [信息] 正在停止所有Python进程...
echo.

REM 停止所有相关的Python进程
for /f "tokens=2 delims=," %%i in ('tasklist /fi "imagename eq python.exe" /fo csv ^| findstr /v "PID"') do (
    echo [信息] 正在停止进程 %%i
    taskkill /f /pid %%i >nul 2>&1
)

echo.
echo [信息] 清理临时文件...
if exist "*.pyc" del /q "*.pyc" >nul 2>&1
if exist "__pycache__" rmdir /s /q "__pycache__" >nul 2>&1
if exist "..\*.pyc" del /q "..\*.pyc" >nul 2>&1
if exist "..\__pycache__" rmdir /s /q "..\__pycache__" >nul 2>&1
if exist "..\tcp\__pycache__" rmdir /s /q "..\tcp\__pycache__" >nul 2>&1
if exist "..\vda5050\__pycache__" rmdir /s /q "..\vda5050\__pycache__" >nul 2>&1

echo.
echo =================================================
echo       VDA5050虚拟AGV测试系统已停止
echo =================================================
echo.
echo ✅ 系统组件已停止：
echo   - MQTT-TCP桥接服务器
echo   - 虚拟AGV模拟器 (VWED-0010)
echo   - MQTT测试客户端
echo   - 相关Python进程
echo.
echo 按任意键关闭此窗口...
pause >nul 