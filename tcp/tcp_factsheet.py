#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP协议与VDA5050 Factsheet消息转换器
负责处理AGV规格说明书信息的双向转换
"""

import os
import json
import yaml
import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# 导入VDA5050相关类
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from vda5050.factsheet_message import (
        FactsheetMessage, 
        TypeSpecification, 
        PhysicalParameters, 
        ProtocolLimits
    )
    from vda5050.base_message import VDA5050BaseMessage
    VDA5050_AVAILABLE = True
except ImportError as e:
    logging.warning(f"导入VDA5050模块失败: {e}")
    VDA5050_AVAILABLE = False
    
    # 创建占位符类以避免NameError
    class FactsheetMessage:
        pass
    class TypeSpecification:
        pass
    class PhysicalParameters:
        pass
    class ProtocolLimits:
        pass

logger = logging.getLogger(__name__)


class TCPFactsheetConverter:
    """TCP协议与VDA5050 Factsheet消息转换器"""
    
    def __init__(self):
        """初始化转换器"""
        # 默认协议限制
        self.default_protocol_limits = {
            "maxStringLens": {
                "msgId": 255,
                "topic": 255,
                "serialNumber": 255,
                "orderId": 255,
                "zoneSetId": 255,
                "nodeId": 255,
                "edgeId": 255,
                "actionId": 255,
                "actionType": 255,
                "headerId": 255
            },
            "maxArrayLens": {
                "nodes": 1000,
                "edges": 1000,
                "actions": 100,
                "actionParameters": 100,
                "nodeStates": 1000,
                "edgeStates": 1000,
                "actionStates": 100,
                "errors": 100,
                "trajectories": 1000,
                "loads": 100,
                "agvActions": 100,
                "information": 100
            },
            "timing": {
                "minOrderInterval": 1.0,
                "minStateInterval": 0.1,
                "maxNodeWaitTime": 300.0,
                "maxEdgeExecutionTime": 3600.0
            }
        }
        
        # 默认协议特性
        self.default_protocol_features = {
            "optionalParameters": [
                "orderId",
                "orderUpdateId", 
                "zoneSetId",
                "actionParameters"
            ],
            "agvActions": [
                "pick",
                "drop", 
                "move",
                "wait",
                "translate",
                "turn",
                "startPause",
                "stopPause",
                "cancelOrder"
            ],
            "drivingDirection": "BOTH",
            "maxDeviationRange": 1.0,
            "maxRotationSpeed": 3.14159,
            "supportedDeviation": ["x", "y", "theta"]
        }

    def create_factsheet_from_robot_config(self, config_path: str) -> Optional['FactsheetMessage']:
        """从机器人配置文件创建VDA5050 Factsheet消息
        
        Args:
            config_path: 机器人配置文件路径（如robot_config/VWED-0010.yaml）
            
        Returns:
            VDA5050 FactsheetMessage对象，失败则返回None
        """
        try:
            if not VDA5050_AVAILABLE:
                logger.error("VDA5050模块不可用，无法创建Factsheet")
                return None
                
            # 加载机器人配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            logger.info(f"从配置文件创建Factsheet: {config_path}")
            
            # 提取机器人基本信息
            robot_info = config_data.get('robot_info', {})
            network_info = config_data.get('network', {})
            vda5050_config = config_data.get('vda5050', {})
            
            # 创建类型规格
            type_spec_data = robot_info.get('type_specification', {})
            type_specification = TypeSpecification(
                series_name=type_spec_data.get('series_name', 'UNKNOWN_SERIES'),
                agv_kinematic=type_spec_data.get('agv_kinematic', 'DIFF'),
                agv_class=type_spec_data.get('agv_class', 'CARRIER'),
                max_load_mass=type_spec_data.get('max_load_mass', 100.0),
                localization_types=type_spec_data.get('localization_types', ['NATURAL']),
                navigation_types=type_spec_data.get('navigation_types', ['AUTONOMOUS']),
                series_description=type_spec_data.get('series_description', f"{robot_info.get('manufacturer', 'Unknown')} AGV系列")
            )
            
            # 创建物理参数
            physical_data = robot_info.get('physical_parameters', {})
            physical_parameters = PhysicalParameters(
                speed_min=physical_data.get('speed_min', 0.0),
                speed_max=physical_data.get('speed_max', 2.0),
                acceleration_max=physical_data.get('acceleration_max', 1.0),
                deceleration_max=physical_data.get('deceleration_max', 1.5),
                height_min=physical_data.get('height_min', 0.1),
                height_max=physical_data.get('height_max', 2.0),
                width=physical_data.get('width', 0.8),
                length=physical_data.get('length', 1.5)
            )
            
            # 创建协议限制
            protocol_limits_data = vda5050_config.get('protocol_limits', {})
            protocol_limits = ProtocolLimits(
                max_string_lens=protocol_limits_data.get('max_string_lens', self.default_protocol_limits['maxStringLens']),
                max_array_lens=protocol_limits_data.get('max_array_lens', self.default_protocol_limits['maxArrayLens']),
                timing=protocol_limits_data.get('timing', self.default_protocol_limits['timing'])
            )
            
            # 协议特性
            protocol_features = vda5050_config.get('protocol_features', self.default_protocol_features.copy())
            
            # AGV几何结构
            agv_geometry = robot_info.get('agv_geometry', {
                "wheelDefinitions": [],
                "envelope2d": [
                    {"x": 0.6, "y": 0.4},
                    {"x": -0.6, "y": 0.4},
                    {"x": -0.6, "y": -0.4},
                    {"x": 0.6, "y": -0.4}
                ]
            })
            
            # 负载规格
            load_specification = robot_info.get('load_specification', {
                "loadPositions": [
                    {
                        "loadType": "PALLET",
                        "loadPosition": "default",
                        "loadDimensions": {
                            "length": 1.0,
                            "width": 0.8,
                            "height": 0.1
                        },
                        "maxWeight": type_specification.max_load_mass,
                        "boundingBoxReference": {
                            "x": 0.0,
                            "y": 0.0,
                            "z": 0.5
                        }
                    }
                ]
            })
            
            # 创建Factsheet消息
            factsheet = FactsheetMessage(
                header_id=random.randint(100000, 999999),
                type_specification=type_specification,
                physical_parameters=physical_parameters,
                protocol_limits=protocol_limits,
                protocol_features=protocol_features,
                agv_geometry=agv_geometry,
                load_specification=load_specification,
                timestamp=datetime.now(timezone.utc).isoformat(),
                version=vda5050_config.get('protocol_version', '2.0.0'),
                manufacturer=robot_info.get('manufacturer', 'Unknown'),
                serial_number=robot_info.get('serial_number', robot_info.get('vehicle_id', 'Unknown'))
            )
            
            logger.info(f"成功创建Factsheet - 制造商: {factsheet.manufacturer}, 序列号: {factsheet.serial_number}")
            return factsheet
            
        except Exception as e:
            logger.error(f"从配置文件创建Factsheet失败: {e}")
            return None

    def convert_tcp_to_vda5050(self, tcp_data: Dict[str, Any]) -> Optional['FactsheetMessage']:
        """将TCP格式的Factsheet数据转换为VDA5050格式
        
        Args:
            tcp_data: TCP格式的factsheet数据字典
            
        Returns:
            VDA5050 FactsheetMessage对象，失败则返回None
        """
        try:
            if not VDA5050_AVAILABLE:
                logger.error("VDA5050模块不可用，无法转换")
                return None
                
            logger.info("开始转换TCP Factsheet数据为VDA5050格式")
            
            # 提取TCP数据中的各个部分
            type_spec_data = tcp_data.get("type_specification", {})
            physical_params_data = tcp_data.get("physical_parameters", {})
            capabilities = tcp_data.get("capabilities", {})
            safety_features = tcp_data.get("safety_features", {})
            
            # 创建类型规格
            type_specification = TypeSpecification(
                series_name=type_spec_data.get("series_name", tcp_data.get("model", "UNKNOWN_SERIES")),
                agv_kinematic=type_spec_data.get("agv_kinematic", "DIFF"),
                agv_class=type_spec_data.get("agv_class", "CARRIER"),
                max_load_mass=type_spec_data.get("max_load_mass", capabilities.get("max_payload", 100.0)),
                localization_types=type_spec_data.get("localization_types", ["NATURAL"]),
                navigation_types=type_spec_data.get("navigation_types", ["AUTONOMOUS"]),
                series_description=f"转换自TCP的{type_spec_data.get('series_name', 'AGV')}系列"
            )
            
            # 创建物理参数
            physical_parameters = PhysicalParameters(
                speed_min=physical_params_data.get("speed_min", 0.0),
                speed_max=physical_params_data.get("speed_max", 2.0),
                acceleration_max=physical_params_data.get("acceleration_max", 1.0),
                deceleration_max=physical_params_data.get("deceleration_max", 1.5),
                height_min=physical_params_data.get("height_min", 0.1),
                height_max=physical_params_data.get("height_max", 2.0),
                width=physical_params_data.get("width", 0.8),
                length=physical_params_data.get("length", 1.5)
            )
            
            # 创建协议限制（使用默认值）
            protocol_limits = ProtocolLimits(
                max_string_lens=self.default_protocol_limits["maxStringLens"],
                max_array_lens=self.default_protocol_limits["maxArrayLens"],
                timing=self.default_protocol_limits["timing"]
            )
            
            # 创建协议特性（基于TCP数据中的能力信息）
            protocol_features = self.default_protocol_features.copy()
            if "supported_actions" in capabilities:
                protocol_features["agvActions"] = capabilities["supported_actions"]
            
            # 创建AGV几何结构（简化版本）
            agv_geometry = {
                "wheelDefinitions": [
                    {
                        "name": "left_wheel",
                        "type": "DRIVE_WHEEL",
                        "position": {"x": 0.0, "y": 0.25, "z": 0.0},
                        "diameter": 0.2
                    },
                    {
                        "name": "right_wheel", 
                        "type": "DRIVE_WHEEL",
                        "position": {"x": 0.0, "y": -0.25, "z": 0.0},
                        "diameter": 0.2
                    }
                ],
                "envelope2d": [
                    {"x": physical_parameters.length/2, "y": physical_parameters.width/2},
                    {"x": -physical_parameters.length/2, "y": physical_parameters.width/2},
                    {"x": -physical_parameters.length/2, "y": -physical_parameters.width/2},
                    {"x": physical_parameters.length/2, "y": -physical_parameters.width/2}
                ]
            }
            
            # 创建负载规格
            load_specification = {
                "loadPositions": [
                    {
                        "loadType": "PALLET",
                        "loadPosition": "default",
                        "loadDimensions": {
                            "length": 1.0,
                            "width": 0.8,
                            "height": 0.1
                        },
                        "maxWeight": type_specification.max_load_mass,
                        "boundingBoxReference": {
                            "x": 0.0,
                            "y": 0.0,
                            "z": physical_parameters.height_max / 2
                        }
                    }
                ]
            }
            
            # 创建Factsheet消息
            factsheet = FactsheetMessage(
                header_id=random.randint(100000, 999999),
                type_specification=type_specification,
                physical_parameters=physical_parameters,
                protocol_limits=protocol_limits,
                protocol_features=protocol_features,
                agv_geometry=agv_geometry,
                load_specification=load_specification,
                timestamp=tcp_data.get("create_on", datetime.now(timezone.utc).isoformat()),
                version="2.0.0",
                manufacturer=tcp_data.get("manufacturer", "Unknown"),
                serial_number=tcp_data.get("serial_number", tcp_data.get("vehicle_id", "Unknown"))
            )
            
            logger.info(f"TCP数据转换成功 - 制造商: {factsheet.manufacturer}, 序列号: {factsheet.serial_number}")
            return factsheet
            
        except Exception as e:
            logger.error(f"TCP Factsheet转换失败: {e}")
            return None

    def convert_vda5050_to_tcp(self, factsheet_msg: 'FactsheetMessage') -> Dict[str, Any]:
        """将VDA5050 Factsheet消息转换为TCP格式
        
        Args:
            factsheet_msg: VDA5050 FactsheetMessage对象
            
        Returns:
            TCP格式的factsheet数据字典
        """
        try:
            if not VDA5050_AVAILABLE:
                logger.error("VDA5050模块不可用，无法转换")
                return {}
                
            logger.info("开始转换VDA5050 Factsheet为TCP格式")
            
            tcp_data = {
                "vehicle_id": factsheet_msg.serial_number,
                "create_on": factsheet_msg.timestamp or datetime.now(timezone.utc).isoformat(),
                "manufacturer": factsheet_msg.manufacturer,
                "model": factsheet_msg.type_specification.series_name,
                "version": factsheet_msg.version,
                "serial_number": factsheet_msg.serial_number,
                
                # 类型规格
                "type_specification": {
                    "series_name": factsheet_msg.type_specification.series_name,
                    "series_description": factsheet_msg.type_specification.series_description,
                    "agv_kinematic": factsheet_msg.type_specification.agv_kinematic,
                    "agv_class": factsheet_msg.type_specification.agv_class,
                    "max_load_mass": factsheet_msg.type_specification.max_load_mass,
                    "localization_types": factsheet_msg.type_specification.localization_types,
                    "navigation_types": factsheet_msg.type_specification.navigation_types
                },
                
                # 物理参数
                "physical_parameters": {
                    "speed_min": factsheet_msg.physical_parameters.speed_min,
                    "speed_max": factsheet_msg.physical_parameters.speed_max,
                    "acceleration_max": factsheet_msg.physical_parameters.acceleration_max,
                    "deceleration_max": factsheet_msg.physical_parameters.deceleration_max,
                    "height_min": factsheet_msg.physical_parameters.height_min,
                    "height_max": factsheet_msg.physical_parameters.height_max,
                    "width": factsheet_msg.physical_parameters.width,
                    "length": factsheet_msg.physical_parameters.length
                },
                
                # 能力信息
                "capabilities": {
                    "supported_actions": factsheet_msg.protocol_features.get("agvActions", []),
                    "max_payload": factsheet_msg.type_specification.max_load_mass,
                    "battery_capacity": 100.0,  # 默认值
                    "charging_types": ["automatic"],
                    "communication_protocols": ["TCP", "MQTT"]
                },
                
                # 安全特性（默认值）
                "safety_features": {
                    "emergency_stop": True,
                    "collision_avoidance": True,
                    "safety_scanners": 4,
                    "warning_lights": True,
                    "safety_rated": "PLd"
                },
                
                # 协议信息
                "protocol_info": {
                    "protocol_version": factsheet_msg.version,
                    "protocol_limits": factsheet_msg.protocol_limits.to_dict(),
                    "protocol_features": factsheet_msg.protocol_features
                }
            }
            
            logger.info(f"VDA5050转换TCP成功 - 车辆ID: {tcp_data['vehicle_id']}")
            return tcp_data
            
        except Exception as e:
            logger.error(f"VDA5050 Factsheet转换TCP失败: {e}")
            return {}

    def generate_sample_tcp_factsheet(self, vehicle_id: Optional[str] = None) -> Dict[str, Any]:
        """生成示例TCP Factsheet数据
        
        Args:
            vehicle_id: 车辆ID，如果为None则自动生成
            
        Returns:
            示例TCP factsheet数据字典
        """
        if vehicle_id is None:
            vehicle_id = f"AGV_{random.randint(1, 999):03d}"
        
        sample_data = {
            "vehicle_id": vehicle_id,
            "create_on": datetime.now(timezone.utc).isoformat(),
            "manufacturer": "SEER",
            "model": "AGV_Model_" + random.choice(["A", "B", "C"]),
            "version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "serial_number": f"SN{random.randint(100000, 999999)}",
            
            "type_specification": {
                "series_name": "SEER_AGV_SERIES",
                "series_description": "SEER智能搬运机器人系列",
                "agv_kinematic": random.choice(["DIFF", "OMNI", "THREEWHEEL"]),
                "agv_class": random.choice(["CARRIER", "TUGGER", "FORKLIFT"]),
                "max_load_mass": round(random.uniform(50.0, 200.0), 1),
                "localization_types": ["NATURAL", "REFLECTOR"],
                "navigation_types": ["AUTONOMOUS"]
            },
            
            "physical_parameters": {
                "speed_min": 0.0,
                "speed_max": round(random.uniform(1.5, 3.0), 1),
                "acceleration_max": round(random.uniform(0.8, 2.0), 1),
                "deceleration_max": round(random.uniform(1.0, 2.5), 1),
                "height_min": 0.1,
                "height_max": round(random.uniform(1.8, 2.5), 1),
                "width": round(random.uniform(0.6, 1.2), 1),
                "length": round(random.uniform(1.0, 2.0), 1)
            },
            
            "capabilities": {
                "supported_actions": ["pick", "drop", "move", "wait", "translate", "turn", "startPause", "stopPause"],
                "max_payload": round(random.uniform(50, 200), 1),
                "battery_capacity": round(random.uniform(50, 100), 1),
                "charging_types": ["automatic", "manual"],
                "communication_protocols": ["TCP", "MQTT", "HTTP"]
            },
            
            "safety_features": {
                "emergency_stop": True,
                "collision_avoidance": True,
                "safety_scanners": random.randint(2, 6),
                "warning_lights": True,
                "safety_rated": random.choice(["PLd", "PLe"])
            }
        }
        
        logger.info(f"生成示例TCP Factsheet数据 - 车辆ID: {vehicle_id}")
        return sample_data

    def validate_tcp_factsheet(self, tcp_data: Dict[str, Any]) -> bool:
        """验证TCP Factsheet数据的有效性
        
        Args:
            tcp_data: TCP factsheet数据字典
            
        Returns:
            验证结果，True表示有效
        """
        try:
            # 检查必需字段
            required_fields = ["vehicle_id", "manufacturer"]
            for field in required_fields:
                if field not in tcp_data:
                    logger.error(f"缺少必需字段: {field}")
                    return False
            
            # 检查类型规格
            if "type_specification" in tcp_data:
                type_spec = tcp_data["type_specification"]
                valid_kinematics = ["DIFF", "OMNI", "THREEWHEEL", "BICYCLE"]
                valid_classes = ["FORKLIFT", "CONVEYOR", "TUGGER", "CARRIER"]
                
                agv_kinematic = type_spec.get("agv_kinematic")
                if agv_kinematic and agv_kinematic not in valid_kinematics:
                    logger.error(f"无效的运动学类型: {agv_kinematic}")
                    return False
                
                agv_class = type_spec.get("agv_class")
                if agv_class and agv_class not in valid_classes:
                    logger.error(f"无效的AGV类型: {agv_class}")
                    return False
            
            # 检查物理参数
            if "physical_parameters" in tcp_data:
                physical = tcp_data["physical_parameters"]
                speed_max = physical.get("speed_max", 0)
                if speed_max <= 0:
                    logger.error(f"无效的最大速度: {speed_max}")
                    return False
            
            logger.info("TCP Factsheet数据验证通过")
            return True
            
        except Exception as e:
            logger.error(f"验证TCP Factsheet数据时出错: {e}")
            return False

    def get_factsheet_tcp_message_type(self) -> int:
        """获取Factsheet消息的TCP报文类型
        
        Returns:
            TCP报文类型代码
        """
        return 9002  # Factsheet消息的TCP报文类型

    def get_factsheet_tcp_port(self) -> int:
        """获取Factsheet消息的TCP端口
        
        Returns:
            TCP端口号
        """
        return 19200  # Factsheet消息的默认TCP端口


# 工厂函数和工具函数
def create_factsheet_from_config_file(config_path: str) -> Optional['FactsheetMessage']:
    """从配置文件创建Factsheet消息的便利函数
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        FactsheetMessage对象或None
    """
    converter = TCPFactsheetConverter()
    return converter.create_factsheet_from_robot_config(config_path)


def convert_tcp_factsheet_to_vda5050(tcp_data: Dict[str, Any]) -> Optional['FactsheetMessage']:
    """TCP转VDA5050的便利函数
    
    Args:
        tcp_data: TCP factsheet数据
        
    Returns:
        FactsheetMessage对象或None
    """
    converter = TCPFactsheetConverter()
    return converter.convert_tcp_to_vda5050(tcp_data)


def generate_sample_factsheet(vehicle_id: Optional[str] = None) -> Dict[str, Any]:
    """生成示例Factsheet数据的便利函数
    
    Args:
        vehicle_id: 车辆ID
        
    Returns:
        示例TCP factsheet数据
    """
    converter = TCPFactsheetConverter()
    return converter.generate_sample_tcp_factsheet(vehicle_id)


if __name__ == "__main__":
    """测试代码"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建转换器
    converter = TCPFactsheetConverter()
    
    # 测试1: 生成示例TCP数据
    print("=" * 60)
    print("测试1: 生成示例TCP Factsheet数据")
    print("=" * 60)
    sample_tcp = converter.generate_sample_tcp_factsheet("TEST_AGV_001")
    print(json.dumps(sample_tcp, indent=2, ensure_ascii=False))
    
    # 测试2: TCP转VDA5050
    print("\n" + "=" * 60)
    print("测试2: TCP数据转换为VDA5050格式")
    print("=" * 60)
    vda5050_msg = converter.convert_tcp_to_vda5050(sample_tcp)
    if vda5050_msg:
        print(json.dumps(vda5050_msg.get_message_dict(), indent=2, ensure_ascii=False))
    
    # 测试3: VDA5050转TCP
    print("\n" + "=" * 60)
    print("测试3: VDA5050转换回TCP格式")
    print("=" * 60)
    if vda5050_msg:
        tcp_converted = converter.convert_vda5050_to_tcp(vda5050_msg)
        print(json.dumps(tcp_converted, indent=2, ensure_ascii=False))
    
    # 测试4: 从配置文件创建（如果存在）
    config_path = "robot_config/VWED-0010.yaml"
    if os.path.exists(config_path):
        print("\n" + "=" * 60)
        print("测试4: 从配置文件创建Factsheet")
        print("=" * 60)
        config_factsheet = converter.create_factsheet_from_robot_config(config_path)
        if config_factsheet:
            print(f"成功从配置文件创建Factsheet:")
            print(f"制造商: {config_factsheet.manufacturer}")
            print(f"序列号: {config_factsheet.serial_number}")
            print(f"AGV类型: {config_factsheet.type_specification.agv_class}")
            print(f"运动学: {config_factsheet.type_specification.agv_kinematic}")
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60) 