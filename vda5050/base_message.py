#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议基础消息类定义
定义了所有VDA5050消息类型的共同字段和基础功能
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
import json


class VDA5050BaseMessage(ABC):
    """VDA5050协议基础消息类"""
    
    def __init__(self, 
                 header_id: int,
                 timestamp: Optional[str] = None,
                 version: str = "2.0.0",
                 manufacturer: str = "",
                 serial_number: str = ""):
        """
        初始化基础消息
        
        Args:
            header_id: 消息头ID
            timestamp: ISO8601格式时间戳，如果为None则使用当前时间
            version: 协议版本
            manufacturer: 制造商
            serial_number: 序列号
        """
        self.header_id = header_id
        self.timestamp = timestamp or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        self.version = version
        self.manufacturer = manufacturer
        self.serial_number = serial_number
    
    @property
    @abstractmethod
    def subtopic(self) -> str:
        """返回消息的子主题"""
        pass
    
    @abstractmethod
    def get_message_dict(self) -> Dict[str, Any]:
        """返回消息的字典表示"""
        pass
    
    def get_base_dict(self) -> Dict[str, Any]:
        """返回基础字段的字典表示"""
        return {
            "headerId": self.header_id,
            "timestamp": self.timestamp,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.get_message_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str):
        """从JSON字符串创建消息对象"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从字典创建消息对象"""
        pass
    
    def validate(self) -> bool:
        """验证消息是否符合VDA5050协议规范"""
        # 基础验证
        if not isinstance(self.header_id, int) or self.header_id < 0:
            return False
        if not self.timestamp:
            return False
        if not self.version:
            return False
        return True


class ActionParameter:
    """动作参数类"""
    
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(data["key"], data["value"])


class Action:
    """动作类"""
    
    def __init__(self,
                 action_id: str,
                 action_type: str,
                 blocking_type: str,
                 action_description: Optional[str] = None,
                 action_parameters: Optional[list] = None):
        self.action_id = action_id
        self.action_type = action_type
        self.blocking_type = blocking_type
        self.action_description = action_description
        self.action_parameters = action_parameters or []
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "actionId": self.action_id,
            "actionType": self.action_type,
            "blockingType": self.blocking_type
        }
        if self.action_description:
            result["actionDescription"] = self.action_description
        if self.action_parameters:
            result["actionParameters"] = [param.to_dict() for param in self.action_parameters]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        action_parameters = []
        if "actionParameters" in data:
            action_parameters = [ActionParameter.from_dict(param) for param in data["actionParameters"]]
        
        return cls(
            action_id=data["actionId"],
            action_type=data["actionType"],
            blocking_type=data["blockingType"],
            action_description=data.get("actionDescription"),
            action_parameters=action_parameters
        )


class NodePosition:
    """节点位置类"""
    
    def __init__(self,
                 x: float,
                 y: float,
                 map_id: str,
                 theta: Optional[float] = None,
                 allowed_deviation_xy: Optional[float] = None,
                 allowed_deviation_theta: Optional[float] = None,
                 map_description: Optional[str] = None):
        self.x = x
        self.y = y
        self.map_id = map_id
        self.theta = theta
        self.allowed_deviation_xy = allowed_deviation_xy
        self.allowed_deviation_theta = allowed_deviation_theta
        self.map_description = map_description
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "x": self.x,
            "y": self.y,
            "mapId": self.map_id
        }
        if self.theta is not None:
            result["theta"] = self.theta
        if self.allowed_deviation_xy is not None:
            result["allowedDeviationXY"] = self.allowed_deviation_xy
        if self.allowed_deviation_theta is not None:
            result["allowedDeviationTheta"] = self.allowed_deviation_theta
        if self.map_description:
            result["mapDescription"] = self.map_description
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            x=data["x"],
            y=data["y"],
            map_id=data["mapId"],
            theta=data.get("theta"),
            allowed_deviation_xy=data.get("allowedDeviationXY"),
            allowed_deviation_theta=data.get("allowedDeviationTheta"),
            map_description=data.get("mapDescription")
        ) 