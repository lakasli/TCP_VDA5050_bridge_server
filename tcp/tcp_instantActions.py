#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050即时动作转TCP协议转换器
参考网页前端转换逻辑，实现Python版本的即时动作转换功能
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time
import random
from .manufacturer_a import ManufacturerATCPProtocol


class DataFormatType(Enum):
    """TCP数据格式类型"""
    MOVE_TASK_LIST = "move_task_list"    # 移动任务列表格式
    EMPTY_DATA = "empty_data"            # 空数据格式
    SINGLE_FIELD = "single_field"        # 单独字段格式


@dataclass
class ActionConfig:
    """即时动作配置"""
    port: int
    message_type: int
    data_format: DataFormatType


@dataclass
class TCPActionResult:
    """TCP动作转换结果"""
    action_type: str
    action_id: str
    action_description: str
    port: int
    message_type: int
    data_format: DataFormatType
    data: Dict[str, Any]
    tcp_operation: str


class VDA5050InstantActionsToTCPConverter:
    """VDA5050即时动作转TCP协议转换器"""
    
    # VDA5050动作类型到TCP操作的映射表
    ACTION_MAPPING = {
        'pick': 'JackLoad',           # 托盘抬升
        'drop': 'JackUnload',         # 托盘下降
        'translate': 'Translate',     # 平动
        'turn': 'Turn',               # 转动
        'rotateLoad': 'RotateLoad',   # 托盘旋转
        'softEmc': 'EmergencyStop',   # 软急停
        'startPause': 'Pause',        # 暂停任务
        'stopPause': 'Resume',        # 继续任务
        'cancelOrder': 'Cancel',      # 取消订单
        'reloc': 'Reloc',             # 重定位
        'cancelReloc': 'CancelReloc', # 取消重定位
        'clearErrors': 'ClearErrors'  # 清除错误
    }
    
    # VDA5050动作类型到端口号和报文类型的配置表
    ACTION_CONFIG = {
        'pick': ActionConfig(19206, 3066, DataFormatType.MOVE_TASK_LIST),
        'drop': ActionConfig(19206, 3066, DataFormatType.MOVE_TASK_LIST),
        'startPause': ActionConfig(19206, 3001, DataFormatType.EMPTY_DATA),
        'stopPause': ActionConfig(19206, 3002, DataFormatType.EMPTY_DATA),
        'cancelOrder': ActionConfig(19206, 3003, DataFormatType.EMPTY_DATA),
        'reloc': ActionConfig(19205, 2002, DataFormatType.SINGLE_FIELD),
        'cancelReloc': ActionConfig(19205, 2004, DataFormatType.EMPTY_DATA),
        'clearErrors': ActionConfig(19207, 4009, DataFormatType.SINGLE_FIELD),
        'rotateLoad': ActionConfig(19206, 3057, DataFormatType.SINGLE_FIELD),
        'softEmc': ActionConfig(19210, 6004, DataFormatType.SINGLE_FIELD),
        'turn': ActionConfig(19206, 3056, DataFormatType.SINGLE_FIELD),
        'translate': ActionConfig(19206, 3055, DataFormatType.SINGLE_FIELD)
    }
    
    def __init__(self):
        """初始化转换器"""
        # 创建TCP协议处理器实例，用于统一生成task_id
        self.tcp_protocol = ManufacturerATCPProtocol()
    
    def generate_tcp_task_id(self, base_id: Optional[str] = None, counter: int = 1) -> str:
        """生成TCP协议task_id，使用统一的ID生成逻辑
        
        Args:
            base_id: 基础ID，通常使用headerId
            counter: 计数器
            
        Returns:
            生成的task_id
        """
        if base_id:
            # 重置计数器到指定值，然后生成ID
            original_counter = self.tcp_protocol.task_id_counter
            self.tcp_protocol.task_id_counter = counter
            task_id = self.tcp_protocol.generate_task_id(base_id)
            # 恢复计数器状态
            self.tcp_protocol.task_id_counter = original_counter
            return task_id
        
        # 如果没有baseId，使用默认生成逻辑
        return self.tcp_protocol.generate_task_id()
    
    def convert_single_action(self, action: Dict[str, Any], base_task_id: str = "", 
                            counter: int = 1) -> Optional[TCPActionResult]:
        """转换单个VDA5050即时动作为TCP格式
        
        Args:
            action: VDA5050动作对象
            base_task_id: 基础任务ID
            counter: 计数器
            
        Returns:
            TCP动作转换结果，如果动作不支持则返回None
        """
        action_type = action.get('actionType')
        if not action_type or action_type not in self.ACTION_MAPPING:
            return None
        
        action_config = self.ACTION_CONFIG[action_type]
        tcp_operation = self.ACTION_MAPPING[action_type]
        
        # 根据数据格式类型生成相应的数据结构
        tcp_data = self._generate_tcp_data(action, action_config, base_task_id, counter)
        
        return TCPActionResult(
            action_type=action_type,
            action_id=action.get('actionId', ''),
            action_description=action.get('actionDescription', ''),
            port=action_config.port,
            message_type=action_config.message_type,
            data_format=action_config.data_format,
            data=tcp_data,
            tcp_operation=tcp_operation
        )
    
    def _generate_tcp_data(self, action: Dict[str, Any], config: ActionConfig, 
                          base_task_id: str, counter: int) -> Dict[str, Any]:
        """根据动作配置生成TCP数据
        
        Args:
            action: VDA5050动作对象
            config: 动作配置
            base_task_id: 基础任务ID
            counter: 计数器
            
        Returns:
            TCP数据字典
        """
        action_type = action.get('actionType')
        
        if config.data_format == DataFormatType.MOVE_TASK_LIST:
            # move_task_list格式（pick, drop）
            return {
                "move_task_list": [{
                    "id": "SELF_POSITION",
                    "source_id": "SELF_POSITION",
                    "task_id": self.generate_tcp_task_id(base_task_id, counter),
                    "operation": self.ACTION_MAPPING[action_type]
                }]
            }
        
        elif config.data_format == DataFormatType.EMPTY_DATA:
            # 空数据格式（startPause, stopPause, cancelOrder, cancelReloc）
            return {}
        
        elif config.data_format == DataFormatType.SINGLE_FIELD:
            # 单独字段格式
            return self._generate_single_field_data(action)
        
        return {}
    
    def _generate_single_field_data(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """生成单独字段格式的TCP数据
        
        Args:
            action: VDA5050动作对象
            
        Returns:
            TCP数据字典
        """
        action_type = action.get('actionType')
        tcp_data = {}
        
        if action_type == 'reloc':
            # 重定位动作特殊处理
            action_params = self._parse_action_parameters(action)
            
            if 'isAuto' in action_params:
                tcp_data['isAuto'] = action_params['isAuto']
            if 'home' in action_params:
                tcp_data['home'] = action_params['home']
            if 'length' in action_params and action_params['length'] != '':
                tcp_data['length'] = float(action_params['length'])
            
            # 坐标参数（当isAuto和home都为false时才有效）
            is_auto = action_params.get('isAuto', False)
            home = action_params.get('home', False)
            if not is_auto and not home:
                if 'x' in action_params and action_params['x'] != '':
                    tcp_data['x'] = float(action_params['x'])
                if 'y' in action_params and action_params['y'] != '':
                    tcp_data['y'] = float(action_params['y'])
                if 'angle' in action_params and action_params['angle'] != '':
                    tcp_data['angle'] = float(action_params['angle'])
        
        elif action_type == 'clearErrors':
            # 清除错误动作特殊处理
            action_params = self._parse_action_parameters(action)
            if 'error_codes' in action_params and action_params['error_codes']:
                try:
                    # 尝试解析错误码列表
                    if isinstance(action_params['error_codes'], list):
                        tcp_data['error_codes'] = action_params['error_codes']
                    elif isinstance(action_params['error_codes'], str):
                        # 尝试JSON解析
                        try:
                            error_codes = json.loads(action_params['error_codes'])
                            if isinstance(error_codes, list):
                                tcp_data['error_codes'] = error_codes
                        except json.JSONDecodeError:
                            # 按逗号分割的数字
                            codes = []
                            for code in action_params['error_codes'].split(','):
                                try:
                                    codes.append(int(code.strip()))
                                except ValueError:
                                    pass
                            if codes:
                                tcp_data['error_codes'] = codes
                except Exception:
                    pass
        
        elif action_type == 'translate':
            # 平动动作特殊处理
            action_params = self._parse_action_parameters(action)
            if 'dist' in action_params and action_params['dist'] != '':
                tcp_data['dist'] = float(action_params['dist'])
            if 'vx' in action_params and action_params['vx'] != '':
                tcp_data['vx'] = float(action_params['vx'])
            if 'vy' in action_params and action_params['vy'] != '':
                tcp_data['vy'] = float(action_params['vy'])
            if 'mode' in action_params and action_params['mode'] != '':
                tcp_data['mode'] = int(action_params['mode'])
        
        elif action_type == 'turn':
            # 转动动作特殊处理
            action_params = self._parse_action_parameters(action)
            if 'angle' in action_params and action_params['angle'] != '':
                tcp_data['angle'] = float(action_params['angle'])
            if 'vw' in action_params and action_params['vw'] != '':
                tcp_data['vw'] = float(action_params['vw'])
            if 'mode' in action_params and action_params['mode'] != '':
                tcp_data['mode'] = int(action_params['mode'])
        
        elif action_type == 'rotateLoad':
            # 托盘旋转动作特殊处理
            action_params = self._parse_action_parameters(action)
            if 'increase_spin_angle' in action_params and action_params['increase_spin_angle'] != '':
                tcp_data['increase_spin_angle'] = float(action_params['increase_spin_angle'])
            if 'robot_spin_angle' in action_params and action_params['robot_spin_angle'] != '':
                tcp_data['robot_spin_angle'] = float(action_params['robot_spin_angle'])
            if 'global_spin_angle' in action_params and action_params['global_spin_angle'] != '':
                tcp_data['global_spin_angle'] = float(action_params['global_spin_angle'])
            if 'spin_direction' in action_params and action_params['spin_direction'] != '':
                tcp_data['spin_direction'] = int(action_params['spin_direction'])
        
        elif action_type == 'softEmc':
            # 软急停动作特殊处理
            action_params = self._parse_action_parameters(action)
            if 'status' in action_params:
                status = action_params['status']
                if isinstance(status, str):
                    tcp_data['status'] = status.lower() == 'true'
                else:
                    tcp_data['status'] = bool(status)
        
        return tcp_data
    
    def _parse_action_parameters(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """解析动作参数
        
        Args:
            action: VDA5050动作对象
            
        Returns:
            参数字典
        """
        params = {}
        
        # 从actionParameters中解析参数
        action_parameters = action.get('actionParameters', [])
        if isinstance(action_parameters, list):
            for param in action_parameters:
                if isinstance(param, dict) and 'key' in param and 'value' in param:
                    params[param['key']] = param['value']
        
        # 也支持直接在action对象中的参数
        for key, value in action.items():
            if key not in ['actionId', 'actionType', 'actionDescription', 'blockingType', 'actionParameters']:
                params[key] = value
        
        return params
    
    def convert_vda5050_instant_actions(self, vda_json: Dict[str, Any]) -> Dict[str, Any]:
        """转换VDA5050即时动作消息为TCP协议
        
        Args:
            vda_json: VDA5050即时动作消息JSON对象
            
        Returns:
            转换结果字典
        """
        try:
            # 使用headerId作为task_id的基础部分
            base_task_id = str(vda_json.get('headerId', '')) if vda_json.get('headerId') else ''
            task_id_counter = 1
            action_results = []
            
            # 处理actions数组
            actions = vda_json.get('actions', [])
            if not isinstance(actions, list):
                return {
                    "error": "actions字段必须是数组类型",
                    "note": "请检查VDA5050即时动作消息格式"
                }
            
            for index, action in enumerate(actions):
                if not isinstance(action, dict):
                    continue
                
                result = self.convert_single_action(action, base_task_id, task_id_counter)
                if result:
                    action_results.append(result)
                    task_id_counter += 1
            
            # 如果没有有效的动作
            if not action_results:
                return {
                    "error": "未找到支持的VDA5050动作类型或动作为空",
                    "note": "支持的动作类型: " + ", ".join(self.ACTION_MAPPING.keys())
                }
            
            # 根据动作数量返回相应格式
            if len(action_results) == 1:
                # 单个动作，返回对应格式的数据
                result = action_results[0]
                return result.data
            else:
                # 多个动作，返回动作列表和说明
                instant_actions = []
                for result in action_results:
                    instant_actions.append({
                        "actionType": result.action_type,
                        "actionId": result.action_id,
                        "actionDescription": result.action_description,
                        "port": result.port,
                        "messageType": result.message_type,
                        "dataFormat": result.data_format.value,
                        "tcpOperation": result.tcp_operation,
                        "data": result.data
                    })
                
                return {
                    "instant_actions": instant_actions,
                    "note": "多个即时动作，每个动作需要分别发送到对应端口",
                    "total_actions": len(instant_actions)
                }
        
        except Exception as error:
            return {
                "error": "即时动作转换失败",
                "message": str(error)
            }
    
    def analyze_instant_action_configs(self, vda_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析即时动作配置，用于发送到不同端口
        
        Args:
            vda_json: VDA5050即时动作消息JSON对象
            
        Returns:
            动作配置列表
        """
        configs = []
        actions = vda_json.get('actions', [])
        
        for index, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            
            action_type = action.get('actionType')
            if action_type and action_type in self.ACTION_CONFIG:
                config = self.ACTION_CONFIG[action_type]
                
                configs.append({
                    "actionType": action_type,
                    "actionId": action.get('actionId', ''),
                    "actionDescription": action.get('actionDescription', ''),
                    "port": config.port,
                    "messageType": config.message_type,
                    "dataFormat": config.data_format.value,
                    "tcpOperation": self.ACTION_MAPPING[action_type],
                    "index": index
                })
        
        return configs
    
    def get_supported_actions(self) -> List[str]:
        """获取支持的动作类型列表
        
        Returns:
            支持的动作类型列表
        """
        return list(self.ACTION_MAPPING.keys())
    
    def is_action_supported(self, action_type: str) -> bool:
        """检查动作类型是否支持
        
        Args:
            action_type: 动作类型
            
        Returns:
            是否支持
        """
        return action_type in self.ACTION_MAPPING


# 创建默认转换器实例
instant_actions_converter = VDA5050InstantActionsToTCPConverter()


def convert_vda5050_instant_actions_to_tcp(vda_json: Union[Dict[str, Any], str]) -> str:
    """VDA5050即时动作转TCP协议的便捷函数
    
    Args:
        vda_json: VDA5050即时动作消息，可以是字典或JSON字符串
        
    Returns:
        TCP协议JSON字符串
    """
    try:
        if isinstance(vda_json, str):
            vda_data = json.loads(vda_json)
        else:
            vda_data = vda_json
        
        result = instant_actions_converter.convert_vda5050_instant_actions(vda_data)
        return json.dumps(result, indent=2, ensure_ascii=False)
    
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


def create_sample_vda5050_instant_actions() -> Dict[str, Any]:
    """创建示例VDA5050即时动作消息
    
    Returns:
        示例VDA5050即时动作消息
    """
    return {
        "headerId": 12345,
        "timestamp": "2024-01-15T10:30:00.000Z",
        "version": "2.0.0",
        "manufacturer": "ACME",
        "serialNumber": "AGV001",
        "actions": [
            {
                "actionId": "action_001",
                "actionType": "pick",
                "actionDescription": "抬升托盘",
                "blockingType": "HARD",
                "actionParameters": [
                    {"key": "start_height", "value": 0.0},
                    {"key": "end_height", "value": 0.2}
                ]
            },
            {
                "actionId": "action_002", 
                "actionType": "translate",
                "actionDescription": "平动移动",
                "blockingType": "HARD",
                "actionParameters": [
                    {"key": "dist", "value": 1.5},
                    {"key": "vx", "value": 0.5},
                    {"key": "mode", "value": 1}
                ]
            },
            {
                "actionId": "action_003",
                "actionType": "reloc", 
                "actionDescription": "重定位",
                "blockingType": "HARD",
                "actionParameters": [
                    {"key": "isAuto", "value": False},
                    {"key": "home", "value": False},
                    {"key": "x", "value": 10.5},
                    {"key": "y", "value": 8.2},
                    {"key": "angle", "value": 1.57}
                ]
            }
        ]
    }


if __name__ == "__main__":
    """测试转换功能"""
    print("=== VDA5050即时动作转TCP协议转换器测试 ===\n")
    
    # 创建示例数据
    sample_data = create_sample_vda5050_instant_actions()
    print("示例VDA5050即时动作消息:")
    print(json.dumps(sample_data, indent=2, ensure_ascii=False))
    print("\n" + "="*50 + "\n")
    
    # 测试转换
    result = convert_vda5050_instant_actions_to_tcp(sample_data)
    print("转换后的TCP协议:")
    print(result)
    print("\n" + "="*50 + "\n")
    
    # 测试动作配置分析
    converter = VDA5050InstantActionsToTCPConverter()
    configs = converter.analyze_instant_action_configs(sample_data)
    print("动作配置分析:")
    for config in configs:
        print(f"- {config['actionType']}: 端口{config['port']}, 报文类型{config['messageType']}, 格式{config['dataFormat']}")
    
    print(f"\n支持的动作类型: {', '.join(converter.get_supported_actions())}")
