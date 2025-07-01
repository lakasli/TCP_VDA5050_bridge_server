#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050订单消息转TCP协议转换器
基于网页前端的转换逻辑，将VDA5050格式转换为TCP移动任务列表格式
"""

import json
import time
import math
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from .manufacturer_a import ManufacturerATCPProtocol


class VDA5050ToTCPConverter:
    """VDA5050订单消息转TCP协议转换器"""
    
    # VDA5050动作类型到TCP操作的映射表
    VDA5050_TO_TCP_ACTION_MAPPING = {
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
    INSTANT_ACTION_CONFIG = {
        'pick': {'port': 19206, 'message_type': 3066},           # 托盘抬升
        'drop': {'port': 19206, 'message_type': 3066},           # 托盘下降
        'startPause': {'port': 19206, 'message_type': 3001},     # 暂停任务
        'stopPause': {'port': 19206, 'message_type': 3002},      # 继续任务
        'cancelOrder': {'port': 19206, 'message_type': 3003},    # 取消订单
        'reloc': {'port': 19205, 'message_type': 2002},          # 重定位
        'cancelReloc': {'port': 19205, 'message_type': 2004},    # 取消重定位
        'clearErrors': {'port': 19207, 'message_type': 4009},    # 清除错误
        'rotateLoad': {'port': 19206, 'message_type': 3057},     # 托盘旋转
        'softEmc': {'port': 19210, 'message_type': 6004},        # 软急停
        'turn': {'port': 19206, 'message_type': 3056},           # 转动
        'translate': {'port': 19206, 'message_type': 3055}       # 平动
    }
    
    def __init__(self):
        # 创建TCP协议处理器实例，用于统一生成task_id
        self.tcp_protocol = ManufacturerATCPProtocol()
    
    def generate_tcp_task_id(self, base_id: str, counter: int) -> str:
        """生成TCP协议task_id，使用统一的ID生成逻辑"""
        if base_id and base_id.strip():
            # 重置计数器到指定值，然后生成ID
            original_counter = self.tcp_protocol.task_id_counter
            self.tcp_protocol.task_id_counter = counter
            task_id = self.tcp_protocol.generate_task_id(base_id)
            # 恢复计数器状态
            self.tcp_protocol.task_id_counter = original_counter
            return task_id
        
        # 如果没有baseId，使用默认生成逻辑
        return self.tcp_protocol.generate_task_id()
    
    def extract_operation_from_actions(self, actions: List[Dict[str, Any]]) -> Optional[str]:
        """从VDA5050动作数组中提取对应的TCP操作"""
        if not actions or not isinstance(actions, list):
            return None
        
        # 遍历actions数组，查找支持的动作类型
        for action in actions:
            if isinstance(action, dict) and action.get('actionType'):
                action_type = action['actionType']
                if action_type in self.VDA5050_TO_TCP_ACTION_MAPPING:
                    return self.VDA5050_TO_TCP_ACTION_MAPPING[action_type]
        
        return None
    
    def extract_all_operations_from_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从VDA5050动作数组中提取所有对应的TCP操作"""
        if not actions or not isinstance(actions, list):
            return []
        
        operations = []
        for action in actions:
            if isinstance(action, dict) and action.get('actionType'):
                action_type = action['actionType']
                if action_type in self.VDA5050_TO_TCP_ACTION_MAPPING:
                    operations.append({
                        'operation': self.VDA5050_TO_TCP_ACTION_MAPPING[action_type],
                        'action_id': action.get('actionId', ''),
                        'action_description': action.get('actionDescription', '')
                    })
        
        return operations
    
    def convert_vda5050_order_to_tcp_move_task_list(self, vda_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        将VDA5050订单协议转换为TCP移动任务列表协议
        按照"路径移动，原地动作，路径移动"的模式进行转换
        """
        try:
            tcp_protocol = {
                "move_task_list": []
            }
            
            # 创建节点动作映射（支持多个动作）
            node_actions_map = {}
            if 'nodes' in vda_json and isinstance(vda_json['nodes'], list):
                for node in vda_json['nodes']:
                    if isinstance(node, dict) and 'actions' in node:
                        node_id = node.get('nodeId')
                        if node_id and isinstance(node['actions'], list) and len(node['actions']) > 0:
                            operations = self.extract_all_operations_from_actions(node['actions'])
                            if operations:
                                node_actions_map[node_id] = operations
            
            # 获取orderId作为task_id前缀
            order_id_prefix = vda_json.get('orderId', 'DEFAULT_ORDER')
            task_id_counter = 1  # 从1开始计数
            
            # 根据edges的sequenceId排序，确定路径执行顺序
            edges = vda_json.get('edges', [])
            if isinstance(edges, list):
                sorted_edges = sorted(edges, key=lambda x: x.get('sequenceId', 0))
            else:
                sorted_edges = []
            
            # 按边的顺序处理路径
            for edge in sorted_edges:
                if not isinstance(edge, dict):
                    continue
                
                start_node_id = edge.get('startNodeId')
                end_node_id = edge.get('endNodeId')
                
                if not start_node_id or not end_node_id:
                    continue
                
                # 1. 检查起始节点是否有动作需要执行
                start_node_actions = node_actions_map.get(start_node_id)
                if start_node_actions:
                    # 为每个动作创建一个TCP任务
                    for action_info in start_node_actions:
                        tcp_protocol['move_task_list'].append({
                            'source_id': 'SELF_POSITION',
                            'id': 'SELF_POSITION',
                            'task_id': self.generate_tcp_task_id(order_id_prefix, task_id_counter),
                            'operation': action_info['operation']
                        })
                        task_id_counter += 1
                    # 标记已处理，避免重复
                    del node_actions_map[start_node_id]
                
                # 2. 添加路径移动任务
                move_task = {
                    'source_id': start_node_id,
                    'id': end_node_id,
                    'task_id': self.generate_tcp_task_id(order_id_prefix, task_id_counter)
                }
                
                # 检查边本身是否有动作
                edge_operations = self.extract_all_operations_from_actions(edge.get('actions', []))
                if edge_operations:
                    # 如果边有动作，先添加移动任务（不带动作）
                    tcp_protocol['move_task_list'].append(move_task)
                    task_id_counter += 1
                    
                    # 然后为每个边动作添加原地执行任务
                    for action_info in edge_operations:
                        tcp_protocol['move_task_list'].append({
                            'source_id': 'SELF_POSITION',
                            'id': 'SELF_POSITION',
                            'task_id': self.generate_tcp_task_id(order_id_prefix, task_id_counter),
                            'operation': action_info['operation']
                        })
                        task_id_counter += 1
                else:
                    # 如果边没有动作，直接添加移动任务
                    tcp_protocol['move_task_list'].append(move_task)
                    task_id_counter += 1
            
            # 3. 处理路径结束后的节点动作
            # 找到最后一个边的目标节点，检查是否有动作
            if sorted_edges:
                last_edge = sorted_edges[-1]
                if isinstance(last_edge, dict):
                    end_node_id = last_edge.get('endNodeId')
                    if end_node_id and end_node_id in node_actions_map:
                        end_node_actions = node_actions_map[end_node_id]
                        # 为每个动作创建一个TCP任务
                        for action_info in end_node_actions:
                            tcp_protocol['move_task_list'].append({
                                'source_id': 'SELF_POSITION',
                                'id': 'SELF_POSITION',
                                'task_id': self.generate_tcp_task_id(order_id_prefix, task_id_counter),
                                'operation': action_info['operation']
                            })
                            task_id_counter += 1
                        del node_actions_map[end_node_id]
            
            # 4. 处理剩余的独立节点动作（没有关联到任何边的节点）
            for node_id, operations in node_actions_map.items():
                # 为每个动作创建一个TCP任务
                for action_info in operations:
                    tcp_protocol['move_task_list'].append({
                        'source_id': 'SELF_POSITION',
                        'id': 'SELF_POSITION',
                        'task_id': self.generate_tcp_task_id(order_id_prefix, task_id_counter),
                        'operation': action_info['operation']
                    })
                    task_id_counter += 1
            
            return tcp_protocol
            
        except Exception as e:
            return {
                'error': '转换失败',
                'message': str(e)
            }
    
    def convert_vda5050_instant_actions_to_tcp(self, vda_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        将VDA5050即时动作协议转换为TCP协议
        根据端口和报文类型定制格式
        """
        try:
            # 使用headerId作为task_id的基础部分
            base_task_id = str(vda_json.get('headerId', '')) if vda_json.get('headerId') else ''
            task_id_counter = 1
            action_results = []
            
            # 处理actions数组，收集有效的动作
            actions = vda_json.get('actions', [])
            if isinstance(actions, list):
                for action in actions:
                    if not isinstance(action, dict) or not action.get('actionType'):
                        continue
                    
                    action_type = action['actionType']
                    if action_type not in self.VDA5050_TO_TCP_ACTION_MAPPING:
                        continue
                    
                    action_config = self.INSTANT_ACTION_CONFIG.get(action_type)
                    if not action_config:
                        continue
                    
                    tcp_operation = self.VDA5050_TO_TCP_ACTION_MAPPING[action_type]
                    
                    # 根据端口号和报文类型决定数据格式
                    if (action_config['port'] == 19206 and 
                        action_config['message_type'] == 3066):
                        # 端口19206，报文3066 - 使用move_task_list格式（pick, drop）
                        action_result = {
                            'type': 'move_task_list',
                            'port': action_config['port'],
                            'message_type': action_config['message_type'],
                            'data': {
                                'move_task_list': [{
                                    'id': 'SELF_POSITION',
                                    'source_id': 'SELF_POSITION',
                                    'task_id': self.generate_tcp_task_id(base_task_id, task_id_counter),
                                    'operation': tcp_operation
                                }]
                            }
                        }
                    elif action_type in ['startPause', 'stopPause', 'cancelOrder', 'cancelReloc']:
                        # 特定动作 - 数据区无内容，只需要端口号和报文类型
                        action_result = {
                            'type': 'empty_data',
                            'port': action_config['port'],
                            'message_type': action_config['message_type'],
                            'data': {},
                            'action_type': action_type,
                            'description': f"{action_type}（数据区为空）"
                        }
                    else:
                        # 其他动作 - 使用单独字段格式
                        tcp_data = {}
                        
                        # 特殊处理reloc动作，添加重定位参数
                        if action_type == 'reloc':
                            if 'isAuto' in action:
                                tcp_data['isAuto'] = action['isAuto']
                            if 'home' in action:
                                tcp_data['home'] = action['home']
                            if 'length' in action and action['length'] != '':
                                tcp_data['length'] = float(action['length'])
                            
                            # 坐标参数（当isAuto和home都为false时才有效）
                            if not action.get('isAuto', False) and not action.get('home', False):
                                if 'x' in action and action['x'] != '':
                                    tcp_data['x'] = float(action['x'])
                                if 'y' in action and action['y'] != '':
                                    tcp_data['y'] = float(action['y'])
                                if 'angle' in action and action['angle'] != '':
                                    tcp_data['angle'] = float(action['angle'])
                        
                        # 处理其他动作的参数
                        elif action_type in ['translate', 'turn', 'rotateLoad']:
                            # 这些动作可能有特定的参数
                            for key in ['distance', 'angle', 'speed', 'direction']:
                                if key in action and action[key] != '':
                                    try:
                                        tcp_data[key] = float(action[key])
                                    except (ValueError, TypeError):
                                        tcp_data[key] = action[key]
                        
                        action_result = {
                            'type': 'single_field',
                            'port': action_config['port'],
                            'message_type': action_config['message_type'],
                            'data': tcp_data,
                            'action_type': action_type
                        }
                    
                    action_results.append(action_result)
                    task_id_counter += 1
            
            return action_results
            
        except Exception as e:
            return [{
                'error': '即时动作转换失败',
                'message': str(e)
            }]
    
    def convert_order_message_to_tcp(self, order_message) -> Dict[str, Any]:
        """
        将VDA5050 OrderMessage对象转换为TCP格式
        
        Args:
            order_message: VDA5050 OrderMessage实例
            
        Returns:
            Dict[str, Any]: TCP格式的数据
        """
        try:
            # 转换为字典格式
            if hasattr(order_message, 'get_message_dict'):
                vda_dict = order_message.get_message_dict()
            else:
                vda_dict = order_message
            
            return self.convert_vda5050_order_to_tcp_move_task_list(vda_dict)
            
        except Exception as e:
            return {
                'error': '订单消息转换失败',
                'message': str(e)
            }


def create_sample_tcp_task_list() -> Dict[str, Any]:
    """创建示例TCP移动任务列表"""
    return {
        "move_task_list": [
            {
                "source_id": "START_POINT",
                "id": "PICK_POINT",
                "task_id": "TASK_001"
            },
            {
                "source_id": "SELF_POSITION",
                "id": "SELF_POSITION",
                "task_id": "TASK_002",
                "operation": "JackLoad"
            },
            {
                "source_id": "PICK_POINT",
                "id": "DROP_POINT",
                "task_id": "TASK_003"
            },
            {
                "source_id": "SELF_POSITION",
                "id": "SELF_POSITION",
                "task_id": "TASK_004",
                "operation": "JackUnload"
            }
        ]
    }


def create_sample_instant_action_tcp() -> List[Dict[str, Any]]:
    """创建示例TCP即时动作"""
    return [
        {
            'type': 'move_task_list',
            'port': 19206,
            'message_type': 3066,
            'data': {
                'move_task_list': [{
                    'id': 'SELF_POSITION',
                    'source_id': 'SELF_POSITION',
                    'task_id': 'INSTANT_12345_1',
                    'operation': 'JackLoad'
                }]
            }
        },
        {
            'type': 'empty_data',
            'port': 19206,
            'message_type': 3001,
            'data': {},
            'action_type': 'startPause',
            'description': 'startPause（数据区为空）'
        }
    ]
