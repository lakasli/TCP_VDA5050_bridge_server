#!/bin/bash

# 设置UTF-8编码
export LANG=zh_CN.UTF-8

echo "================================================="
echo "     VDA5050 虚拟AGV测试系统启动脚本"
echo "================================================="
echo

# 检查Python是否可用
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[错误] 未找到Python，请确保Python已安装并添加到PATH环境变量中"
    exit 1
fi

# 优先使用python3，如果没有则使用python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "[信息] Python环境检查通过 (使用: $PYTHON_CMD)"
echo

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# 创建日志目录（在父目录）
mkdir -p "$PARENT_DIR/logs"
echo "[信息] 日志文件将保存到 ../logs/ 目录中"

echo "[步骤1/3] 启动MQTT-TCP桥接服务器..."

# 检查是否有gnome-terminal或xterm可用
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --title="VDA5050 MQTT-TCP Bridge Server" -- bash -c "cd '$PARENT_DIR' && $PYTHON_CMD mqtt_tcp_bridge_server.py; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -title "VDA5050 MQTT-TCP Bridge Server" -e "cd '$PARENT_DIR' && $PYTHON_CMD mqtt_tcp_bridge_server.py; exec bash" &
elif command -v konsole &> /dev/null; then
    konsole --title "VDA5050 MQTT-TCP Bridge Server" -e bash -c "cd '$PARENT_DIR' && $PYTHON_CMD mqtt_tcp_bridge_server.py; exec bash" &
else
    echo "[警告] 未找到支持的终端模拟器，尝试在后台启动..."
    cd "$PARENT_DIR"
    nohup $PYTHON_CMD mqtt_tcp_bridge_server.py > logs/bridge_server.log 2>&1 &
    cd "$SCRIPT_DIR"
fi

echo "[信息] 等待5秒让TCP服务器完全启动..."
sleep 5

echo "[步骤2/3] 启动AGV模拟器..."

if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --title="AGV Simulator" -- bash -c "cd '$SCRIPT_DIR' && $PYTHON_CMD agv_simulator.py; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -title "AGV Simulator" -e "cd '$SCRIPT_DIR' && $PYTHON_CMD agv_simulator.py; exec bash" &
elif command -v konsole &> /dev/null; then
    konsole --title "AGV Simulator" -e bash -c "cd '$SCRIPT_DIR' && $PYTHON_CMD agv_simulator.py; exec bash" &
else
    echo "[警告] 未找到支持的终端模拟器，尝试在后台启动..."
    cd "$SCRIPT_DIR"
    nohup $PYTHON_CMD agv_simulator.py > logs/agv_simulator.log 2>&1 &
fi

echo "[信息] 等待3秒让AGV模拟器连接..."
sleep 3

echo "[步骤3/4] 启动MQTT测试客户端..."

if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --title="MQTT Test Client" -- bash -c "cd '$PARENT_DIR' && $PYTHON_CMD mqtt_test_client.py; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -title "MQTT Test Client" -e "cd '$PARENT_DIR' && $PYTHON_CMD mqtt_test_client.py; exec bash" &
elif command -v konsole &> /dev/null; then
    konsole --title "MQTT Test Client" -e bash -c "cd '$PARENT_DIR' && $PYTHON_CMD mqtt_test_client.py; exec bash" &
else
    echo "[警告] 未找到支持的终端模拟器，尝试在后台启动..."
    cd "$PARENT_DIR"
    nohup $PYTHON_CMD mqtt_test_client.py > logs/mqtt_client.log 2>&1 &
    cd "$SCRIPT_DIR"
fi

echo "[信息] 等待2秒让MQTT客户端连接..."
sleep 2

echo "[步骤4/4] 启动MQTT状态监控器..."

if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --title="MQTT State Monitor" -- bash -c "cd '$SCRIPT_DIR' && $PYTHON_CMD mqtt_state_monitor.py; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -title "MQTT State Monitor" -e "cd '$SCRIPT_DIR' && $PYTHON_CMD mqtt_state_monitor.py; exec bash" &
elif command -v konsole &> /dev/null; then
    konsole --title "MQTT State Monitor" -e bash -c "cd '$SCRIPT_DIR' && $PYTHON_CMD mqtt_state_monitor.py; exec bash" &
else
    echo "[警告] 未找到支持的终端模拟器，尝试在后台启动..."
    cd "$SCRIPT_DIR"
    nohup $PYTHON_CMD mqtt_state_monitor.py > logs/mqtt_state_monitor.log 2>&1 &
fi

echo
echo "================================================="
echo "              系统启动完成！"
echo "================================================="
echo
echo "已启动的组件："
echo "  1. MQTT-TCP桥接服务器 (端口: 19205-19210, 19301)"
echo "  2. 虚拟AGV模拟器 (模拟VWED-0010)"
echo "  3. MQTT测试客户端 (连接到broker.emqx.io:1883)"
echo "  4. MQTT状态监控器 (监听AGV状态消息)"
echo
echo "📱 MQTTX客户端配置建议："
echo "  服务器: broker.emqx.io:1883"
echo "  客户端ID: vda5050"
echo "  协议: MQTT 3.1.1"
echo
echo "📡 订阅以下Topic接收AGV状态："
echo "  /uagv/v2/SEER/VWED-0010/state"
echo "  /uagv/v2/SEER/VWED-0010/visualization"
echo "  /uagv/v2/SEER/VWED-0010/connection"
echo
echo "📤 发送指令到以下Topic："
echo "  /uagv/v2/SEER/VWED-0010/order"
echo "  /uagv/v2/SEER/VWED-0010/instantActions"
echo
echo "注意：如果系统没有GUI终端，组件已在后台启动"
echo "可以使用 'ps aux | grep python' 查看运行状态"
echo "日志文件位于 ../logs/ 目录中"
echo
echo "按Enter键退出..."
read 