# VDA5050-MQTT-TCP桥接服务器使用说明

## 概述

VDA5050-MQTT-TCP桥接服务器是一个多线程协议转换服务器，实现VDA5050协议与TCP协议之间的双向转换，通过MQTT与上层系统（如MQTTX）通信，同时通过TCP与AGV硬件通信。

## 系统架构

```
MQTTX客户端 ←→ MQTT代理 ←→ 桥接服务器 ←→ TCP连接 ←→ AGV硬件
     ↑                        ↑                    ↑
  VDA5050协议              协议转换             TCP协议
```

### 主要组件

1. **MQTTClientManager**: MQTT客户端管理器，负责与MQTT代理通信
2. **TCPServerManager**: TCP服务器管理器，负责监听多个端口与AGV通信
3. **ProtocolConverter**: 协议转换器，实现VDA5050与TCP协议间的转换
4. **VDA5050Server**: 主服务器类，协调所有组件

## 功能特性

### 下行转换（MQTTX → AGV）
- **Order消息**: VDA5050订单转换为TCP移动任务列表
- **InstantActions消息**: VDA5050即时动作转换为TCP控制指令

### 上行转换（AGV → MQTTX）
- **State消息**: TCP状态数据转换为VDA5050状态消息
- **Visualization消息**: TCP状态数据转换为VDA5050可视化消息
- **Connection消息**: 创建VDA5050连接状态消息

### TCP端口映射
- `19205`: pick/drop动作
- `19206`: translate动作
- `19207`: turn动作
- `19208`: reloc动作
- `19209`: pause动作
- `19210`: 其他动作
- `19301`: 状态上报

## 安装依赖

```bash
pip install paho-mqtt
```

## 配置文件

### server_config.json
```json
{
    "mqtt": {
        "name": "vda5050",
        "host": "mqtt://broker.emqx.io",
        "port": 1883,
        "client_id": "mqttx_f927dcb3"
    },
    "agv": {
        "ip": "192.168.1.100",
        "manufacturer": "Demo_Manufacturer",
        "serial_number": "AGV_001"
    },
    "tcp_ports": {
        "pick_drop": 19205,
        "translate": 19206,
        "turn": 19207,
        "reloc": 19208,
        "pause": 19209,
        "other": 19210,
        "state": 19301
    }
}
```

## 使用方法

### 1. 启动桥接服务器

```bash
cd test
python mqtt_tcp_bridge_server.py
```

服务器启动后会：
- 连接到MQTT代理（broker.emqx.io:1883）
- 监听所有配置的TCP端口
- 订阅VDA5050下行topic
- 开始协议转换服务

### 2. 启动AGV模拟器（用于测试）

```bash
cd test
python agv_simulator.py --server localhost --agv-id AGV_001
```

AGV模拟器会：
- 连接到服务器的所有TCP端口
- 模拟AGV行为和状态上报
- 处理从服务器接收的控制指令

### 3. 启动MQTT测试客户端

```bash
cd test
python mqtt_test_client.py --broker broker.emqx.io --port 1883
```

测试客户端支持：
- 发送VDA5050 Order消息
- 发送VDA5050 InstantActions消息
- 接收AGV状态反馈

## VDA5050 Topic格式

### 下行Topic（MQTTX → AGV）
- Order: `/uagv/v2/Demo_Manufacturer/AGV_001/order`
- InstantActions: `/uagv/v2/Demo_Manufacturer/AGV_001/instantActions`

### 上行Topic（AGV → MQTTX）
- State: `/uagv/v2/Demo_Manufacturer/AGV_001/state`
- Visualization: `/uagv/v2/Demo_Manufacturer/AGV_001/visualization`
- Connection: `/uagv/v2/Demo_Manufacturer/AGV_001/connection`

## 消息示例

### Order消息示例
```json
{
    "headerId": 1001,
    "timestamp": "2024-01-01T12:00:00.000Z",
    "version": "2.0.0",
    "manufacturer": "Demo_Manufacturer",
    "serialNumber": "AGV_001",
    "orderId": "order_1704110400",
    "orderUpdateId": 0,
    "zoneSetId": "zone_set_1",
    "nodes": [
        {
            "nodeId": "node_1",
            "sequenceId": 0,
            "released": true,
            "nodePosition": {
                "x": 10.5,
                "y": 20.3,
                "theta": 90.0,
                "allowed_deviation_xy": 0.5,
                "allowed_deviation_theta": 5.0
            },
            "actions": []
        }
    ],
    "edges": [
        {
            "edgeId": "edge_1_2",
            "sequenceId": 0,
            "released": true,
            "startNodeId": "node_1",
            "endNodeId": "node_2",
            "maxSpeed": 2.0,
            "actions": []
        }
    ]
}
```

### InstantActions消息示例
```json
{
    "headerId": 1002,
    "timestamp": "2024-01-01T12:00:00.000Z",
    "version": "2.0.0",
    "manufacturer": "Demo_Manufacturer",
    "serialNumber": "AGV_001",
    "actions": [
        {
            "actionType": "translate",
            "actionId": "instant_translate_1704110400_0",
            "actionDescription": "Instant translate action",
            "blocking_type": "HARD",
            "actionParameters": [
                {"key": "x", "value": "50.0"},
                {"key": "y", "value": "30.0"},
                {"key": "theta", "value": "180.0"}
            ]
        }
    ]
}
```

## 日志说明

服务器运行时会输出详细日志：

```
2024-01-01 12:00:00,000 - __main__ - INFO - 正在启动VDA5050协议转换服务器...
2024-01-01 12:00:00,100 - __main__ - INFO - 正在连接MQTT代理: broker.emqx.io:1883
2024-01-01 12:00:00,200 - __main__ - INFO - MQTT连接成功
2024-01-01 12:00:00,300 - __main__ - INFO - 启动TCP服务器 - 端口: 19205, 类型: pick_drop
2024-01-01 12:00:00,400 - __main__ - INFO - VDA5050协议转换服务器启动成功
```

## 测试流程

### 完整测试步骤

1. **启动服务器**:
   ```bash
   python mqtt_tcp_bridge_server.py
   ```

2. **启动AGV模拟器**:
   ```bash
   python agv_simulator.py
   ```

3. **启动MQTT测试客户端**:
   ```bash
   python mqtt_test_client.py
   ```

4. **发送测试消息**:
   - 在MQTT客户端中输入 `1` 发送Order消息
   - 输入 `2` 发送InstantActions消息

5. **观察转换过程**:
   - 服务器日志显示协议转换过程
   - AGV模拟器日志显示指令执行
   - MQTT客户端接收状态反馈

## 故障排除

### 常见问题

1. **MQTT连接失败**
   - 检查网络连接
   - 确认MQTT代理地址和端口
   - 检查防火墙设置

2. **TCP连接失败**
   - 确认端口未被占用
   - 检查AGV IP地址配置
   - 验证网络连通性

3. **协议转换错误**
   - 检查VDA5050消息格式
   - 确认所有必需字段存在
   - 查看详细错误日志

### 调试技巧

1. **启用详细日志**:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **检查端口占用**:
   ```bash
   netstat -an | grep 1920
   ```

3. **测试MQTT连接**:
   ```bash
   mosquitto_pub -h broker.emqx.io -p 1883 -t test -m "hello"
   ```

## 实际部署

### 生产环境配置

1. **修改配置文件**:
   - 更新AGV实际IP地址
   - 配置生产MQTT代理
   - 设置正确的厂商和序列号

2. **安全配置**:
   - 启用MQTT用户认证
   - 配置SSL/TLS加密
   - 设置防火墙规则

3. **监控和日志**:
   - 配置日志轮转
   - 设置系统监控
   - 建立告警机制

## 扩展功能

### 添加新的动作类型

1. 在`ProtocolConverter`中添加端口映射
2. 在转换方法中添加处理逻辑
3. 更新AGV模拟器支持新动作

### 支持多AGV

1. 修改配置文件支持AGV列表
2. 为每个AGV创建独立的TCP连接
3. 实现AGV路由和负载均衡

## 联系支持

如有问题或建议，请通过以下方式联系：
- 查看项目文档和示例
- 检查日志文件获取详细错误信息
- 参考VDA5050协议规范

---

**注意**: 本系统为演示版本，生产环境使用前请进行充分测试和安全评估。 