# VDA5050协议标准格式定义

本项目基于VDA5050协议的schema文件，为六种主题消息提供了完整的Python类定义，便于后续转换为TCP协议使用。

## 项目结构

```
protocols/
├── vda5050/
│   ├── __init__.py                 # 模块初始化和导出
│   ├── base_message.py            # 基础消息类和通用组件
│   ├── order_message.py           # 订单消息类
│   ├── state_message.py           # 状态消息类
│   ├── instant_actions_message.py # 即时动作消息类
│   ├── visualization_message.py   # 可视化消息类
│   ├── connection_message.py      # 连接消息类
│   ├── factsheet_message.py       # 规格说明书消息类
│   └── examples.py                # 使用示例
├── tcp/
│   └── manufacturer_a.py          # TCP协议厂商实现(示例)
└── README.md                      # 本文件
```

## 支持的消息类型

### 1. 订单消息 (OrderMessage)
- **子主题**: `/order`
- **用途**: 从主控制系统发送给AGV的订单指令
- **主要组件**: 节点(Node)、边(Edge)、动作(Action)

### 2. 状态消息 (StateMessage)
- **子主题**: `/state`
- **用途**: AGV向主控制系统报告的全面状态信息
- **主要组件**: 节点状态、边状态、动作状态、电池状态、安全状态

### 3. 即时动作消息 (InstantActionsMessage)
- **子主题**: `/instantActions`
- **用途**: 需要AGV立即执行的动作指令
- **主要组件**: 动作列表

### 4. 可视化消息 (VisualizationMessage)
- **子主题**: `/visualization`
- **用途**: AGV位置和速度信息，用于可视化显示
- **主要组件**: AGV位置、速度信息

### 5. 连接消息 (ConnectionMessage)
- **子主题**: `/connection`
- **用途**: AGV连接状态信息
- **主要组件**: 连接状态(ONLINE/OFFLINE/CONNECTIONBROKEN)

### 6. 规格说明书消息 (FactsheetMessage)
- **子主题**: `/factsheet`
- **用途**: AGV的基本信息和能力描述
- **主要组件**: 类型规格、物理参数、协议限制

## 使用方法

### 基本使用

```python
from vda5050 import OrderMessage, StateMessage, Action, Node, NodePosition

# 创建一个简单的订单消息
order = OrderMessage(
    header_id=1,
    order_id="order_001",
    order_update_id=0,
    nodes=[],
    edges=[],
    manufacturer="TEST_MANUFACTURER",
    serial_number="AGV_001"
)

# 转换为JSON
json_str = order.to_json()
print(json_str)

# 从JSON创建对象
order_from_json = OrderMessage.from_json(json_str)

# 验证消息格式
is_valid = order.validate()
print(f"消息格式有效: {is_valid}")
```

### 创建复杂订单

```python
from vda5050 import OrderMessage, Node, Edge, Action, ActionParameter, NodePosition

# 创建动作参数
param = ActionParameter("duration", 5.0)

# 创建动作
action = Action(
    action_id="pick_001",
    action_type="PICK",
    blocking_type="HARD",
    action_parameters=[param]
)

# 创建节点位置
position = NodePosition(
    x=10.0,
    y=20.0,
    map_id="warehouse_floor_1",
    theta=1.57
)

# 创建节点
node = Node(
    node_id="pickup_point",
    sequence_id=0,
    released=True,
    actions=[action],
    node_position=position
)

# 创建边
edge = Edge(
    edge_id="path_001",
    sequence_id=1,
    released=True,
    start_node_id="pickup_point",
    end_node_id="delivery_point",
    actions=[],
    max_speed=2.0
)

# 创建订单
order = OrderMessage(
    header_id=1,
    order_id="complex_order_001",
    order_update_id=0,
    nodes=[node],
    edges=[edge],
    manufacturer="TEST_MANUFACTURER",
    serial_number="AGV_001"
)
```

### 状态消息示例

```python
from vda5050 import StateMessage, BatteryState, SafetyState, NodeState

# 创建电池状态
battery = BatteryState(
    battery_charge=85.5,
    battery_voltage=24.2,
    charging=False
)

# 创建安全状态
safety = SafetyState(
    e_stop="NONE",
    field_violation=False
)

# 创建状态消息
state = StateMessage(
    header_id=1,
    order_id="order_001",
    order_update_id=0,
    last_node_id="node_001",
    last_node_sequence_id=0,
    node_states=[],
    edge_states=[],
    driving=False,
    action_states=[],
    battery_state=battery,
    operating_mode="AUTOMATIC",
    errors=[],
    safety_state=safety,
    manufacturer="TEST_MANUFACTURER",
    serial_number="AGV_001"
)
```

## 运行示例

```bash
# 运行示例代码
python -m vda5050.examples
```

## 特性

### 1. 完整的字段支持
- 支持VDA5050协议中定义的所有必需和可选字段
- 严格按照schema规范进行字段类型和约束定义

### 2. 数据验证
- 每个消息类都提供`validate()`方法
- 验证必需字段、枚举值、数值范围等

### 3. JSON序列化
- 支持`to_json()`和`from_json()`方法
- 支持`from_dict()`和`get_message_dict()`方法

### 4. 类型安全
- 使用Python类型提示
- 明确的参数和返回值类型

### 5. 模块化设计
- 每个消息类型独立文件
- 便于维护和扩展

## 为TCP协议转换做准备

这些标准格式类设计考虑了后续转换为TCP协议的需求：

### 1. 统一的消息接口
```python
# 所有消息类都继承自VDA5050BaseMessage
class VDA5050BaseMessage(ABC):
    @property
    @abstractmethod
    def subtopic(self) -> str:
        """返回消息的子主题"""
        pass
    
    @abstractmethod
    def get_message_dict(self) -> Dict[str, Any]:
        """返回消息的字典表示"""
        pass
```

### 2. 消息类型映射
```python
from vda5050 import MESSAGE_TYPES, get_message_class

# 通过字符串获取消息类
message_class = get_message_class("order")
```

### 3. 易于序列化
- 所有消息都可转换为字典和JSON格式
- 便于在TCP协议中传输

## 协议版本

当前实现基于VDA5050协议2.0.0版本规范。

## 注意事项

1. **字段命名**: 严格遵循VDA5050协议的字段命名约定(驼峰命名法)
2. **数据类型**: 确保数据类型与schema定义一致
3. **枚举值**: 所有枚举类型的值都与协议规范匹配
4. **验证**: 建议在使用前调用`validate()`方法验证消息格式

## 扩展和定制

如需为特定厂商定制TCP协议实现，可以：

1. 继承现有消息类
2. 添加厂商特定字段
3. 实现自定义序列化方法
4. 扩展验证逻辑

示例：
```python
class CustomOrderMessage(OrderMessage):
    def __init__(self, *args, custom_field=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_field = custom_field
    
    def get_message_dict(self):
        result = super().get_message_dict()
        if self.custom_field:
            result["customField"] = self.custom_field
        return result
``` 