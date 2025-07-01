#!/bin/bash

# VDA5050 真实AGV连接系统启动脚本 (Linux版本)
# 作者: VDA5050 TCP Bridge Server
# 版本: 1.0.0

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}       VDA5050 真实AGV连接系统启动脚本${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# 检查是否以root权限运行（可选）
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}[警告] 正在以root权限运行，建议使用普通用户权限${NC}"
   echo ""
fi

# 检查Python是否可用
echo -e "${CYAN}[信息] 检查Python环境...${NC}"
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}[错误] 未找到Python，请确保Python已安装${NC}"
    echo -e "${RED}       Ubuntu/Debian: sudo apt-get install python3${NC}"
    echo -e "${RED}       CentOS/RHEL: sudo yum install python3${NC}"
    exit 1
fi

# 优先使用python3
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo -e "${GREEN}[信息] Python环境检查通过: $(${PYTHON_CMD} --version)${NC}"
echo ""

# 检查必要的Python模块
echo -e "${CYAN}[信息] 检查必要的Python模块...${NC}"
required_modules=("paho-mqtt" "yaml" "json")
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

# 创建日志目录
if [ ! -d "logs" ]; then
    mkdir -p logs
    echo -e "${GREEN}[信息] 创建日志目录: logs/${NC}"
else
    echo -e "${GREEN}[信息] 日志目录已存在: logs/${NC}"
fi

# 创建PID文件目录
PID_DIR="./pids"
if [ ! -d "$PID_DIR" ]; then
    mkdir -p "$PID_DIR"
fi

echo -e "${GREEN}[信息] 日志文件将保存到 logs/ 目录中${NC}"
echo ""

# 检查端口是否被占用
echo -e "${CYAN}[信息] 检查TCP端口占用情况...${NC}"
ports=(19205 19206 19207 19210 19301)
occupied_ports=()

for port in "${ports[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":${port} " || ss -tuln 2>/dev/null | grep -q ":${port} "; then
        occupied_ports+=("${port}")
    fi
done

if [ ${#occupied_ports[@]} -ne 0 ]; then
    echo -e "${YELLOW}[警告] 以下端口已被占用: ${occupied_ports[*]}${NC}"
    echo -e "${YELLOW}[建议] 请检查并停止占用端口的进程，或修改配置文件${NC}"
    echo ""
fi

# 函数：启动服务并记录PID
start_service() {
    local service_name="$1"
    local script_name="$2"
    local pid_file="$3"
    
    echo -e "${CYAN}[启动] ${service_name}...${NC}"
    
    # 检查服务是否已经在运行
    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo -e "${YELLOW}[警告] ${service_name} 已经在运行 (PID: $(cat $pid_file))${NC}"
        return 1
    fi
    
    # 启动服务
    nohup ${PYTHON_CMD} "$script_name" > "logs/${service_name,,}.log" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    
    # 等待一秒检查进程是否成功启动
    sleep 1
    if kill -0 $pid 2>/dev/null; then
        echo -e "${GREEN}[成功] ${service_name} 已启动 (PID: $pid)${NC}"
        return 0
    else
        echo -e "${RED}[失败] ${service_name} 启动失败${NC}"
        rm -f "$pid_file"
        return 1
    fi
}

echo -e "${BLUE}[步骤1/2] 启动MQTT-TCP桥接服务器...${NC}"
echo -e "${CYAN}[信息] 服务器将监听以下端口等待真实AGV连接：${NC}"
echo -e "${CYAN}        - 19205: 重定位控制${NC}"
echo -e "${CYAN}        - 19206: 运动控制${NC}"
echo -e "${CYAN}        - 19207: 权限控制${NC}"
echo -e "${CYAN}        - 19210: 安全控制${NC}"
echo -e "${CYAN}        - 19301: 状态上报${NC}"
echo ""

# 启动MQTT-TCP桥接服务器
start_service "MQTT-TCP Bridge Server" "mqtt_tcp_bridge_server.py" "$PID_DIR/bridge_server.pid"

echo -e "${CYAN}[信息] 等待8秒让TCP服务器完全启动...${NC}"
sleep 8

echo -e "${BLUE}[步骤2/2] 启动MQTT测试客户端...${NC}"

# 启动MQTT测试客户端
start_service "MQTT Test Client" "mqtt_test_client.py" "$PID_DIR/test_client.pid"

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}              系统启动完成！${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""
echo -e "${GREEN}已启动的组件：${NC}"
echo -e "${GREEN}  1. MQTT-TCP桥接服务器 (端口: 19205-19210, 19301)${NC}"
echo -e "${GREEN}  2. MQTT测试客户端 (连接到broker.emqx.io)${NC}"
echo ""
echo -e "${PURPLE}📱 MQTTX客户端配置建议：${NC}"
echo -e "${PURPLE}  服务器: broker.emqx.io:1883${NC}"
echo -e "${PURPLE}  客户端ID: mqttx_real_agv_client${NC}"
echo ""
echo -e "${PURPLE}🤖 真实AGV配置要求：${NC}"
echo -e "${PURPLE}  AGV需要配置连接到: $(hostname -I | awk '{print $1}') (本机IP)${NC}"
echo -e "${PURPLE}  使用的TCP端口如上所示${NC}"
echo -e "${PURPLE}  AGV ID应配置为: VWED-0010${NC}"
echo -e "${PURPLE}  制造商: SEER${NC}"
echo ""
echo -e "${PURPLE}📡 MQTT话题结构：${NC}"
echo -e "${PURPLE}  订阅AGV状态: /uagv/v2/SEER/VWED-0010/state${NC}"
echo -e "${PURPLE}  订阅可视化: /uagv/v2/SEER/VWED-0010/visualization${NC}"
echo -e "${PURPLE}  订阅连接状态: /uagv/v2/SEER/VWED-0010/connection${NC}"
echo -e "${PURPLE}  发送订单到: /uagv/v2/SEER/VWED-0010/order${NC}"
echo -e "${PURPLE}  发送即时动作: /uagv/v2/SEER/VWED-0010/instantActions${NC}"
echo ""
echo -e "${YELLOW}⚠️  注意事项：${NC}"
echo -e "${YELLOW}  - 确保真实AGV的IP能访问到运行此脚本的计算机${NC}"
echo -e "${YELLOW}  - 防火墙需要开放上述TCP端口${NC}"
echo -e "${YELLOW}  - AGV配置文件应使用 robot_config/VWED-0010.yaml 的参数${NC}"
echo -e "${YELLOW}  - 使用 ./stop_vda5050_system.sh 停止系统${NC}"
echo ""
echo -e "${CYAN}🧪 如需测试虚拟AGV，请运行: ./test/test_start_vda5050_system.sh${NC}"
echo ""
echo -e "${CYAN}📊 实时监控命令：${NC}"
echo -e "${CYAN}  查看桥接服务器日志: tail -f logs/mqtt-tcp\\ bridge\\ server.log${NC}"
echo -e "${CYAN}  查看测试客户端日志: tail -f logs/mqtt\\ test\\ client.log${NC}"
echo -e "${CYAN}  查看系统端口状态: netstat -tuln | grep -E '(19205|19206|19207|19210|19301)'${NC}"
echo ""
echo -e "${GREEN}🚀 系统已成功启动并在后台运行！${NC}" 