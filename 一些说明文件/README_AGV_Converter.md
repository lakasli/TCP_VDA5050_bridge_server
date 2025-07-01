# AGV 19301端口推送数据到VDA5050转换器

## 概述

本转换器用于将AGV通过19301端口推送的状态数据转换为标准的VDA5050协议格式。它支持完整的字段映射和多种AGV工作场景。

## 功能特点

### 支持的AGV推送字段

| 字段类别 | 字段名称 | 描述 | VDA5050映射 |
|---------|---------|------|-------------|
| **基本信息** | `vehicle_id` | 机器人名称 | `serialNumber` |
| | `create_on` | 时间戳 | `timestamp` |
| | `current_map` | 当前地图 | `maps[].mapId` |
| **位置和移动** | `x`, `y` | 坐标位置 | `agvPosition.x/y` |
| | `angle` | 角度 | `agvPosition.theta` |
| | `vx`, `vy`, `w` | 速度信息 | `velocity.vx/vy/omega` |
| | `is_stop` | 停止状态 | `driving` (取反) |
| **导航和任务** | `current_station` | 当前站点 | `nodeStates[].nodeId` |
| | `task_status` | 任务状态 | `actionStates[].actionStatus` |
| | `task_type` | 任务类型 | `actionStates[].actionType` |
| | `target_dist` | 剩余距离 | `distanceSinceLastNode` |
| **电池信息** | `battery_level` | 电池电量 | `batteryState.batteryCharge` |
| | `charging` | 充电状态 | `batteryState.charging` |
| | `voltage` | 电压 | `batteryState.batteryVoltage` |
| **安全状态** | `emergency` | 急停状态 | `safetyState.eStop` |
| | `blocked` | 阻挡状态 | `safetyState.fieldViolation` |
| | `errors` | 错误列表 | `errors[]` |
| | `warnings` | 警告列表 | `errors[]` (WARNING级别) |

### 支持的工作场景

1. **正常运行场景** - 自动模式下的移动和任务执行
2. **紧急停止场景** - 急停按钮触发或软急停
3. **充电场景** - 在充电站进行充电操作
4. **移动场景** - 路径规划和导航执行
5. **故障场景** - 错误和警告信息处理

## 使用方法

### 基本使用

```python
from tcp.agv_to_vda5050_converter import AGVToVDA5050Converter

# 创建转换器实例
converter = AGVToVDA5050Converter()

# AGV推送数据示例
agv_data = {
    "vehicle_id": "AGV_001",
    "current_map": "warehouse_map_v1",
    "x": 12.5,
    "y": 8.3,
    "angle": 1.57,
    "battery_level": 78.5,
    "task_status": "RUNNING",
    "task_type": "MOVE",
    # ... 其他字段
}

# 执行转换
vda5050_state = converter.convert_agv_data_to_vda5050_state(agv_data)

# 获取VDA5050格式的字典
vda5050_dict = vda5050_state.get_message_dict()

# 转换为JSON字符串
import json
json_output = json.dumps(vda5050_dict, indent=2, ensure_ascii=False)
print(json_output)
```

### 实时数据处理

```python
import socket
import json
from tcp.agv_to_vda5050_converter import AGVToVDA5050Converter

def listen_agv_data():
    """监听AGV 19301端口的推送数据"""
    converter = AGVToVDA5050Converter()
    
    # 创建TCP服务器监听19301端口
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 19301))
    server_socket.listen(1)
    
    print("正在监听AGV推送数据...")
    
    while True:
        conn, addr = server_socket.accept()
        print(f"AGV连接: {addr}")
        
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                # 解析AGV数据
                agv_data = json.loads(data.decode('utf-8'))
                
                # 转换为VDA5050格式
                vda5050_state = converter.convert_agv_data_to_vda5050_state(agv_data)
                vda5050_dict = vda5050_state.get_message_dict()
                
                # 处理转换后的VDA5050数据
                print("接收到VDA5050状态:", json.dumps(vda5050_dict, indent=2))
                
        except Exception as e:
            print(f"处理数据时出错: {e}")
        finally:
            conn.close()
```

### 批量数据转换

```python
def batch_convert_agv_logs(log_file_path):
    """批量转换AGV日志文件"""
    converter = AGVToVDA5050Converter()
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                agv_data = json.loads(line.strip())
                vda5050_state = converter.convert_agv_data_to_vda5050_state(agv_data)
                
                # 保存转换结果
                output_file = f"vda5050_state_{agv_data.get('create_on', 'unknown')}.json"
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    json.dump(vda5050_state.get_message_dict(), out_f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                print(f"转换失败: {e}")
```

## 字段映射规则

### 状态映射

| AGV状态 | VDA5050操作模式 |
|---------|----------------|
| `emergency=True` | `EMERGENCY` |
| `charging=True` | `SERVICE` |
| `soft_emc=True` | `SEMIAUTOMATIC` |
| 其他 | `AUTOMATIC` |

### 任务状态映射

| AGV任务状态 | VDA5050动作状态 |
|------------|----------------|
| `IDLE` | `WAITING` |
| `RUNNING` | `RUNNING` |
| `PAUSED` | `WAITING` |
| `COMPLETED` | `FINISHED` |
| `FAILED` | `FAILED` |
| `CANCELED` | `FAILED` |

### 安全状态映射

| AGV安全状态 | VDA5050安全状态 |
|------------|----------------|
| `emergency=True` 或 `soft_emc=True` | `eStop="TRIGGERED"` |
| 正常状态 | `eStop="AUTOACK"` |
| `blocked=True` | `fieldViolation=True` |

## 运行测试

```bash
# 运行完整测试套件
python tcp/test_agv_converter.py

# 测试包括：
# - 基本转换功能测试
# - 紧急情况场景测试
# - 充电场景测试
# - 移动场景测试
# - 字段映射完整性测试
# - 数据验证测试
```

## 注意事项

### 数据完整性
- 转换器会自动处理缺失字段，使用合理的默认值
- 建议AGV推送包含完整的状态信息以获得最佳转换效果

### 性能考虑
- 转换器设计为实时处理，适合高频率数据推送
- 大批量数据转换时建议使用批处理模式

### 错误处理
- 转换过程中的异常会被捕获并记录
- 无效数据不会导致程序崩溃，会使用默认值继续处理

### 扩展性
- 可以通过继承`AGVToVDA5050Converter`类来添加自定义映射规则
- 支持新增字段的映射配置

## 示例数据

### AGV原始推送数据示例
```json
{
  "vehicle_id": "AGV_001",
  "create_on": 1751276677750,
  "current_map": "warehouse_map_v1",
  "x": 12.5,
  "y": 8.3,
  "angle": 1.57,
  "vx": 0.5,
  "vy": 0.0,
  "w": 0.0,
  "is_stop": false,
  "current_station": "ST001",
  "task_status": "RUNNING",
  "task_type": "MOVE",
  "battery_level": 78.5,
  "charging": false,
  "emergency": false,
  "errors": [],
  "warnings": ["电池温度偏高"]
}
```

### 转换后的VDA5050状态消息示例
```json
{
  "headerId": 1751276677,
  "timestamp": "2025-06-30T09:44:37.751206+00:00",
  "version": "2.0.0",
  "manufacturer": "AGV_Manufacturer",
  "serialNumber": "AGV_001",
  "orderId": "order_AGV_001_1751276677",
  "driving": true,
  "operatingMode": "AUTOMATIC",
  "batteryState": {
    "batteryCharge": 78.5,
    "charging": false
  },
  "agvPosition": {
    "x": 12.5,
    "y": 8.3,
    "theta": 1.57,
    "mapId": "warehouse_map_v1"
  },
  "velocity": {
    "vx": 0.5,
    "vy": 0.0,
    "omega": 0.0
  },
  "safetyState": {
    "eStop": "AUTOACK",
    "fieldViolation": false,
    "protectiveField": "FREE"
  }
}
```

## 技术支持

如有问题或需要技术支持，请查看：
1. 运行测试套件确认功能正常
2. 检查AGV推送数据格式是否符合预期
3. 查看错误日志获取详细信息

转换器已通过完整的测试套件验证，支持多种AGV工作场景和数据格式。 