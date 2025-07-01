#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP状态数据转VDA5050可视化消息转换器
从小车上报的TCP状态数据中提取可视化相关参数，封装为VDA5050 visualization topic
"""

import json
import math
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import sys
import os

# 添加父目录到Python路径，以便导入vda5050模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vda5050.visualization_message import VisualizationMessage, AGVPosition, Velocity


class TCPStateToVisualizationConverter:
    """TCP状态数据转VDA5050可视化消息转换器"""
    
    def __init__(self):
        """初始化转换器"""
        pass
    
    def convert_tcp_state_to_visualization(self, tcp_state: Dict[str, Any]) -> VisualizationMessage:
        """将TCP状态数据转换为VDA5050可视化消息
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            VDA5050可视化消息对象
        """
        # 提取基础消息字段
        header_id = self._generate_header_id_from_timestamp(tcp_state.get('create_on'))
        timestamp = self._convert_tcp_timestamp_to_iso8601(tcp_state.get('create_on'))
        manufacturer = "TCP_AGV"  # 默认制造商
        serial_number = tcp_state.get('vehicle_id', '')
        
        # 提取AGV位置信息
        agv_position = self._extract_agv_position(tcp_state)
        
        # 提取速度信息
        velocity = self._extract_velocity(tcp_state)
        
        # 创建可视化消息
        visualization_msg = VisualizationMessage(
            header_id=header_id,
            timestamp=timestamp,
            version="2.0.0",
            manufacturer=manufacturer,
            serial_number=serial_number,
            agv_position=agv_position,
            velocity=velocity
        )
        
        return visualization_msg
    
    def _extract_agv_position(self, tcp_state: Dict[str, Any]) -> Optional[AGVPosition]:
        """从TCP状态数据中提取AGV位置信息
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            AGV位置对象，如果数据不完整则返回None
        """
        # 检查必要的位置字段
        x = tcp_state.get('x')
        y = tcp_state.get('y')
        angle = tcp_state.get('angle')
        current_map = tcp_state.get('current_map')
        
        if x is None or y is None or angle is None:
            return None
        
        # 转换角度（从小车的角度格式转换为VDA5050的theta格式）
        # 假设小车的angle是角度值，需要转换为弧度
        if isinstance(angle, (int, float)):
            theta = math.radians(angle) if abs(angle) > math.pi * 2 else angle
        else:
            theta = 0.0
        
        # 确定位置是否已初始化
        position_initialized = True  # 如果有位置数据，认为已初始化
        
        # 获取定位置信度
        localization_score = tcp_state.get('confidence')
        if localization_score is not None:
            # 确保置信度在0.0-1.0范围内
            if isinstance(localization_score, (int, float)):
                localization_score = max(0.0, min(1.0, float(localization_score)))
            else:
                localization_score = None
        
        # 获取偏差范围（如果有的话）
        deviation_range = tcp_state.get('deviation_range')
        
        return AGVPosition(
            x=float(x),
            y=float(y),
            theta=float(theta),
            map_id=current_map or "unknown_map",
            position_initialized=position_initialized,
            localization_score=localization_score,
            deviation_range=deviation_range
        )
    
    def _extract_velocity(self, tcp_state: Dict[str, Any]) -> Optional[Velocity]:
        """从TCP状态数据中提取速度信息
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            速度对象，如果没有速度数据则返回None
        """
        vx = tcp_state.get('vx')
        vy = tcp_state.get('vy')
        w = tcp_state.get('w')  # 角速度
        
        # 如果没有任何速度数据，返回None
        if vx is None and vy is None and w is None:
            return None
        
        # 转换数据类型
        vx_float = float(vx) if vx is not None else None
        vy_float = float(vy) if vy is not None else None
        omega_float = float(w) if w is not None else None
        
        return Velocity(
            vx=vx_float,
            vy=vy_float,
            omega=omega_float
        )
    
    def _generate_header_id_from_timestamp(self, timestamp_str: Optional[str]) -> int:
        """从时间戳生成headerId
        
        Args:
            timestamp_str: 时间戳字符串
            
        Returns:
            生成的header ID
        """
        if not timestamp_str:
            return int(datetime.now().timestamp() * 1000) % 2147483647
        
        try:
            # 尝试解析时间戳并转换为整数
            if 'T' in timestamp_str:
                # ISO格式时间戳
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return int(dt.timestamp() * 1000) % 2147483647
            else:
                # 假设是Unix时间戳
                return int(float(timestamp_str) * 1000) % 2147483647
        except (ValueError, TypeError):
            # 如果解析失败，使用当前时间
            return int(datetime.now().timestamp() * 1000) % 2147483647
    
    def _convert_tcp_timestamp_to_iso8601(self, timestamp_str: Optional[str]) -> str:
        """将TCP时间戳转换为ISO8601格式
        
        Args:
            timestamp_str: TCP时间戳字符串
            
        Returns:
            ISO8601格式的时间戳字符串
        """
        if not timestamp_str:
            return datetime.now(timezone.utc).isoformat()
        
        try:
            # 尝试多种时间戳格式
            if 'T' in timestamp_str:
                # 已经是ISO格式，可能需要标准化
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return dt.isoformat()
            else:
                # 假设是Unix时间戳
                dt = datetime.fromtimestamp(float(timestamp_str), tz=timezone.utc)
                return dt.isoformat()
        except (ValueError, TypeError):
            # 如果解析失败，使用当前时间
            return datetime.now(timezone.utc).isoformat()
    
    def convert_to_json(self, tcp_state: Dict[str, Any]) -> str:
        """将TCP状态数据转换为VDA5050可视化消息的JSON字符串
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            VDA5050可视化消息的JSON字符串
        """
        visualization_msg = self.convert_tcp_state_to_visualization(tcp_state)
        return json.dumps(visualization_msg.get_message_dict(), indent=2, ensure_ascii=False)
    
    def extract_visualization_fields(self, tcp_state: Dict[str, Any]) -> Dict[str, Any]:
        """从TCP状态数据中提取可视化相关字段的概要信息
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            包含可视化相关字段概要的字典
        """
        return {
            "basic_info": {
                "vehicle_id": tcp_state.get('vehicle_id'),
                "create_on": tcp_state.get('create_on'),
                "current_map": tcp_state.get('current_map')
            },
            "position": {
                "x": tcp_state.get('x'),
                "y": tcp_state.get('y'),
                "angle": tcp_state.get('angle'),
                "confidence": tcp_state.get('confidence')
            },
            "velocity": {
                "vx": tcp_state.get('vx'),
                "vy": tcp_state.get('vy'),
                "w": tcp_state.get('w'),
                "is_stop": tcp_state.get('is_stop')
            },
            "navigation": {
                "current_station": tcp_state.get('current_station'),
                "target_id": tcp_state.get('target_id'),
                "target_dist": tcp_state.get('target_dist'),
                "task_status": tcp_state.get('task_status')
            }
        }
    
    def is_position_valid(self, tcp_state: Dict[str, Any]) -> bool:
        """检查TCP状态数据中的位置信息是否有效
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            位置信息是否有效
        """
        x = tcp_state.get('x')
        y = tcp_state.get('y')
        angle = tcp_state.get('angle')
        
        return (x is not None and y is not None and angle is not None and
                isinstance(x, (int, float)) and isinstance(y, (int, float)) and
                isinstance(angle, (int, float)))
    
    def is_velocity_available(self, tcp_state: Dict[str, Any]) -> bool:
        """检查TCP状态数据中是否包含速度信息
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            是否包含速度信息
        """
        vx = tcp_state.get('vx')
        vy = tcp_state.get('vy')
        w = tcp_state.get('w')
        
        return any(v is not None and isinstance(v, (int, float)) for v in [vx, vy, w])


# 创建默认转换器实例
visualization_converter = TCPStateToVisualizationConverter()


def convert_tcp_state_to_visualization_json(tcp_state: Union[Dict[str, Any], str]) -> str:
    """TCP状态数据转VDA5050可视化消息的便捷函数
    
    Args:
        tcp_state: TCP状态数据，可以是字典或JSON字符串
        
    Returns:
        VDA5050可视化消息的JSON字符串
    """
    try:
        if isinstance(tcp_state, str):
            state_data = json.loads(tcp_state)
        else:
            state_data = tcp_state
        
        return visualization_converter.convert_to_json(state_data)
    
    except json.JSONDecodeError as e:
        return json.dumps({
            "error": "JSON解析失败",
            "message": str(e)
        }, indent=2, ensure_ascii=False)
    
    except Exception as e:
        return json.dumps({
            "error": "转换失败",
            "message": str(e)
        }, indent=2, ensure_ascii=False)


def create_sample_tcp_state() -> Dict[str, Any]:
    """创建示例TCP状态数据
    
    Returns:
        示例TCP状态数据字典
    """
    return {
        "vehicle_id": "AGV001",
        "create_on": "2024-01-15T10:30:00.000Z",
        "current_map": "factory_floor_1",
        "x": 12.5,
        "y": 8.3,
        "angle": 45.0,  # 角度值
        "vx": 0.5,
        "vy": 0.0,
        "w": 0.1,
        "is_stop": False,
        "confidence": 0.95,
        "current_station": "WS001",
        "target_id": "WS002",
        "target_dist": 15.2,
        "task_status": "DRIVING",
        "battery_level": 0.85,
        "charging": False,
        "voltage": 48.5,
        "emergency": False,
        "blocked": False
    }


def create_sample_tcp_state_minimal() -> Dict[str, Any]:
    """创建最小化的示例TCP状态数据（仅包含必要字段）
    
    Returns:
        最小化的示例TCP状态数据字典
    """
    return {
        "vehicle_id": "AGV002",
        "create_on": "2024-01-15T10:31:00.000Z",
        "x": 10.0,
        "y": 5.0,
        "angle": 0.0
    }


if __name__ == "__main__":
    """测试转换功能"""
    print("=== TCP状态数据转VDA5050可视化消息转换器测试 ===\n")
    
    # 创建转换器
    converter = TCPStateToVisualizationConverter()
    
    # 测试完整数据转换
    print("1. 完整TCP状态数据转换测试:")
    sample_state = create_sample_tcp_state()
    print("原始TCP状态数据:")
    print(json.dumps(sample_state, indent=2, ensure_ascii=False))
    print("\n转换后的VDA5050可视化消息:")
    result = convert_tcp_state_to_visualization_json(sample_state)
    print(result)
    print("\n" + "="*60 + "\n")
    
    # 测试最小数据转换
    print("2. 最小TCP状态数据转换测试:")
    minimal_state = create_sample_tcp_state_minimal()
    print("最小TCP状态数据:")
    print(json.dumps(minimal_state, indent=2, ensure_ascii=False))
    print("\n转换后的VDA5050可视化消息:")
    result_minimal = convert_tcp_state_to_visualization_json(minimal_state)
    print(result_minimal)
    print("\n" + "="*60 + "\n")
    
    # 测试字段提取功能
    print("3. 可视化字段提取测试:")
    visualization_fields = converter.extract_visualization_fields(sample_state)
    print("提取的可视化相关字段:")
    print(json.dumps(visualization_fields, indent=2, ensure_ascii=False))
    print("\n" + "="*60 + "\n")
    
    # 测试数据有效性检查
    print("4. 数据有效性检查测试:")
    print(f"完整数据位置有效性: {converter.is_position_valid(sample_state)}")
    print(f"完整数据速度可用性: {converter.is_velocity_available(sample_state)}")
    print(f"最小数据位置有效性: {converter.is_position_valid(minimal_state)}")
    print(f"最小数据速度可用性: {converter.is_velocity_available(minimal_state)}")
    
    # 测试无效数据处理
    print("\n5. 无效数据处理测试:")
    invalid_state = {"vehicle_id": "AGV003"}  # 缺少位置信息
    print("无效TCP状态数据:")
    print(json.dumps(invalid_state, indent=2, ensure_ascii=False))
    print("\n转换结果:")
    result_invalid = convert_tcp_state_to_visualization_json(invalid_state)
    print(result_invalid)
