# TCP连接监听器使用说明

## 概述

`tcp_connection.py` 是一个TCP连接监听器，负责监听小车的状态推送端口，当收到小车的状态上报时，会生成VDA5050协议的connection消息并发布到MQTT。

## 功能特性

- **自动配置读取**：从`robot_config`文件夹读取机器人YAML配置文件
- **多机器人支持**：同时监听多个机器人的状态端口
- **状态监控**：实时监控机器人连接状态，支持心跳检测
- **VDA5050协议**：生成标准的VDA5050连接消息
- **MQTT发布**：将连接状态发布到MQTT主题
- **错误处理**：完善的错误处理和日志记录

## 工作原理

1. **配置加载**：扫描`robot_config`文件夹中的YAML配置文件
2. **端口监听**：为每个机器人在指定端口创建TCP服务器
3. **连接处理**：接受机器人的TCP连接请求
4. **消息解析**：使用TCP协议处理器解析接收到的数据
5. **状态判断**：根据消息类型判断机器人状态
6. **消息发布**：生成VDA5050连接消息并发布到MQTT

## 配置文件结构

TCP连接监听器依赖以下配置：

### 机器人配置文件 (robot_config/*.yaml)

```yaml
# 机器人基本信息
robot_info:
  vehicle_id: "VWED-0010"
  manufacturer: "SEER"

# 网络配置
network:
  ip_address: "127.0.0.1"

# TCP端口配置
tcp_ports:
  # 基础通信端口
  basic_communication:
    status_port: 19204
  # 导航控制端口
  navigation_control:
    push_service_port: 19301

# 报文类型配置
message_types:
  # 状态推送
  status_push:
    robot_status: 9300
```

### MQTT配置文件 (mqtt_config/mqtt_config.yaml)

```yaml
# MQTT服务器配置
mqtt_server:
  host: "localhost"
  port: 1883
  keepalive: 60

# VDA5050主题配置
vda5050_topics:
  state_topic_pattern: "vda5050/{vehicle_id}/state"
```

## 使用方法

### 1. 独立运行

```bash
# 直接运行TCP连接监听器
python protocols/tcp/tcp_connection.py
```

### 2. 集成到现有服务

```python
from protocols.tcp.tcp_connection import TCPConnectionListener

# 创建监听器
listener = TCPConnectionListener(
    config_dir="robot_config",
    mqtt_config_file="mqtt_config/mqtt_config.yaml"
)

# 启动监听器
listener.start()

# 停止监听器
listener.stop()
```

### 3. 与VDA5050服务器集成

```python
from protocols.tcp.tcp_connection import TCPConnectionManager, RobotConfig

# 加载机器人配置
robot_config = RobotConfig("robot_config/VWED-0010.yaml")

# 创建连接管理器
def mqtt_publisher(topic, payload):
    # 自定义MQTT发布函数
    print(f"发布到主题 {topic}: {payload}")

manager = TCPConnectionManager(
    robot_config=robot_config,
    mqtt_publisher=mqtt_publisher
)

# 启动管理器
manager.start()
```

## 监听端口配置

### 端口优先级

1. **push_service_port** (优先使用)
   - 配置路径: `tcp_ports.navigation_control.push_service_port`
   - 默认值: 19301

2. **status_port** (备选)
   - 配置路径: `tcp_ports.basic_communication.status_port`
   - 默认值: 19204

### 消息类型识别

- **状态推送消息**: 9300 (robot_status)
- **心跳消息**: 25940 (常见的心跳类型)
- **其他消息**: 记录但不处理

## 生成的VDA5050消息

### Connection消息格式

```json
{
  "headerId": 1672531200,
  "timestamp": "2023-01-01T00:00:00.000Z",
  "version": "2.0.0",
  "manufacturer": "SEER",
  "serialNumber": "VWED-0010",
  "connectionState": "ONLINE"
}
```

### 连接状态值

- **ONLINE**: 机器人已连接
- **OFFLINE**: 机器人已断开连接
- **CONNECTIONBROKEN**: 连接中断（暂未使用）

### MQTT主题

- 主题格式: `vda5050/{vehicle_id}/connection`
- 示例: `vda5050/VWED-0010/connection`

## 状态监控机制

### 心跳检测

- **连接超时**: 30秒无数据则认为连接断开
- **检查间隔**: 每10秒检查一次连接状态
- **自动清理**: 超时连接自动清理

### 消息统计

- **total_received**: 接收消息总数
- **status_messages**: 状态消息数量
- **heartbeat_messages**: 心跳消息数量
- **unknown_messages**: 未知消息数量

## 日志记录

### 日志级别

- **INFO**: 连接状态变化、启动停止信息
- **DEBUG**: 详细的消息处理信息
- **WARNING**: 连接异常、解析失败等
- **ERROR**: 严重错误信息

### 日志示例

```
2023-01-01 00:00:00,000 - tcp_connection - INFO - 🔗 TCP连接监听器启动 - 机器人: VWED-0010
2023-01-01 00:00:00,000 - tcp_connection - INFO - 📡 监听地址: 127.0.0.1:19301
2023-01-01 00:00:00,000 - tcp_connection - INFO - 🤖 机器人连接: VWED-0010 (127.0.0.1:55001)
2023-01-01 00:00:00,000 - tcp_connection - INFO - 📡 发布连接状态: VWED-0010 -> ONLINE
```

## 错误处理

### 常见错误

1. **配置文件不存在**
   - 检查`robot_config`目录是否存在
   - 确认YAML文件格式正确

2. **端口占用**
   - 检查端口是否被其他进程占用
   - 修改配置文件中的端口号

3. **MQTT连接失败**
   - 检查MQTT服务器地址和端口
   - 验证认证信息是否正确

4. **消息解析失败**
   - 检查TCP协议格式是否正确
   - 确认消息类型配置

### 故障排除

1. **启用详细日志**
   ```python
   import logging
   logging.getLogger().setLevel(logging.DEBUG)
   ```

2. **检查配置文件**
   ```bash
   # 验证YAML格式
   python -c "import yaml; yaml.safe_load(open('robot_config/VWED-0010.yaml'))"
   ```

3. **测试MQTT连接**
   ```bash
   # 使用MQTT客户端测试
   mosquitto_pub -h localhost -p 1883 -t test -m "test"
   ```

## 性能优化

### 建议配置

- **连接超时**: 根据网络环境调整 (30-60秒)
- **检查间隔**: 平衡性能和实时性 (5-15秒)
- **接收缓冲区**: 根据消息大小调整 (4096字节)

### 监控指标

- 连接数量
- 消息处理速率
- 错误率
- 内存使用

## 扩展功能

### 自定义消息处理

可以通过继承`TCPConnectionManager`类来添加自定义的消息处理逻辑：

```python
class CustomTCPConnectionManager(TCPConnectionManager):
    def _handle_status_message(self, parsed_data, client_key):
        super()._handle_status_message(parsed_data, client_key)
        # 添加自定义处理逻辑
        self._process_custom_status(parsed_data)
```

### 连接状态回调

可以添加连接状态变化的回调函数：

```python
def on_connection_change(vehicle_id, state):
    print(f"机器人 {vehicle_id} 连接状态变更: {state}")

manager = TCPConnectionManager(
    robot_config=robot_config,
    mqtt_publisher=mqtt_publisher,
    connection_callback=on_connection_change
)
```

## 总结

TCP连接监听器提供了一个完整的解决方案来监听机器人状态并生成VDA5050连接消息。它具有良好的扩展性和可配置性，适用于各种工业自动化场景。 