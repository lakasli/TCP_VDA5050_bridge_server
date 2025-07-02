@echo off
chcp 65001 >nul
echo =================================================
echo     VDA5050 虚拟AGV测试系统启动脚本
echo =================================================
echo.

REM 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH环境变量中
    pause
    exit /b 1
)

echo [信息] Python环境检查通过
echo.

REM 创建日志目录（在父目录）
if not exist "..\logs" mkdir ..\logs
echo [信息] 日志文件将保存到 ../logs/ 目录中

echo [步骤1/2] 启动MQTT-TCP桥接服务器...
start "VDA5050 MQTT-TCP Bridge Server" cmd /k "cd /d %~dp0..\ && python mqtt_tcp_bridge_server.py"

echo [信息] 等待5秒让TCP服务器完全启动...
timeout /t 5 /nobreak >nul

echo [步骤2/2] 启动AGV模拟器...
start "AGV Simulator" cmd /k "cd /d %~dp0 && python agv_simulator.py"

echo [信息] 等待3秒让AGV模拟器连接...
timeout /t 3 /nobreak >nul


echo.
echo =================================================
echo              系统启动完成！
echo =================================================
echo.
echo 已启动的组件：
echo   1. MQTT-TCP桥接服务器 (端口: 19205-19210, 19301)
echo   2. 虚拟AGV模拟器 (模拟VWED-0010)
echo.
echo [MQTTX] 客户端配置建议：
echo   服务器: 172.31.232.152:1883
echo   客户端ID: mqttx_virtual_test_client
echo.
echo [订阅] 以下Topic接收AGV状态：
echo   /uagv/v2/SEER/VWED-0010/state
echo   /uagv/v2/SEER/VWED-0010/visualization
echo   /uagv/v2/SEER/VWED-0010/connection
echo.
echo [发送] 指令到以下Topic：
echo   /uagv/v2/SEER/VWED-0010/order
echo   /uagv/v2/SEER/VWED-0010/instantActions
echo.
echo 按任意键关闭此窗口...
pause >nul 