#!/bin/bash

# VDA5050 虚拟AGV测试系统启动脚本 (Linux版本)
# 作者: VDA5050 TCP Bridge Server
# 版本: 1.0.1

# 设置UTF-8编码
export LANG=zh_CN.UTF-8

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 检查是否开启了调试模式
DEBUG_MODE=false
if [[ "$1" == "--debug" || "$1" == "-d" ]]; then
    DEBUG_MODE=true
    echo -e "${YELLOW}[调试模式] 启用详细输出${NC}"
fi

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}     VDA5050 虚拟AGV测试系统启动脚本${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# 获取脚本所在目录和父目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

if [ "$DEBUG_MODE" = true ]; then
    echo -e "${CYAN}[调试] 脚本目录: $SCRIPT_DIR${NC}"
    echo -e "${CYAN}[调试] 父目录: $PARENT_DIR${NC}"
fi

# 检查Python是否可用
echo -e "${CYAN}[信息] 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}[错误] 未找到Python，请确保Python已安装并添加到PATH环境变量中${NC}"
    exit 1
fi

# 优先使用python3，如果没有则使用python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo -e "${GREEN}[信息] Python环境检查通过 (使用: $PYTHON_CMD)${NC}"
echo ""

# 检查必要的Python模块
echo -e "${CYAN}[信息] 检查必要的Python模块...${NC}"
required_modules=("paho.mqtt.client" "yaml" "json")
missing_modules=()

for module in "${required_modules[@]}"; do
    if ! ${PYTHON_CMD} -c "import ${module}" &> /dev/null; then
        missing_modules+=("${module}")
    fi
done

if [ ${#missing_modules[@]} -ne 0 ]; then
    echo -e "${YELLOW}[警告] 缺少以下Python模块: ${missing_modules[*]}${NC}"
    echo -e "${YELLOW}[建议] 运行: pip3 install paho-mqtt PyYAML${NC}"
    echo ""
fi

# 创建日志目录（在父目录和当前目录）
mkdir -p "$PARENT_DIR/logs" "$SCRIPT_DIR/logs"
echo -e "${GREEN}[信息] 日志文件将保存到 ../logs/ 和 ./logs/ 目录中${NC}"

# 创建PID文件目录
PID_DIR="$SCRIPT_DIR/pids"
if [ ! -d "$PID_DIR" ]; then
    mkdir -p "$PID_DIR"
    echo -e "${GREEN}[成功] 创建PID目录: $PID_DIR${NC}"
fi

# 检查主要文件是否存在
echo -e "${CYAN}[检查] 验证必要文件...${NC}"
if [ "$DEBUG_MODE" = true ]; then
    echo -e "${CYAN}[调试] 文件检查:${NC}"
    echo -e "${CYAN}       $PARENT_DIR/mqtt_tcp_bridge_server.py: $([ -f "$PARENT_DIR/mqtt_tcp_bridge_server.py" ] && echo '✓' || echo '✗')${NC}"
    echo -e "${CYAN}       $SCRIPT_DIR/agv_simulator.py: $([ -f "$SCRIPT_DIR/agv_simulator.py" ] && echo '✓' || echo '✗')${NC}"
    echo -e "${CYAN}       $SCRIPT_DIR/mqtt_test_client.py: $([ -f "$SCRIPT_DIR/mqtt_test_client.py" ] && echo '✓' || echo '✗')${NC}"
    echo -e "${CYAN}       $SCRIPT_DIR/mqtt_state_monitor.py: $([ -f "$SCRIPT_DIR/mqtt_state_monitor.py" ] && echo '✓' || echo '✗')${NC}"
fi

# 函数：检查TCP端口是否开放
check_tcp_port() {
    local host="$1"
    local port="$2"
    local timeout="$3"
    
    if command -v nc &> /dev/null; then
        # 使用netcat检查端口
        nc -z -w"$timeout" "$host" "$port" 2>/dev/null
        return $?
    elif command -v telnet &> /dev/null; then
        # 使用telnet检查端口
        timeout "$timeout" bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null
        return $?
    else
        # 使用Python检查端口
        ${PYTHON_CMD} -c "
import socket
import sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout($timeout)
    result = sock.connect_ex(('$host', $port))
    sock.close()
    sys.exit(0 if result == 0 else 1)
except:
    sys.exit(1)
" 2>/dev/null
        return $?
    fi
}

# 函数：等待TCP服务启动
wait_for_tcp_service() {
    local service_name="$1"
    local port="$2"
    local max_attempts="$3"
    local delay="$4"
    
    echo -e "${CYAN}[等待] 等待${service_name}的TCP端口${port}启动...${NC}"
    
    for ((i=1; i<=max_attempts; i++)); do
        if check_tcp_port "localhost" "$port" 3; then
            echo -e "${GREEN}[成功] ${service_name}端口${port}已就绪 (尝试${i}/${max_attempts})${NC}"
            return 0
        else
            echo -e "${YELLOW}[等待] ${service_name}端口${port}未就绪，等待${delay}秒... (尝试${i}/${max_attempts})${NC}"
            sleep "$delay"
        fi
    done
    
    echo -e "${RED}[失败] ${service_name}端口${port}在${max_attempts}次尝试后仍未就绪${NC}"
    return 1
}

# 函数：启动服务并记录PID
start_service() {
    local service_name="$1"
    local script_path="$2"
    local working_dir="$3"
    local pid_file="$4"
    local log_file="$5"
    
    echo -e "${CYAN}[启动] ${service_name}...${NC}"
    
    # 检查Python脚本是否存在
    if [ ! -f "$script_path" ]; then
        echo -e "${RED}[错误] Python脚本不存在: $script_path${NC}"
        return 1
    fi
    
    # 检查服务是否已经在运行
    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo -e "${YELLOW}[警告] ${service_name} 已经在运行 (PID: $(cat $pid_file))${NC}"
        return 1
    fi
    
    # 创建日志文件
    mkdir -p "$(dirname "$log_file")"
    touch "$log_file" 2>/dev/null
    
    # 测试Python脚本语法
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "${CYAN}[测试] 检查Python脚本语法: $script_path${NC}"
        ${PYTHON_CMD} -m py_compile "$script_path" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo -e "${RED}[错误] Python脚本语法错误: $script_path${NC}"
            return 1
        fi
    fi
    
    # 调试模式显示启动信息
    if [ "$DEBUG_MODE" = true ]; then
        echo -e "${CYAN}[调试] 启动参数:${NC}"
        echo -e "${CYAN}       工作目录: $working_dir${NC}"
        echo -e "${CYAN}       脚本路径: $script_path${NC}"
        echo -e "${CYAN}       日志文件: $log_file${NC}"
        echo -e "${CYAN}       PID文件: $pid_file${NC}"
    fi
    
    # 启动服务
    cd "$working_dir"
    nohup ${PYTHON_CMD} "$(basename "$script_path")" > "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    cd "$SCRIPT_DIR"
    
    # 等待并检查进程状态
    sleep 2
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}[成功] ${service_name} 已启动 (PID: $pid)${NC}"
        echo -e "${CYAN}[日志] 日志文件: $log_file${NC}"
        
        # 显示最后几行日志
        if [ -f "$log_file" ] && [ -s "$log_file" ]; then
            echo -e "${CYAN}[日志] 最近输出:${NC}"
            tail -n 3 "$log_file" | sed 's/^/       /'
        fi
        return 0
    else
        echo -e "${RED}[失败] ${service_name} 启动失败${NC}"
        rm -f "$pid_file"
        
        # 显示错误日志
        if [ -f "$log_file" ] && [ -s "$log_file" ]; then
            echo -e "${RED}[错误日志]${NC}"
            tail -n 5 "$log_file" | sed 's/^/       /'
        fi
        return 1
    fi
}

# 检查是否有终端模拟器可用
check_terminal() {
    if command -v gnome-terminal &> /dev/null; then
        echo "gnome-terminal"
    elif command -v xterm &> /dev/null; then
        echo "xterm"
    elif command -v konsole &> /dev/null; then
        echo "konsole"
    else
        echo "none"
    fi
}

TERMINAL=$(check_terminal)
if [ "$TERMINAL" = "none" ]; then
    echo -e "${YELLOW}[信息] 未找到GUI终端，所有组件将在后台启动${NC}"
    USE_BACKGROUND=true
else
    echo -e "${CYAN}[信息] 发现终端模拟器: $TERMINAL${NC}"
    USE_BACKGROUND=false
fi

echo ""

# 启动第一个组件：MQTT-TCP桥接服务器
echo -e "${BLUE}[步骤1/4] 启动MQTT-TCP桥接服务器...${NC}"
start_service "MQTT-TCP Bridge Server" "$PARENT_DIR/mqtt_tcp_bridge_server.py" "$PARENT_DIR" \
    "$PID_DIR/bridge_server.pid" "$PARENT_DIR/logs/bridge_server.log"

# 等待TCP服务器的关键端口启动
if wait_for_tcp_service "MQTT-TCP桥接服务器" "19301" 10 2; then
    echo -e "${GREEN}[信息] TCP桥接服务器已完全启动${NC}"
else
    echo -e "${RED}[警告] TCP桥接服务器可能未完全启动，但继续启动其他组件${NC}"
fi

echo -e "${CYAN}[信息] 等待3秒让TCP服务器稳定...${NC}"
sleep 3

# 启动第二个组件：AGV模拟器
echo -e "${BLUE}[步骤2/4] 启动AGV模拟器...${NC}"
start_service "AGV Simulator" "$SCRIPT_DIR/agv_simulator.py" "$SCRIPT_DIR" \
    "$PID_DIR/agv_simulator.pid" "$SCRIPT_DIR/logs/agv_simulator.log"

echo -e "${CYAN}[信息] 等待5秒让AGV模拟器连接...${NC}"
sleep 5

# 启动第三个组件：MQTT测试客户端 (非交互模式)
echo -e "${BLUE}[步骤3/4] 启动MQTT测试客户端...${NC}"
# 修改启动参数，添加非交互模式
cd "$SCRIPT_DIR"
nohup ${PYTHON_CMD} mqtt_test_client.py --non-interactive --auto-send > "$SCRIPT_DIR/logs/mqtt_test_client.log" 2>&1 &
client_pid=$!
echo $client_pid > "$PID_DIR/mqtt_test_client.pid"
cd "$SCRIPT_DIR"

# 检查进程状态
sleep 2
if kill -0 $client_pid 2>/dev/null; then
    echo -e "${GREEN}[成功] MQTT Test Client 已启动 (PID: $client_pid)${NC}"
    echo -e "${CYAN}[日志] 日志文件: $SCRIPT_DIR/logs/mqtt_test_client.log${NC}"
else
    echo -e "${RED}[失败] MQTT Test Client 启动失败${NC}"
    rm -f "$PID_DIR/mqtt_test_client.pid"
fi

echo -e "${CYAN}[信息] 等待2秒让MQTT客户端连接...${NC}"
sleep 2

# 启动第四个组件：MQTT状态监控器
echo -e "${BLUE}[步骤4/4] 启动MQTT状态监控器...${NC}"
start_service "MQTT State Monitor" "$SCRIPT_DIR/mqtt_state_monitor.py" "$SCRIPT_DIR" \
    "$PID_DIR/mqtt_state_monitor.pid" "$SCRIPT_DIR/logs/mqtt_state_monitor.log"

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}              系统启动完成！${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""
echo -e "${GREEN}已启动的组件：${NC}"
echo -e "${GREEN}  1. MQTT-TCP桥接服务器 (端口: 19205-19210, 19301)${NC}"
echo -e "${GREEN}  2. 虚拟AGV模拟器 (模拟VWED-0010)${NC}"
echo -e "${GREEN}  3. MQTT测试客户端 (连接到172.31.232.152:1883)${NC}"
echo -e "${GREEN}  4. MQTT状态监控器 (监听AGV状态消息)${NC}"
echo ""
echo -e "${PURPLE}[MQTTX] 客户端配置建议：${NC}"
echo -e "${PURPLE}  服务器: 172.31.232.152:1883${NC}"
echo -e "${PURPLE}  客户端ID: mqttx_virtual_test_client${NC}"
echo -e "${PURPLE}  协议: MQTT 3.1.1${NC}"
echo ""
echo -e "${PURPLE}[订阅] 以下Topic接收AGV状态：${NC}"
echo -e "${PURPLE}  /uagv/v2/SEER/VWED-0010/state${NC}"
echo -e "${PURPLE}  /uagv/v2/SEER/VWED-0010/visualization${NC}"
echo -e "${PURPLE}  /uagv/v2/SEER/VWED-0010/connection${NC}"
echo ""
echo -e "${PURPLE}[发送] 指令到以下Topic：${NC}"
echo -e "${PURPLE}  /uagv/v2/SEER/VWED-0010/order${NC}"
echo -e "${PURPLE}  /uagv/v2/SEER/VWED-0010/instantActions${NC}"
echo ""
echo -e "${CYAN}[监控] 实时监控命令：${NC}"
echo -e "${CYAN}  查看桥接服务器日志: tail -f ../logs/bridge_server.log${NC}"
echo -e "${CYAN}  查看AGV模拟器日志: tail -f logs/agv_simulator.log${NC}"
echo -e "${CYAN}  查看测试客户端日志: tail -f logs/mqtt_test_client.log${NC}"
echo -e "${CYAN}  查看状态监控器日志: tail -f logs/mqtt_state_monitor.log${NC}"
echo -e "${CYAN}  查看运行的进程: ps aux | grep python${NC}"
echo ""
echo -e "${YELLOW}[注意] 注意事项：${NC}"
echo -e "${YELLOW}  - 所有组件已在后台启动${NC}"
echo -e "${YELLOW}  - 可以使用 'ps aux | grep python' 查看运行状态${NC}"
echo -e "${YELLOW}  - 日志文件位于 ../logs/ 和 ./logs/ 目录中${NC}"
echo -e "${YELLOW}  - 使用以下命令停止系统：${NC}"
echo -e "${YELLOW}    pkill -f mqtt_tcp_bridge_server.py${NC}"
echo -e "${YELLOW}    pkill -f agv_simulator.py${NC}"
echo -e "${YELLOW}    pkill -f mqtt_test_client.py${NC}"
echo -e "${YELLOW}    pkill -f mqtt_state_monitor.py${NC}"
echo ""
echo -e "${GREEN}[成功] 虚拟AGV测试系统已成功启动！${NC}"
echo ""
echo -e "${YELLOW}[故障] 排除指南：${NC}"
echo -e "${YELLOW}  1. 如果启动失败，请使用调试模式：${NC}"
echo -e "${YELLOW}     ./test_start_vda5050_system.sh --debug${NC}"
echo -e "${YELLOW}  2. 检查Python环境和依赖：${NC}"
echo -e "${YELLOW}     ${PYTHON_CMD} -c 'import paho.mqtt.client, yaml, json'${NC}"
echo -e "${YELLOW}  3. 手动测试各个组件：${NC}"
echo -e "${YELLOW}     cd .. && ${PYTHON_CMD} mqtt_tcp_bridge_server.py${NC}"
echo -e "${YELLOW}     ${PYTHON_CMD} agv_simulator.py${NC}"
echo -e "${YELLOW}  4. 查看完整日志：${NC}"
echo -e "${YELLOW}     ls -la logs/ ../logs/${NC}"
echo ""

if [ "$USE_BACKGROUND" = false ]; then
    echo -e "${CYAN}[提示] 如果需要交互式界面，可以手动在终端中运行各个组件${NC}"
    echo ""
fi

echo -e "${GREEN}按Enter键退出...${NC}"
read 