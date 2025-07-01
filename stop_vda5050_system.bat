@echo off
chcp 65001 >nul
echo =================================================
echo       VDA5050 真实AGV连接系统停止脚本
echo =================================================
echo.

echo [信息] 正在停止MQTT-TCP桥接服务器和相关进程...
echo.

REM 停止MQTT-TCP桥接服务器
for /f "tokens=2 delims=," %%i in ('tasklist /fi "windowtitle eq VDA5050 MQTT-TCP Bridge Server*" /fo csv ^| findstr /v "PID"') do (
    if not "%%i"=="" (
        echo [信息] 正在停止MQTT-TCP桥接服务器 %%i
        taskkill /f /pid %%i >nul 2>&1
    )
)

REM 停止MQTT测试客户端
for /f "tokens=2 delims=," %%i in ('tasklist /fi "windowtitle eq MQTT Test Client*" /fo csv ^| findstr /v "PID"') do (
    if not "%%i"=="" (
        echo [信息] 正在停止MQTT测试客户端 %%i
        taskkill /f /pid %%i >nul 2>&1
    )
)

REM 停止所有相关的Python进程（谨慎操作）
echo [信息] 正在检查Python进程...
for /f "tokens=1,2" %%a in ('tasklist /fi "imagename eq python.exe" /fo table /nh') do (
    for /f "tokens=*" %%c in ('wmic process where "ProcessId=%%b" get CommandLine /value ^| findstr "mqtt_tcp_bridge_server"') do (
        echo [信息] 正在停止相关Python进程 %%b
        taskkill /f /pid %%b >nul 2>&1
    )
)

echo.
echo [信息] 清理临时文件...
if exist "*.pyc" del /q "*.pyc" >nul 2>&1
if exist "__pycache__" rmdir /s /q "__pycache__" >nul 2>&1
if exist "tcp\__pycache__" rmdir /s /q "tcp\__pycache__" >nul 2>&1
if exist "vda5050\__pycache__" rmdir /s /q "vda5050\__pycache__" >nul 2>&1

echo.
echo =================================================
echo         VDA5050真实AGV连接系统已停止
echo =================================================
echo.
echo ✅ 系统组件已停止：
echo   - MQTT-TCP桥接服务器
echo   - MQTT测试客户端
echo   - 相关Python进程
echo.
echo ⚠️  注意：
echo   - 真实AGV的TCP连接会自动断开
echo   - 如需重新连接，请运行 start_vda5050_system.bat
echo.
echo 按任意键关闭此窗口...
pause >nul 