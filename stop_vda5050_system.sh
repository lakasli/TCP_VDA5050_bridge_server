#!/bin/bash

# VDA5050 真实AGV连接系统停止脚本 (Linux版本)
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

echo -e "${RED}=================================================${NC}"
echo -e "${RED}       VDA5050 真实AGV连接系统停止脚本${NC}"
echo -e "${RED}=================================================${NC}"
echo ""

# PID文件目录
PID_DIR="./pids"

# 函数：停止服务
stop_service() {
    local service_name="$1"
    local pid_file="$2"
    
    if [ ! -f "$pid_file" ]; then
        echo -e "${YELLOW}[信息] ${service_name} 没有运行或PID文件不存在${NC}"
        return 1
    fi
    
    local pid=$(cat "$pid_file")
    
    # 检查进程是否存在
    if ! kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}[信息] ${service_name} 进程已经停止 (PID: $pid)${NC}"
        rm -f "$pid_file"
        return 1
    fi
    
    echo -e "${CYAN}[停止] ${service_name} (PID: $pid)...${NC}"
    
    # 尝试优雅关闭
    kill -TERM "$pid" 2>/dev/null
    
    # 等待进程结束
    local wait_count=0
    while kill -0 "$pid" 2>/dev/null && [ $wait_count -lt 10 ]; do
        sleep 1
        wait_count=$((wait_count + 1))
    done
    
    # 检查进程是否已经停止
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}[警告] ${service_name} 没有响应SIGTERM信号，强制终止...${NC}"
        kill -KILL "$pid" 2>/dev/null
        sleep 2
        
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${RED}[失败] 无法停止 ${service_name}${NC}"
            return 1
        fi
    fi
    
    echo -e "${GREEN}[成功] ${service_name} 已停止${NC}"
    rm -f "$pid_file"
    return 0
}

# 函数：按进程名查找并停止
stop_by_name() {
    local process_name="$1"
    local display_name="$2"
    
    # 查找进程ID
    local pids=$(pgrep -f "$process_name" 2>/dev/null)
    
    if [ -z "$pids" ]; then
        echo -e "${YELLOW}[信息] 未找到运行中的 ${display_name} 进程${NC}"
        return 1
    fi
    
    echo -e "${CYAN}[停止] ${display_name} 进程...${NC}"
    
    for pid in $pids; do
        echo -e "${CYAN}[停止] 进程 $pid ($display_name)${NC}"
        kill -TERM "$pid" 2>/dev/null
        
        # 等待进程结束
        local wait_count=0
        while kill -0 "$pid" 2>/dev/null && [ $wait_count -lt 5 ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done
        
        # 强制终止
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}[强制] 强制终止进程 $pid${NC}"
            kill -KILL "$pid" 2>/dev/null
        fi
    done
    
    echo -e "${GREEN}[成功] ${display_name} 进程已停止${NC}"
    return 0
}

echo -e "${BLUE}[步骤1/3] 停止MQTT测试客户端...${NC}"
stop_service "MQTT Test Client" "$PID_DIR/test_client.pid"

echo -e "${BLUE}[步骤2/3] 停止MQTT-TCP桥接服务器...${NC}"
stop_service "MQTT-TCP Bridge Server" "$PID_DIR/bridge_server.pid"

echo -e "${BLUE}[步骤3/3] 清理残余进程...${NC}"
# 按进程名查找并停止可能的残余进程
stop_by_name "mqtt_tcp_bridge_server.py" "MQTT-TCP桥接服务器"

echo ""
echo -e "${CYAN}[清理] 检查端口占用情况...${NC}"
ports=(19205 19206 19207 19210 19301)
occupied_ports=()

for port in "${ports[@]}"; do
    if netstat -tuln 2>/dev/null | grep -q ":${port} " || ss -tuln 2>/dev/null | grep -q ":${port} "; then
        occupied_ports+=("${port}")
    fi
done

if [ ${#occupied_ports[@]} -ne 0 ]; then
    echo -e "${YELLOW}[警告] 以下端口仍被占用: ${occupied_ports[*]}${NC}"
    echo -e "${YELLOW}[建议] 可能有其他进程在使用这些端口${NC}"
else
    echo -e "${GREEN}[成功] 所有VDA5050相关端口已释放${NC}"
fi

# 清理PID文件目录
if [ -d "$PID_DIR" ]; then
    rm -f "$PID_DIR"/*.pid 2>/dev/null
    if [ -z "$(ls -A $PID_DIR 2>/dev/null)" ]; then
        rmdir "$PID_DIR" 2>/dev/null
        echo -e "${GREEN}[清理] PID文件目录已清理${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}              系统停止完成！${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""
echo -e "${GREEN}✅ 已停止的组件：${NC}"
echo -e "${GREEN}  1. MQTT-TCP桥接服务器${NC}"
echo -e "${GREEN}  2. MQTT测试客户端${NC}"
echo ""
echo -e "${CYAN}📊 验证命令：${NC}"
echo -e "${CYAN}  检查进程状态: ps aux | grep -E '(mqtt_tcp_bridge_server)'${NC}"
echo -e "${CYAN}  检查端口状态: netstat -tuln | grep -E '(19205|19206|19207|19210|19301)'${NC}"
echo ""
echo -e "${PURPLE}🔄 重新启动系统: ./start_vda5050_system.sh${NC}"
echo -e "${GREEN}🏁 VDA5050系统已完全停止！${NC}" 