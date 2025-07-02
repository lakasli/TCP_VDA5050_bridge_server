#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP状态数据转VDA5050可视化消息转换器
从小车上报的TCP状态数据中提取可视化相关参数，封装为VDA5050 visualization topic

端口配置说明：
- 端口19301：AGV状态上报端口（机器人→服务器）
- 报文类型9300：状态数据的标准报文类型
- 转换方向：TCP→VDA5050
"""

import json
import math
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
import sys
import os
import logging

# 添加父目录到Python路径，以便导入vda5050模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vda5050.visualization_message import VisualizationMessage, AGVPosition, Velocity

# 配置常量
TCP_STATE_PORT = 19301      # AGV状态上报端口
STATE_MESSAGE_TYPE = 9300   # 状态数据报文类型

logger = logging.getLogger(__name__)

class TCPStateToVisualizationConverter:
    """TCP状态数据转VDA5050可视化消息转换器"""
    
    def __init__(self):
        """初始化转换器"""
        pass
    
    def convert_tcp_state_to_visualization(self, tcp_state: Dict[str, Any]) -> VisualizationMessage:
        """将TCP状态数据转换为VDA5050可视化消息
        
        处理流程：
        1. 验证TCP状态数据（端口19301，报文类型9300）
        2. 提取位置信息（x, y, angle）转换为AGVPosition
        3. 提取速度信息（vx, vy, w）转换为Velocity
        4. 生成VDA5050标准的可视化消息
        
        Args:
            tcp_state: TCP状态数据字典，应包含：
                      - vehicle_id: 车辆ID
                      - x, y, angle: 位置信息
                      - vx, vy, w: 速度信息（可选）
                      - current_map: 地图ID
                      - confidence: 定位置信度（可选）
            
        Returns:
            VDA5050可视化消息对象
        """
        # 验证数据来源（可选验证）
        message_type = tcp_state.get('messageType')
        if message_type and message_type != STATE_MESSAGE_TYPE:
            logger.warning(f"[WARNING] 数据报文类型 {message_type} 与期望的状态报文类型 {STATE_MESSAGE_TYPE} 不匹配")
        
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
        
        参照VDA5050 AGVPosition结构：
        - x, y: 位置坐标（必需）
        - theta: 朝向角度，弧度制（必需）
        - map_id: 地图ID（必需）
        - position_initialized: 位置是否已初始化（必需）  
        - localization_score: 定位置信度 0.0-1.0（可选）
        - deviation_range: 偏差范围（可选）
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            AGV位置对象，如果数据不完整则返回None
        """
        # 尝试从嵌套的position字段中提取位置信息（AGV模拟器格式）
        position_data = tcp_state.get('position')
        if position_data and isinstance(position_data, dict):
            x = position_data.get('x')
            y = position_data.get('y')
            angle = position_data.get('theta')  # AGV模拟器使用'theta'字段
        else:
            # 回退到扁平结构（原有格式兼容）
            x = tcp_state.get('x')
            y = tcp_state.get('y')
            angle = tcp_state.get('angle') or tcp_state.get('theta')
        
        current_map = tcp_state.get('current_map')
        
        # 检查位置信息的完整性
        if x is None or y is None or angle is None:
            logger.warning(f"[WARNING] 位置信息不完整：x={x}, y={y}, angle={angle}")
            # 使用默认值
            x = x or 0.0
            y = y or 0.0
            angle = angle or 0.0
        
        # 角度值验证和转换
        if not isinstance(angle, (int, float)):
            logger.warning(f"[WARNING] 无效的角度值：{angle}")
            angle = 0.0
        
        # 确保角度在0-360范围内
        angle = angle % 360
        
        # 确定位置是否已初始化
        position_initialized = True  # 如果有位置数据，认为已初始化
        
        # 获取定位置信度（VDA5050要求范围0.0-1.0）
        localization_score = tcp_state.get('confidence')
        if localization_score is not None:
            if not isinstance(localization_score, (int, float)) or localization_score < 0 or localization_score > 1:
                logger.warning(f"[WARNING] 无效的置信度值：{localization_score}")
                localization_score = 0.5  # 默认值
        
        # 获取偏差范围（如果有的话）
        deviation_range = tcp_state.get('deviation_range')
        if deviation_range is not None and not isinstance(deviation_range, (int, float)):
            deviation_range = None
        
        return AGVPosition(
            x=float(x),
            y=float(y),
            theta=float(angle),
            map_id=current_map or "unknown_map",
            position_initialized=position_initialized,
            localization_score=localization_score,
            deviation_range=deviation_range
        )
    
    def _extract_velocity(self, tcp_state: Dict[str, Any]) -> Optional[Velocity]:
        """从TCP状态数据中提取速度信息
        
        参照VDA5050 Velocity结构：
        - vx: 车辆坐标系中x方向速度，单位m/s（可选）
        - vy: 车辆坐标系中y方向速度，单位m/s（可选）  
        - omega: 角速度，单位rad/s（可选）
        
        Args:
            tcp_state: TCP状态数据字典
            
        Returns:
            速度对象，如果没有速度数据则返回None
        """
        # 尝试从嵌套的velocity字段中提取速度信息（AGV模拟器格式）
        velocity_data = tcp_state.get('velocity')
        if velocity_data and isinstance(velocity_data, dict):
            vx = velocity_data.get('vx')
            vy = velocity_data.get('vy')
            w = velocity_data.get('omega')  # AGV模拟器使用'omega'字段
        else:
            # 回退到扁平结构（原有格式兼容）
            vx = tcp_state.get('vx')
            vy = tcp_state.get('vy')
            w = tcp_state.get('w') or tcp_state.get('omega')
        
        # 速度验证
        if vx is not None and not isinstance(vx, (int, float)):
            logger.warning(f"[WARNING] 无效的vx值：{vx}")
            vx = 0.0
        
        if vy is not None and not isinstance(vy, (int, float)):
            logger.warning(f"[WARNING] 无效的vy值：{vy}")
            vy = 0.0
        
        if w is not None and not isinstance(w, (int, float)):
            logger.warning(f"[WARNING] 无效的角速度值：{w}")
            w = 0.0
        
        # 如果没有任何速度数据，返回None
        if vx is None and vy is None and w is None:
            return None
        
        # 使用默认值0.0而不是None，以避免后续处理错误
        return Velocity(
            vx=vx or 0.0,
            vy=vy or 0.0,
            omega=w or 0.0
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
    
    # 验证配置
    print("[配置] 验证:")
    print(f"   状态上报端口: {TCP_STATE_PORT}")
    print(f"   状态报文类型: {STATE_MESSAGE_TYPE}")
    print(f"   转换方向: TCP → VDA5050 Visualization")
    print()
    
    # 创建转换器
    converter = TCPStateToVisualizationConverter()
    
    # 测试完整数据转换
    print("1. 完整TCP状态数据转换测试:")
    sample_state = create_sample_tcp_state()
    # 添加报文类型以验证
    sample_state['messageType'] = STATE_MESSAGE_TYPE
    print("原始TCP状态数据:")
    print(json.dumps(sample_state, indent=2, ensure_ascii=False))
    print("\n转换后的VDA5050可视化消息:")
    result = convert_tcp_state_to_visualization_json(sample_state)
    print(result)
    print("\n" + "="*60 + "\n")
    
    # 测试最小数据转换
    print("2. 最小TCP状态数据转换测试:")
    minimal_state = create_sample_tcp_state_minimal()
    minimal_state['messageType'] = STATE_MESSAGE_TYPE
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
    
    # 测试报文类型不匹配的情况
    print("\n5. 报文类型验证测试:")
    wrong_type_state = sample_state.copy()
    wrong_type_state['messageType'] = 9999  # 错误的报文类型
    print("使用错误报文类型(9999)的转换:")
    result_wrong = convert_tcp_state_to_visualization_json(wrong_type_state)
    print("转换结果仍然生成，但会有警告信息")
    
    # 测试无效数据处理
    print("\n6. 无效数据处理测试:")
    invalid_state = {"vehicle_id": "AGV003"}  # 缺少位置信息
    print("无效TCP状态数据:")
    print(json.dumps(invalid_state, indent=2, ensure_ascii=False))
    print("\n转换结果:")
    result_invalid = convert_tcp_state_to_visualization_json(invalid_state)
    print(result_invalid)
