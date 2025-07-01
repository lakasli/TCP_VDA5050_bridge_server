# VDA5050协议到TCP协议映射表

## 概述
本文档详细说明了VDA5050协议消息到TCP协议API的映射关系，包括消息类型、动作映射、数据结构转换和API接口设计。

---

## 1. 消息类型映射总览

| VDA5050消息类型 | TCP API接口 | 通信方向 | 触发条件 | 优先级 |
|----------------|-------------|----------|----------|---------|
| Order | `/api/v1/agv/order` | 控制系统 → AGV | 任务下发 | 高 |
| InstantActions | `/api/v1/agv/instant-actions` | 控制系统 → AGV | 紧急控制 | 最高 |
| State | `/api/v1/agv/state` | AGV → 控制系统 | 周期性上报 | 高 |
| Visualization | `/api/v1/agv/visualization` | AGV → 控制系统 | 实时位置 | 中 |
| Connection | `/api/v1/agv/connection` | AGV → 控制系统 | 连接状态变化 | 高 |
| Factsheet | `/api/v1/agv/factsheet` | AGV → 控制系统 | 初始化/请求 | 低 |

---

## 2. 详细API接口映射

### 2.1 订单消息 (Order) → TCP API

#### API接口：`POST /api/v1/agv/order`

**请求参数映射：**
```json
{
  "header": {
    "requestId": "VDA5050.headerId",
    "timestamp": "VDA5050.timestamp",
    "agvId": "VDA5050.serialNumber"
  },
  "order": {
    "orderId": "VDA5050.orderId",
    "orderUpdateId": "VDA5050.orderUpdateId",
    "zoneSetId": "VDA5050.zoneSetId",
    "nodes": [
      {
        "nodeId": "VDA5050.nodes[].nodeId",
        "sequenceId": "VDA5050.nodes[].sequenceId",
        "released": "VDA5050.nodes[].released",
        "position": {
          "x": "VDA5050.nodes[].nodePosition.x",
          "y": "VDA5050.nodes[].nodePosition.y",
          "theta": "VDA5050.nodes[].nodePosition.theta",
          "mapId": "VDA5050.nodes[].nodePosition.mapId"
        },
        "actions": [
          {
            "actionId": "VDA5050.nodes[].actions[].actionId",
            "actionType": "VDA5050.nodes[].actions[].actionType",
            "blockingType": "VDA5050.nodes[].actions[].blockingType",
            "parameters": "VDA5050.nodes[].actions[].actionParameters"
          }
        ]
      }
    ],
    "edges": [
      {
        "edgeId": "VDA5050.edges[].edgeId",
        "sequenceId": "VDA5050.edges[].sequenceId",
        "startNodeId": "VDA5050.edges[].startNodeId",
        "endNodeId": "VDA5050.edges[].endNodeId",
        "maxSpeed": "VDA5050.edges[].maxSpeed",
        "trajectory": "VDA5050.edges[].trajectory"
      }
    ]
  }
}
```

**响应格式：**
```json
{
  "success": true,
  "requestId": "匹配请求ID",
  "message": "订单接收成功",
  "orderStatus": "ACCEPTED|REJECTED",
  "errors": []
}
```

---

### 2.2 即时动作消息 (InstantActions) → TCP API

#### API接口：`POST /api/v1/agv/instant-actions`

**动作类型映射表：**

| VDA5050动作类型 | TCP API动作 | 参数映射 | 执行优先级 |
|----------------|-------------|----------|-----------|
| `startPause` | `PAUSE_TASK` | 无 | 紧急 |
| `stopPause` | `RESUME_TASK` | 无 | 紧急 |
| `cancelOrder` | `CANCEL_ORDER` | 无 | 紧急 |
| `softEmc` | `EMERGENCY_STOP` | `status: boolean` | 最高 |
| `clearErrors` | `CLEAR_ERRORS` | 无 | 高 |
| `motion` | `EXECUTE_MOTION` | `vx, vy, w, duration` | 高 |
| `translate` | `EXECUTE_TRANSLATE` | `dist, vx, vy, mode` | 高 |
| `turn` | `EXECUTE_TURN` | `angle, vw, mode` | 高 |
| `rotateAgv` | `ROTATE_VEHICLE` | `angle` | 中 |
| `reloc` | `RELOCALIZE` | `isAuto, x, y, angle, length, home` | 中 |
| `initPosition` | `INIT_POSITION` | `x, y, theta, coordinate, reachAngle, reachDist, useOdo, maxSpeed, maxRot, holdDir` | 中 |
| `pick` | `PICK_LOAD` | `start_height, end_height` | 高 |
| `drop` | `DROP_LOAD` | `start_height, end_height` | 高 |
| `rotateLoad` | `ROTATE_LOAD` | `angle` | 中 |
| `stateRequest` | `REQUEST_STATE` | 无 | 低 |

**请求参数映射：**
```json
{
  "header": {
    "requestId": "VDA5050.headerId",
    "timestamp": "VDA5050.timestamp",
    "agvId": "VDA5050.serialNumber"
  },
  "actions": [
    {
      "actionId": "VDA5050.actions[].actionId",
      "actionType": "映射后的TCP动作类型",
      "blockingType": "VDA5050.actions[].blockingType",
      "parameters": {
        "key1": "value1",
        "key2": "value2"
      }
    }
  ]
}
```

---

### 2.3 状态消息 (State) → TCP API

#### API接口：`POST /api/v1/agv/state`

**状态数据映射：**
```json
{
  "header": {
    "reportId": "VDA5050.headerId",
    "timestamp": "VDA5050.timestamp",
    "agvId": "VDA5050.serialNumber"
  },
  "orderStatus": {
    "orderId": "VDA5050.orderId",
    "orderUpdateId": "VDA5050.orderUpdateId",
    "lastNodeId": "VDA5050.lastNodeId",
    "lastNodeSequenceId": "VDA5050.lastNodeSequenceId",
    "driving": "VDA5050.driving",
    "paused": "VDA5050.paused",
    "newBaseRequest": "VDA5050.newBaseRequest",
    "distanceSinceLastNode": "VDA5050.distanceSinceLastNode"
  },
  "position": {
    "x": "VDA5050.agvPosition.x",
    "y": "VDA5050.agvPosition.y",
    "theta": "VDA5050.agvPosition.theta",
    "mapId": "VDA5050.agvPosition.mapId",
    "positionInitialized": "VDA5050.agvPosition.positionInitialized"
  },
  "velocity": {
    "vx": "VDA5050.velocity.vx",
    "vy": "VDA5050.velocity.vy",
    "omega": "VDA5050.velocity.omega"
  },
  "battery": {
    "charge": "VDA5050.batteryState.batteryCharge",
    "voltage": "VDA5050.batteryState.batteryVoltage",
    "health": "VDA5050.batteryState.batteryHealth",
    "charging": "VDA5050.batteryState.charging",
    "reach": "VDA5050.batteryState.reach"
  },
  "operatingMode": "VDA5050.operatingMode",
  "safety": {
    "eStop": "VDA5050.safetyState.eStop",
    "fieldViolation": "VDA5050.safetyState.fieldViolation",
    "protectiveField": "VDA5050.safetyState.protectiveField"
  },
  "nodeStates": [
    {
      "nodeId": "VDA5050.nodeStates[].nodeId",
      "sequenceId": "VDA5050.nodeStates[].sequenceId",
      "released": "VDA5050.nodeStates[].released"
    }
  ],
  "actionStates": [
    {
      "actionId": "VDA5050.actionStates[].actionId",
      "actionType": "VDA5050.actionStates[].actionType",
      "actionStatus": "VDA5050.actionStates[].actionStatus",
      "resultDescription": "VDA5050.actionStates[].resultDescription"
    }
  ],
  "errors": [
    {
      "errorType": "VDA5050.errors[].errorType",
      "errorLevel": "VDA5050.errors[].errorLevel",
      "errorDescription": "VDA5050.errors[].errorDescription"
    }
  ],
  "loads": "VDA5050.loads",
  "information": "VDA5050.information"
}
```

---

### 2.4 可视化消息 (Visualization) → TCP API

#### API接口：`POST /api/v1/agv/visualization`

**可视化数据映射：**
```json
{
  "header": {
    "reportId": "VDA5050.headerId",
    "timestamp": "VDA5050.timestamp",
    "agvId": "VDA5050.serialNumber"
  },
  "position": {
    "x": "VDA5050.agvPosition.x",
    "y": "VDA5050.agvPosition.y",
    "theta": "VDA5050.agvPosition.theta",
    "mapId": "VDA5050.agvPosition.mapId",
    "localizationScore": "VDA5050.agvPosition.localizationScore",
    "deviationRange": "VDA5050.agvPosition.deviationRange"
  },
  "velocity": {
    "vx": "VDA5050.velocity.vx",
    "vy": "VDA5050.velocity.vy",
    "omega": "VDA5050.velocity.omega"
  }
}
```

---

### 2.5 连接消息 (Connection) → TCP API

#### API接口：`POST /api/v1/agv/connection`

**连接状态映射：**
```json
{
  "header": {
    "reportId": "VDA5050.headerId",
    "timestamp": "VDA5050.timestamp",
    "agvId": "VDA5050.serialNumber"
  },
  "connectionState": "VDA5050.connectionState", // ONLINE, OFFLINE, CONNECTIONBROKEN
  "lastHeartbeat": "timestamp",
  "networkQuality": "计算值"
}
```

---

### 2.6 规格说明书消息 (Factsheet) → TCP API

#### API接口：`GET /api/v1/agv/factsheet`

**规格数据映射：**
```json
{
  "header": {
    "reportId": "VDA5050.headerId",
    "timestamp": "VDA5050.timestamp",
    "agvId": "VDA5050.serialNumber"
  },
  "typeSpecification": {
    "seriesName": "VDA5050.typeSpecification.seriesName",
    "agvKinematic": "VDA5050.typeSpecification.agvKinematic",
    "agvClass": "VDA5050.typeSpecification.agvClass",
    "maxLoadMass": "VDA5050.typeSpecification.maxLoadMass",
    "localizationTypes": "VDA5050.typeSpecification.localizationTypes",
    "navigationTypes": "VDA5050.typeSpecification.navigationTypes"
  },
  "physicalParameters": {
    "speedMin": "VDA5050.physicalParameters.speedMin",
    "speedMax": "VDA5050.physicalParameters.speedMax",
    "accelerationMax": "VDA5050.physicalParameters.accelerationMax",
    "size": {
      "length": "VDA5050.physicalParameters.length",
      "width": "VDA5050.physicalParameters.width",
      "height": "VDA5050.physicalParameters.heightMax"
    }
  },
  "capabilities": {
    "supportedActions": "VDA5050.protocolFeatures.agvActions",
    "maxNodes": "VDA5050.protocolLimits.maxArrayLens['order.nodes']",
    "maxEdges": "VDA5050.protocolLimits.maxArrayLens['order.edges']"
  }
}
```

---

## 3. 通信协议设计

### 3.1 TCP连接管理

```json
{
  "connectionType": "TCP_PERSISTENT",
  "port": 8080,
  "heartbeatInterval": 30000, // 30秒
  "timeout": 120000, // 2分钟
  "retryAttempts": 3,
  "compressionEnabled": true
}
```

### 3.2 消息格式标准

```json
{
  "messageType": "REQUEST|RESPONSE|NOTIFICATION",
  "version": "1.0",
  "header": {
    "messageId": "唯一标识符",
    "timestamp": "ISO8601格式时间戳",
    "source": "发送方标识",
    "destination": "接收方标识",
    "priority": "HIGH|MEDIUM|LOW"
  },
  "payload": {
    // 具体消息内容
  },
  "checksum": "消息校验和"
}
```

### 3.3 错误处理映射

| VDA5050错误级别 | TCP错误码 | 处理方式 |
|----------------|----------|----------|
| `WARNING` | 4001-4999 | 记录日志，继续执行 |
| `FATAL` | 5001-5999 | 停止执行，需要干预 |
| `SENSOR_FAILURE` | 4101 | 传感器故障警告 |
| `BATTERY_LOW` | 4201 | 低电量警告 |
| `NAVIGATION_ERROR` | 5101 | 导航错误，停止 |
| `SAFETY_VIOLATION` | 5201 | 安全违规，紧急停止 |

---

## 4. 实现建议

### 4.1 API接口优先级

1. **最高优先级：** InstantActions API - 紧急控制
2. **高优先级：** State API - 状态监控
3. **中优先级：** Order API - 任务下发
4. **低优先级：** Visualization, Connection, Factsheet API

### 4.2 数据同步策略

- **State消息：** 每1秒上报一次
- **Visualization消息：** 每2秒上报一次
- **Connection消息：** 状态变化时立即上报
- **Factsheet消息：** 连接建立时上报一次

### 4.3 缓存和队列管理

```json
{
  "messageQueue": {
    "maxSize": 1000,
    "priorityQueue": true,
    "persistentStorage": true
  },
  "responseCache": {
    "maxAge": 300000, // 5分钟
    "maxSize": 100
  }
}
```

---

## 5. 测试验证

### 5.1 单元测试覆盖

- [ ] 所有消息类型的序列化/反序列化
- [ ] 动作参数映射正确性
- [ ] 错误处理机制
- [ ] 网络异常恢复

### 5.2 集成测试场景

- [ ] 完整的任务执行流程
- [ ] 紧急停止响应时间
- [ ] 网络中断恢复
- [ ] 大数据量传输性能

---

## 6. 部署配置

### 6.1 服务器端配置

```yaml
server:
  port: 8080
  maxConnections: 100
  threadPool: 50
  
logging:
  level: INFO
  file: /var/log/vda5050-tcp.log
  
security:
  authentication: true
  encryption: TLS1.2
  
performance:
  bufferSize: 8192
  compressionEnabled: true
```

### 6.2 客户端配置

```yaml
client:
  serverHost: "192.168.1.100"
  serverPort: 8080
  connectTimeout: 30000
  readTimeout: 60000
  
reconnection:
  enabled: true
  maxRetries: 5
  backoffMultiplier: 2.0
```

---

这个映射表为您的VDA5050到TCP协议转换提供了完整的参考框架。您可以根据实际需求调整API接口设计和数据映射关系。 