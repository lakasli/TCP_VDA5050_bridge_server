#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议规格说明书消息类定义
包含AGV基本信息和能力描述
"""

from typing import Dict, Any, List, Optional
from .base_message import VDA5050BaseMessage


class TypeSpecification:
    """类型规格类"""
    
    def __init__(self,
                 series_name: str,
                 agv_kinematic: str,
                 agv_class: str,
                 max_load_mass: float,
                 localization_types: List[str],
                 navigation_types: List[str],
                 series_description: Optional[str] = None):
        self.series_name = series_name
        self.series_description = series_description
        self.agv_kinematic = agv_kinematic  # DIFF, OMNI, THREEWHEEL
        self.agv_class = agv_class  # FORKLIFT, CONVEYOR, TUGGER, CARRIER
        self.max_load_mass = max_load_mass
        self.localization_types = localization_types  # NATURAL, REFLECTOR, RFID, DMC, SPOT, GRID
        self.navigation_types = navigation_types  # PHYSICAL_LINE_GUIDED, VIRTUAL_LINE_GUIDED, AUTONOMOUS
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "seriesName": self.series_name,
            "agvKinematic": self.agv_kinematic,
            "agvClass": self.agv_class,
            "maxLoadMass": self.max_load_mass,
            "localizationTypes": self.localization_types,
            "navigationTypes": self.navigation_types
        }
        if self.series_description:
            result["seriesDescription"] = self.series_description
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            series_name=data["seriesName"],
            agv_kinematic=data["agvKinematic"],
            agv_class=data["agvClass"],
            max_load_mass=data["maxLoadMass"],
            localization_types=data["localizationTypes"],
            navigation_types=data["navigationTypes"],
            series_description=data.get("seriesDescription")
        )


class PhysicalParameters:
    """物理参数类"""
    
    def __init__(self,
                 speed_min: float,
                 speed_max: float,
                 acceleration_max: float,
                 deceleration_max: float,
                 height_max: float,
                 width: float,
                 length: float,
                 height_min: Optional[float] = None):
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.acceleration_max = acceleration_max
        self.deceleration_max = deceleration_max
        self.height_min = height_min
        self.height_max = height_max
        self.width = width
        self.length = length
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "speedMin": self.speed_min,
            "speedMax": self.speed_max,
            "accelerationMax": self.acceleration_max,
            "decelerationMax": self.deceleration_max,
            "heightMax": self.height_max,
            "width": self.width,
            "length": self.length
        }
        if self.height_min is not None:
            result["heightMin"] = self.height_min
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            speed_min=data["speedMin"],
            speed_max=data["speedMax"],
            acceleration_max=data["accelerationMax"],
            deceleration_max=data["decelerationMax"],
            height_max=data["heightMax"],
            width=data["width"],
            length=data["length"],
            height_min=data.get("heightMin")
        )


class ProtocolLimits:
    """协议限制类"""
    
    def __init__(self,
                 max_string_lens: Dict[str, int],
                 max_array_lens: Dict[str, int],
                 timing: Dict[str, float]):
        self.max_string_lens = max_string_lens
        self.max_array_lens = max_array_lens
        self.timing = timing
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "maxStringLens": self.max_string_lens,
            "maxArrayLens": self.max_array_lens,
            "timing": self.timing
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            max_string_lens=data["maxStringLens"],
            max_array_lens=data["maxArrayLens"],
            timing=data["timing"]
        )


class FactsheetMessage(VDA5050BaseMessage):
    """VDA5050规格说明书消息类"""
    
    def __init__(self,
                 header_id: Optional[int],
                 type_specification: TypeSpecification,
                 physical_parameters: PhysicalParameters,
                 protocol_limits: ProtocolLimits,
                 protocol_features: Dict[str, Any],
                 agv_geometry: Dict[str, Any],
                 load_specification: Dict[str, Any],
                 timestamp: Optional[str] = None,
                 version: str = "2.0.0",
                 manufacturer: str = "",
                 serial_number: str = ""):
        super().__init__(header_id or 0, timestamp, version, manufacturer, serial_number)
        self.type_specification = type_specification
        self.physical_parameters = physical_parameters
        self.protocol_limits = protocol_limits
        self.protocol_features = protocol_features
        self.agv_geometry = agv_geometry
        self.load_specification = load_specification
    
    @property
    def subtopic(self) -> str:
        return "/factsheet"
    
    def get_message_dict(self) -> Dict[str, Any]:
        result = {}
        
        # 添加基础字段（headerId和timestamp在factsheet中是可选的）
        if self.header_id is not None:
            result["headerId"] = self.header_id
        if self.timestamp:
            result["timestamp"] = self.timestamp
        result["version"] = self.version
        result["manufacturer"] = self.manufacturer
        result["serialNumber"] = self.serial_number
        
        # 添加必需字段
        result.update({
            "typeSpecification": self.type_specification.to_dict(),
            "physicalParameters": self.physical_parameters.to_dict(),
            "protocolLimits": self.protocol_limits.to_dict(),
            "protocolFeatures": self.protocol_features,
            "agvGeometry": self.agv_geometry,
            "loadSpecification": self.load_specification
        })
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        type_specification = TypeSpecification.from_dict(data["typeSpecification"])
        physical_parameters = PhysicalParameters.from_dict(data["physicalParameters"])
        protocol_limits = ProtocolLimits.from_dict(data["protocolLimits"])
        
        return cls(
            header_id=data.get("headerId"),
            type_specification=type_specification,
            physical_parameters=physical_parameters,
            protocol_limits=protocol_limits,
            protocol_features=data["protocolFeatures"],
            agv_geometry=data["agvGeometry"],
            load_specification=data["loadSpecification"],
            timestamp=data.get("timestamp"),
            version=data.get("version", "2.0.0"),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", "")
        )
    
    def validate(self) -> bool:
        """验证规格说明书消息"""
        # 验证AGV运动学类型
        if self.type_specification.agv_kinematic not in ["DIFF", "OMNI", "THREEWHEEL"]:
            return False
        
        # 验证AGV类型
        if self.type_specification.agv_class not in ["FORKLIFT", "CONVEYOR", "TUGGER", "CARRIER"]:
            return False
        
        # 验证定位类型
        valid_localization_types = ["NATURAL", "REFLECTOR", "RFID", "DMC", "SPOT", "GRID"]
        for loc_type in self.type_specification.localization_types:
            if loc_type not in valid_localization_types:
                return False
        
        # 验证导航类型
        valid_navigation_types = ["PHYSICAL_LINE_GUIDED", "VIRTUAL_LINE_GUIDED", "AUTONOMOUS"]
        for nav_type in self.type_specification.navigation_types:
            if nav_type not in valid_navigation_types:
                return False
        
        # 验证物理参数
        if self.type_specification.max_load_mass < 0:
            return False
        if self.physical_parameters.speed_max <= 0:
            return False
        
        return True 