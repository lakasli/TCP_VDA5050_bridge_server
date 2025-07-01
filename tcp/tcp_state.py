#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGV 19301端口推送数据转换为VDA5050 State格式的转换器
"""

import json
import time
import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# 添加父目录到路径以便导入vda5050模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vda5050.state_message import (
    StateMessage, NodeState, EdgeState, ActionState, 
    BatteryState, Error, SafetyState, NodePosition, MapInfo
)


class AGVToVDA5050Converter:
    """AGV推送数据到VDA5050状态消息转换器"""
    
    def __init__(self):
        self.last_order_id = ""
        self.last_order_update_id = 0
        self.last_node_id = ""
        self.last_node_sequence_id = 0
        
    def convert_agv_data_to_vda5050_state(self, agv_data: Dict[str, Any]) -> StateMessage:
        """
        将AGV推送数据转换为VDA5050状态消息
        
        Args:
            agv_data: AGV通过19301端口推送的数据
            
        Returns:
            StateMessage: VDA5050标准状态消息
        """
        # 获取当前时间戳
        current_time = datetime.now(timezone.utc).isoformat()
        
        # 提取基本信息
        vehicle_id = agv_data.get('vehicle_id', 'AGV_001')
        current_map = agv_data.get('current_map', 'default_map')
        
        # 创建地图信息
        maps = [MapInfo(
            map_id=current_map,
            map_version="1.0.0",
            map_status="ENABLED",
            map_description="AGV当前运行地图"
        )]
        
        # 创建AGV位置信息
        agv_position = None
        if 'x' in agv_data and 'y' in agv_data:
            agv_position = NodePosition(
                x=float(agv_data.get('x', 0.0)),
                y=float(agv_data.get('y', 0.0)),
                theta=float(agv_data.get('angle', 0.0)),
                map_id=current_map
            )
        
        # 创建速度信息
        velocity = None
        if any(key in agv_data for key in ['vx', 'vy', 'w']):
            velocity = {
                "vx": float(agv_data.get('vx', 0.0)),
                "vy": float(agv_data.get('vy', 0.0)),
                "omega": float(agv_data.get('w', 0.0))
            }
        
        # 创建节点状态
        node_states = []
        current_station = agv_data.get('current_station', '')
        if current_station:
            node_state = NodeState(
                node_id=str(current_station),
                sequence_id=self.last_node_sequence_id,
                released=False,
                node_description=f"当前站点: {current_station}",
                node_position=agv_position
            )
            node_states.append(node_state)
            self.last_node_id = str(current_station)
        
        # 创建边状态（空列表，因为AGV数据中没有直接的边信息）
        edge_states = []
        
        # 判断是否在行驶
        is_driving = not agv_data.get('is_stop', True)
        
        # 创建动作状态
        action_states = []
        task_status = agv_data.get('task_status', 'IDLE')
        task_type = agv_data.get('task_type', 'NONE')
        
        if task_type != 'NONE':
            action_status = self._convert_task_status_to_action_status(task_status)
            action_state = ActionState(
                action_id=f"action_{int(time.time())}",
                action_type=task_type,
                action_status=action_status,
                action_description=f"当前任务: {task_type}",
                result_description=f"任务状态: {task_status}"
            )
            action_states.append(action_state)
        
        # 创建电池状态
        battery_state = BatteryState(
            battery_charge=float(agv_data.get('battery_level', 0.0)),
            battery_voltage=agv_data.get('voltage'),
            battery_health=None,  # AGV数据中没有电池健康状态
            charging=agv_data.get('charging', False),
            reach=None  # AGV数据中没有剩余里程信息
        )
        
        # 创建错误列表
        errors = []
        agv_errors = agv_data.get('errors', [])
        agv_warnings = agv_data.get('warnings', [])
        
        # 处理错误
        for error in agv_errors:
            vda_error = Error(
                error_type="DEVICE_ERROR",
                error_level="FATAL",
                error_description=str(error)
            )
            errors.append(vda_error)
        
        # 处理警告
        for warning in agv_warnings:
            vda_warning = Error(
                error_type="DEVICE_WARNING", 
                error_level="WARNING",
                error_description=str(warning)
            )
            errors.append(vda_warning)
        
        # 创建安全状态
        emergency = agv_data.get('emergency', False)
        soft_emc = agv_data.get('soft_emc', False)
        blocked = agv_data.get('blocked', False)
        
        # 确定E-Stop状态
        e_stop = "TRIGGERED" if (emergency or soft_emc) else "AUTOACK"
        
        safety_state = SafetyState(
            e_stop=e_stop,
            field_violation=blocked,
            protective_field="VIOLATED" if blocked else "FREE"
        )
        
        # 确定操作模式
        operating_mode = self._determine_operating_mode(agv_data)
        
        # 创建VDA5050状态消息
        state_message = StateMessage(
            header_id=int(time.time()),
            order_id=self.last_order_id or f"order_{vehicle_id}_{int(time.time())}",
            order_update_id=self.last_order_update_id,
            last_node_id=self.last_node_id,
            last_node_sequence_id=self.last_node_sequence_id,
            node_states=node_states,
            edge_states=edge_states,
            driving=is_driving,
            action_states=action_states,
            battery_state=battery_state,
            operating_mode=operating_mode,
            errors=errors,
            safety_state=safety_state,
            timestamp=current_time,
            version="2.0.0",
            manufacturer="AGV_Manufacturer",
            serial_number=vehicle_id,
            maps=maps,
            zone_set_id=None,
            paused=agv_data.get('is_stop', False),
            new_base_request=None,
            distance_since_last_node=agv_data.get('target_dist'),
            agv_position=agv_position,
            velocity=velocity,
            loads=self._create_loads_info(agv_data),
            information=self._create_information_list(agv_data)
        )
        
        return state_message
    
    def _convert_task_status_to_action_status(self, task_status: str) -> str:
        """将AGV任务状态转换为VDA5050动作状态"""
        status_mapping = {
            'IDLE': 'WAITING',
            'RUNNING': 'RUNNING', 
            'PAUSED': 'WAITING',
            'COMPLETED': 'FINISHED',
            'FAILED': 'FAILED',
            'CANCELED': 'FAILED'
        }
        return status_mapping.get(task_status.upper(), 'WAITING')
    
    def _determine_operating_mode(self, agv_data: Dict[str, Any]) -> str:
        """根据AGV数据确定操作模式"""
        if agv_data.get('emergency', False):
            return "EMERGENCY"
        elif agv_data.get('soft_emc', False):
            return "SEMIAUTOMATIC"
        elif agv_data.get('charging', False):
            return "SERVICE"
        else:
            return "AUTOMATIC"
    
    def _create_loads_info(self, agv_data: Dict[str, Any]) -> Optional[List[Dict]]:
        """创建载荷信息"""
        loads = []
        
        # 检查货叉状态
        if 'fork' in agv_data:
            fork_info = {
                "loadId": "fork_load",
                "loadType": "PALLET", 
                "loadPosition": "FORK",
                "boundingBoxReference": {"x": 0, "y": 0, "z": 0, "theta": 0},
                "loadDimensions": {"length": 1.2, "width": 0.8, "height": 0.1},
                "weight": 0.0
            }
            loads.append(fork_info)
        
        # 检查顶升状态
        if 'jack' in agv_data:
            jack_info = {
                "loadId": "jack_load",
                "loadType": "RACK",
                "loadPosition": "JACK", 
                "boundingBoxReference": {"x": 0, "y": 0, "z": 0, "theta": 0},
                "loadDimensions": {"length": 1.0, "width": 1.0, "height": 0.05},
                "weight": 0.0
            }
            loads.append(jack_info)
            
        return loads if loads else None
    
    def _create_information_list(self, agv_data: Dict[str, Any]) -> Optional[List[Dict]]:
        """创建信息列表"""
        information = []
        
        # 添加定位信息
        if 'confidence' in agv_data:
            info = {
                "infoType": "LOCALIZATION",
                "infoLevel": "INFO",
                "infoDescription": f"定位置信度: {agv_data['confidence']}"
            }
            information.append(info)
        
        # 添加网络信息
        if 'ssid' in agv_data and 'rssi' in agv_data:
            info = {
                "infoType": "NETWORK",
                "infoLevel": "INFO", 
                "infoDescription": f"WiFi: {agv_data['ssid']}, 信号强度: {agv_data['rssi']}dBm"
            }
            information.append(info)
        
        # 添加温度信息
        if 'controller_temp' in agv_data:
            temp_level = "WARNING" if agv_data['controller_temp'] > 70 else "INFO"
            info = {
                "infoType": "TEMPERATURE",
                "infoLevel": temp_level,
                "infoDescription": f"控制器温度: {agv_data['controller_temp']}°C"
            }
            information.append(info)
        
        # 添加里程信息
        if 'odo' in agv_data:
            info = {
                "infoType": "STATISTICS",
                "infoLevel": "INFO",
                "infoDescription": f"累计里程: {agv_data['odo']}m"
            }
            information.append(info)
            
        return information if information else None


def create_sample_agv_data() -> Dict[str, Any]:
    """创建示例AGV推送数据"""
    return {
        "vehicle_id": "AGV_001",
        "create_on": int(time.time() * 1000),
        "current_map": "warehouse_map_v1",
        "x": 12.5,
        "y": 8.3,
        "angle": 1.57,  # 90度
        "vx": 0.5,
        "vy": 0.0,
        "w": 0.0,
        "is_stop": False,
        "current_station": "ST001",
        "task_status": "RUNNING",
        "task_type": "MOVE",
        "target_dist": 15.2,
        "target_id": "ST002",
        "confidence": 0.95,
        "loc_state": "GOOD",
        "reloc_status": "NORMAL",
        "battery_level": 78.5,
        "charging": False,
        "voltage": 48.2,
        "current": 12.5,
        "battery_temp": 35.0,
        "controller_temp": 42.0,
        "blocked": False,
        "block_reason": "",
        "slowed": False,
        "emergency": False,
        "soft_emc": False,
        "brake": False,
        "DI": [True, False, True, False],
        "DO": [False, True, False, True],
        "errors": [],
        "warnings": ["电池温度偏高"],
        "fork": {"height": 0.0, "extended": False},
        "jack": {"height": 0.0, "active": False},
        "roller": {"speed": 0.0, "active": False},
        "odo": 12580.5,
        "today_odo": 125.8,
        "ssid": "AGV_Network",
        "rssi": -45
    } 