@echo off
chcp 65001 >nul
echo =================================================
echo        VDA5050 真实AGV连接系统启动脚本
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

REM 创建日志目录
if not exist "logs" mkdir logs
echo [信息] 日志文件将保存到 logs/ 目录中

echo [步骤1/2] 启动MQTT-TCP桥接服务器...
echo [信息] 服务器将监听以下端口等待真实AGV连接：
echo         - 19205: 重定位控制
echo         - 19206: 运动控制  
echo         - 19207: 权限控制
echo         - 19210: 安全控制
echo         - 19301: 状态上报
echo.
start "VDA5050 MQTT-TCP Bridge Server" cmd /k "python mqtt_tcp_bridge_server.py"

echo [信息] 等待8秒让TCP服务器完全启动...
timeout /t 8 /nobreak >nul

echo [步骤2/2] 启动MQTT测试客户端...
start "MQTT Test Client" cmd /k "python mqtt_test_client.py"

echo.
echo =================================================
echo              系统启动完成！
echo =================================================
echo.
echo 已启动的组件：
echo   1. MQTT-TCP桥接服务器 (端口: 19205-19210, 19301)
echo   2. MQTT测试客户端 (连接到broker.emqx.io)
echo.
echo 📱 MQTTX客户端配置建议：
echo   服务器: broker.emqx.io:1883
echo   客户端ID: mqttx_real_agv_client
echo.
echo 🤖 真实AGV配置要求：
echo   AGV需要配置连接到: 127.0.0.1 (本机)
echo   使用的TCP端口如上所示
echo   AGV ID应配置为: VWED-0010
echo   制造商: SEER
echo.
echo 📡 MQTT话题结构：
echo   订阅AGV状态: /uagv/v2/SEER/VWED-0010/state
echo   订阅可视化: /uagv/v2/SEER/VWED-0010/visualization  
echo   订阅连接状态: /uagv/v2/SEER/VWED-0010/connection
echo   发送订单到: /uagv/v2/SEER/VWED-0010/order
echo   发送即时动作: /uagv/v2/SEER/VWED-0010/instantActions
echo.
echo ⚠️  注意事项：
echo   - 确保真实AGV的IP能访问到运行此脚本的计算机
echo   - 防火墙需要开放上述TCP端口
echo   - AGV配置文件应使用 robot_config/VWED-0010.yaml 的参数
echo.
echo 🧪 如需测试虚拟AGV，请运行: test\test_start_vda5050_system.bat
echo.
echo 按任意键关闭此窗口...
pause >nul 