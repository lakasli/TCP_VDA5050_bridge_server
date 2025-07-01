#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议消息定义模块
包含所有VDA5050协议消息类型的标准格式定义

该模块为VDA5050协议的六种主题消息提供了完整的Python类定义：
- OrderMessage: 订单消息
- StateMessage: 状态消息  
- InstantActionsMessage: 即时动作消息
- VisualizationMessage: 可视化消息
- ConnectionMessage: 连接消息
- FactsheetMessage: 规格说明书消息

每个消息类都包含：
- 完整的字段定义
- 数据验证功能
- JSON序列化/反序列化
- 符合VDA5050协议规范的结构
"""

# 基础消息类和工具类
from .base_message import (
    VDA5050BaseMessage,
    Action,
    ActionParameter,
    NodePosition
)

# 订单消息相关类
from .order_message import (
    OrderMessage,
    Node,
    Edge
)

# 状态消息相关类
from .state_message import (
    StateMessage,
    MapInfo,
    NodeState,
    EdgeState,
    ActionState,
    BatteryState,
    Error,
    SafetyState
)

# 即时动作消息类
from .instantActions_message import (
    InstantActionsMessage,
    InstantActionType,
    InstantActionBuilder
)

# 可视化消息相关类
from .visualization_message import (
    VisualizationMessage,
    AGVPosition,
    Velocity
)

# 连接消息类
from .connection_message import ConnectionMessage

# 规格说明书消息相关类
from .factsheet_message import (
    FactsheetMessage,
    TypeSpecification,
    PhysicalParameters,
    ProtocolLimits
)

# 版本信息
__version__ = "1.0.0"
__author__ = "VDA5050 Protocol Implementation"

# 导出所有公共类
__all__ = [
    # 基础类
    "VDA5050BaseMessage",
    "Action",
    "ActionParameter", 
    "NodePosition",
    
    # 订单消息
    "OrderMessage",
    "Node",
    "Edge",
    
    # 状态消息
    "StateMessage",
    "MapInfo",
    "NodeState",
    "EdgeState", 
    "ActionState",
    "BatteryState",
    "Error",
    "SafetyState",
    
    # 即时动作消息
    "InstantActionsMessage",
    "InstantActionType",
    "InstantActionBuilder",
    
    # 可视化消息
    "VisualizationMessage",
    "AGVPosition",
    "Velocity",
    
    # 连接消息
    "ConnectionMessage",
    
    # 规格说明书消息
    "FactsheetMessage",
    "TypeSpecification",
    "PhysicalParameters",
    "ProtocolLimits",
    
    # 工具函数和变量
    "MESSAGE_TYPES",
    "get_message_class"
]

# 消息类型映射，方便通过字符串获取对应的消息类
MESSAGE_TYPES = {
    "order": OrderMessage,
    "state": StateMessage,
    "instantActions": InstantActionsMessage,
    "visualization": VisualizationMessage,
    "connection": ConnectionMessage,
    "factsheet": FactsheetMessage
}

def get_message_class(message_type: str):
    """
    根据消息类型字符串获取对应的消息类
    
    Args:
        message_type: 消息类型 ("order", "state", "instantActions", "visualization", "connection", "factsheet")
    
    Returns:
        对应的消息类，如果类型不存在则返回None
    """
    return MESSAGE_TYPES.get(message_type) 