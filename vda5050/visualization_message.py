#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议可视化消息类定义
包含AGV位置和速度信息用于可视化目的
"""

from typing import Dict, Any, Optional
from .base_message import VDA5050BaseMessage


class AGVPosition:
    """AGV位置类"""
    
    def __init__(self,
                 x: float,
                 y: float,
                 theta: float,
                 map_id: str,
                 position_initialized: bool,
                 localization_score: Optional[float] = None,
                 deviation_range: Optional[float] = None):
        self.x = x
        self.y = y
        self.theta = theta
        self.map_id = map_id
        self.position_initialized = position_initialized
        self.localization_score = localization_score  # 0.0 to 1.0
        self.deviation_range = deviation_range
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "mapId": self.map_id,
            "positionInitialized": self.position_initialized
        }
        if self.localization_score is not None:
            result["localizationScore"] = self.localization_score
        if self.deviation_range is not None:
            result["deviationRange"] = self.deviation_range
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            x=data["x"],
            y=data["y"],
            theta=data["theta"],
            map_id=data["mapId"],
            position_initialized=data["positionInitialized"],
            localization_score=data.get("localizationScore"),
            deviation_range=data.get("deviationRange")
        )


class Velocity:
    """速度类"""
    
    def __init__(self,
                 vx: Optional[float] = None,
                 vy: Optional[float] = None,
                 omega: Optional[float] = None):
        self.vx = vx  # 车辆坐标系中x方向速度
        self.vy = vy  # 车辆坐标系中y方向速度
        self.omega = omega  # 角速度
    
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.vx is not None:
            result["vx"] = self.vx
        if self.vy is not None:
            result["vy"] = self.vy
        if self.omega is not None:
            result["omega"] = self.omega
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            vx=data.get("vx"),
            vy=data.get("vy"),
            omega=data.get("omega")
        )


class VisualizationMessage(VDA5050BaseMessage):
    """VDA5050可视化消息类"""
    
    def __init__(self,
                 header_id: Optional[int] = None,
                 timestamp: Optional[str] = None,
                 version: Optional[str] = None,
                 manufacturer: Optional[str] = None,
                 serial_number: Optional[str] = None,
                 agv_position: Optional[AGVPosition] = None,
                 velocity: Optional[Velocity] = None):
        # 可视化消息的所有字段都是可选的
        super().__init__(
            header_id or 0, 
            timestamp, 
            version or "2.0.0", 
            manufacturer or "", 
            serial_number or ""
        )
        self.agv_position = agv_position
        self.velocity = velocity
    
    @property
    def subtopic(self) -> str:
        return "/visualization"
    
    def get_message_dict(self) -> Dict[str, Any]:
        result = {}
        
        # 只添加非空的基础字段
        if self.header_id is not None:
            result["headerId"] = self.header_id
        if self.timestamp:
            result["timestamp"] = self.timestamp
        if self.version:
            result["version"] = self.version
        if self.manufacturer:
            result["manufacturer"] = self.manufacturer
        if self.serial_number:
            result["serialNumber"] = self.serial_number
        
        # 添加可选字段
        if self.agv_position:
            result["agvPosition"] = self.agv_position.to_dict()
        if self.velocity:
            result["velocity"] = self.velocity.to_dict()
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        agv_position = None
        if "agvPosition" in data:
            agv_position = AGVPosition.from_dict(data["agvPosition"])
        
        velocity = None
        if "velocity" in data:
            velocity = Velocity.from_dict(data["velocity"])
        
        return cls(
            header_id=data.get("headerId"),
            timestamp=data.get("timestamp"),
            version=data.get("version"),
            manufacturer=data.get("manufacturer"),
            serial_number=data.get("serialNumber"),
            agv_position=agv_position,
            velocity=velocity
        )
    
    def validate(self) -> bool:
        """验证可视化消息（较宽松，因为所有字段都是可选的）"""
        # 如果有位置信息，验证localization_score范围
        if self.agv_position and self.agv_position.localization_score is not None:
            if not (0.0 <= self.agv_position.localization_score <= 1.0):
                return False
        
        return True
    
    def set_position(self, x: float, y: float, theta: float, map_id: str, 
                    position_initialized: bool, localization_score: Optional[float] = None,
                    deviation_range: Optional[float] = None):
        """设置AGV位置"""
        self.agv_position = AGVPosition(
            x, y, theta, map_id, position_initialized, 
            localization_score, deviation_range
        )
    
    def set_velocity(self, vx: Optional[float] = None, vy: Optional[float] = None, 
                    omega: Optional[float] = None):
        """设置AGV速度"""
        self.velocity = Velocity(vx, vy, omega) 