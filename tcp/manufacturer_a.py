#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
厂商A TCP协议处理模块
负责TCP协议数据包的构造、解析和拼接
包括IP地址、端口号、报文类型的处理
"""

import json
import time
import struct
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class ManufacturerATCPProtocol:
    """厂商A TCP协议处理类"""
    
    # VDA5050动作类型到TCP协议映射配置
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
        'pick': {'port': 19206, 'messageType': 3066},           # 托盘抬升
        'drop': {'port': 19206, 'messageType': 3066},           # 托盘下降
        'startPause': {'port': 19206, 'messageType': 3001},     # 暂停任务
        'stopPause': {'port': 19206, 'messageType': 3002},      # 继续任务
        'cancelOrder': {'port': 19206, 'messageType': 3003},    # 取消订单
        'reloc': {'port': 19205, 'messageType': 2002},          # 重定位
        'cancelReloc': {'port': 19205, 'messageType': 2004},    # 取消重定位
        'clearErrors': {'port': 19207, 'messageType': 4009},    # 清除错误
        'rotateLoad': {'port': 19206, 'messageType': 3057},     # 托盘旋转
        'softEmc': {'port': 19210, 'messageType': 6004},        # 软急停
        'turn': {'port': 19206, 'messageType': 3056},           # 转动
        'translate': {'port': 19206, 'messageType': 3055}       # 平动
    }
    
    def __init__(self):
        """初始化TCP协议处理器"""
        self.task_id_counter = 1
        self.sequence_counter = 1
        
    def build_tcp_packet(self, vehicle_id: str, ip_address: str, port: int, 
                        message_type: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建完整的TCP数据包
        
        Args:
            vehicle_id: 车辆ID
            ip_address: 目标IP地址
            port: 目标端口号
            message_type: 报文类型
            data: 数据内容
            
        Returns:
            Dict: 包含所有信息的TCP数据包
        """
        try:
            tcp_packet = {
                # 网络信息
                'target_info': {
                    'vehicle_id': vehicle_id,
                    'ip_address': ip_address,
                    'port': port
                },
                # 协议信息
                'protocol_info': {
                    'messageType': message_type,
                    'timestamp': int(time.time() * 1000),  # 毫秒时间戳
                    'sequence': self._get_next_sequence(),
                    'protocol_version': '1.0'
                },
                # 数据内容
                'data': data
            }
            
            logger.info(f"📦 构建TCP数据包 - 车辆: {vehicle_id}, 地址: {ip_address}:{port}, 类型: {message_type}")
            return tcp_packet
            
        except Exception as e:
            logger.error(f"❌ 构建TCP数据包失败: {e}")
            return {'error': str(e)}
    
    def create_tcp_message_json(self, message_type: int, data: Dict[str, Any]) -> str:
        """
        创建TCP协议JSON消息
        
        Args:
            message_type: 报文类型
            data: 数据内容
            
        Returns:
            str: JSON格式的消息字符串
        """
        try:
            tcp_message = {
                'messageType': message_type,
                'timestamp': int(time.time() * 1000),
                'data': data
            }
            
            # 移除JSON中的空格以减少数据包大小
            json_str = json.dumps(tcp_message, ensure_ascii=False, separators=(',', ':'))
            logger.debug(f"📝 创建TCP JSON消息 - 类型: {message_type}, 长度: {len(json_str)}")
            return json_str
            
        except Exception as e:
            logger.error(f"❌ 创建TCP JSON消息失败: {e}")
            return json.dumps({'error': str(e)})
    
    def create_tcp_message_bytes(self, message_type: int, data: Dict[str, Any]) -> bytes:
        """
        创建TCP协议字节消息
        
        Args:
            message_type: 报文类型
            data: 数据内容
            
        Returns:
            bytes: 编码后的消息字节流
        """
        try:
            json_str = self.create_tcp_message_json(message_type, data)
            message_bytes = json_str.encode('utf-8')
            
            logger.debug(f"🔢 创建TCP字节消息 - 类型: {message_type}, 字节数: {len(message_bytes)}")
            return message_bytes
            
        except Exception as e:
            logger.error(f"❌ 创建TCP字节消息失败: {e}")
            return str(e).encode('utf-8')
    
    def create_binary_tcp_packet(self, message_type: int, data: Dict[str, Any], 
                                sync_header: int = 0x5A, version: int = 0x01) -> bytes:
        """
        创建完整的二进制TCP数据包（包含16字节包头）
        
        Args:
            message_type: 报文类型
            data: 数据内容
            sync_header: 同步头（默认0x5A）
            version: 版本号（默认0x01）
            
        Returns:
            bytes: 完整的二进制TCP数据包
        """
        try:
            # 将数据转换为JSON字符串，移除不必要的空格
            data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            data_bytes = data_json.encode('utf-8')
            data_length = len(data_bytes)
            
            # 获取序列号
            sequence = self._get_next_sequence()
            
            # 构建16字节包头
            packet = bytearray(16)
            packet[0] = sync_header & 0xFF                    # 同步头 (1字节)
            packet[1] = version & 0xFF                        # 版本 (1字节)
            packet[2:4] = sequence.to_bytes(2, 'big')         # 序列号 (2字节，大端序)
            packet[4:8] = data_length.to_bytes(4, 'big')      # 数据长度 (4字节，大端序)
            packet[8:10] = message_type.to_bytes(2, 'big')    # 消息类型 (2字节，大端序)
            packet[10:16] = b'\x00\x00\x00\x00\x00\x00'       # 保留字段，已初始化为0
            
            # 添加数据内容
            packet.extend(data_bytes)
            
            logger.info(f"🔧 构建二进制TCP包 - 类型: {message_type}, 序列: {sequence}, 数据长度: {data_length}")
            logger.debug(f"   十六进制数据: {packet.hex().upper()}")
            
            return bytes(packet)
            
        except Exception as e:
            logger.error(f"❌ 创建二进制TCP数据包失败: {e}")
            return b''
    
    def create_binary_tcp_packet_hex(self, message_type: int, hex_data: str, 
                                     sync_header: int = 0x5A, version: int = 0x01) -> bytes:
        """
        创建基于十六进制数据的二进制TCP数据包（与JavaScript版本保持一致）
        
        Args:
            message_type: 报文类型
            hex_data: 十六进制字符串数据（如："41 42 43" 或 "414243"）
            sync_header: 同步头（默认0x5A）
            version: 版本号（默认0x01）
            
        Returns:
            bytes: 完整的二进制TCP数据包
        """
        try:
            # 清理十六进制数据，移除所有空格
            clean_hex_data = hex_data.replace(' ', '').replace('\t', '').replace('\n', '')
            
            # 验证十六进制格式
            if not all(c in '0123456789ABCDEFabcdef' for c in clean_hex_data):
                raise ValueError(f"无效的十六进制数据: {hex_data}")
            
            # 确保是偶数长度（每两个字符代表一个字节）
            if len(clean_hex_data) % 2 != 0:
                clean_hex_data = '0' + clean_hex_data
            
            # 计算数据区长度（字节数）
            data_length = len(clean_hex_data) // 2
            
            # 将十六进制字符串转换为字节
            data_bytes = bytes.fromhex(clean_hex_data)
            
            # 获取序列号
            sequence = self._get_next_sequence()
            
            # 构建16字节包头
            packet = bytearray(16)
            packet[0] = sync_header & 0xFF                    # 同步头 (1字节)
            packet[1] = version & 0xFF                        # 版本 (1字节)
            packet[2:4] = sequence.to_bytes(2, 'big')         # 序列号 (2字节，大端序)
            packet[4:8] = data_length.to_bytes(4, 'big')      # 数据长度 (4字节，大端序)
            packet[8:10] = message_type.to_bytes(2, 'big')    # 消息类型 (2字节，大端序)
            packet[10:16] = b'\x00\x00\x00\x00\x00\x00'       # 保留字段
            
            # 添加数据内容
            packet.extend(data_bytes)
            
            logger.info(f"🔧 构建十六进制二进制TCP包 - 类型: {message_type}, 序列: {sequence}, 数据长度: {data_length}")
            logger.debug(f"   原始十六进制数据: {clean_hex_data}")
            logger.debug(f"   完整数据包: {packet.hex().upper()}")
            
            return bytes(packet)
            
        except Exception as e:
            logger.error(f"❌ 创建十六进制二进制TCP数据包失败: {e}")
            return b''
    
    def parse_tcp_packet(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        解析TCP数据包
        
        Args:
            data: 原始字节数据
            
        Returns:
            Dict: 解析后的数据包信息，如果解析失败返回None
        """
        try:
            if len(data) < 16:  # 最小包头长度检查
                logger.warning(f"⚠️  数据包太短，长度: {len(data)}")
                return None
            
            # 尝试直接解析JSON格式
            try:
                json_str = data.decode('utf-8')
                parsed_data = json.loads(json_str)
                
                result = {
                    'format': 'json',
                    'message_type': parsed_data.get('messageType', 0),
                    'timestamp': parsed_data.get('timestamp', 0),
                    'data': parsed_data.get('data', {}),
                    'raw_json': parsed_data
                }
                
                logger.debug(f"📋 解析JSON格式TCP包 - 类型: {result['message_type']}")
                return result
                
            except (UnicodeDecodeError, json.JSONDecodeError):
                # 如果不是JSON格式，尝试解析二进制格式
                return self._parse_binary_packet(data)
                
        except Exception as e:
            logger.error(f"❌ 解析TCP数据包失败: {e}")
            return None
    
    def _parse_binary_packet(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        解析二进制格式的TCP数据包
        
        Args:
            data: 原始字节数据
            
        Returns:
            Dict: 解析后的数据包信息
        """
        try:
            if len(data) < 16:
                return None
            
            # 解析包头 (16字节)
            sync_header = data[0]
            version = data[1]
            sequence = int.from_bytes(data[2:4], 'big')
            data_length = int.from_bytes(data[4:8], 'big')
            message_type = int.from_bytes(data[8:10], 'big')
            reserved = data[10:16]
            
            # 提取数据部分
            payload_data = data[16:16+data_length] if len(data) >= 16 + data_length else data[16:]
            
            # 尝试解析JSON数据
            payload_json = None
            payload_str = None
            
            if payload_data:
                try:
                    payload_str = payload_data.decode('utf-8')
                    payload_json = json.loads(payload_str)
                except:
                    payload_str = payload_data.decode('utf-8', errors='ignore')
            
            result = {
                'format': 'binary',
                'sync_header': sync_header,
                'version': version,
                'sequence': sequence,
                'data_length': data_length,
                'message_type': message_type,
                'reserved': reserved.hex(),
                'payload': payload_json or payload_str,
                'raw_payload': payload_data.hex() if payload_data else None
            }
            
            logger.debug(f"📋 解析二进制TCP包 - 类型: {message_type}, 序列: {sequence}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 解析二进制TCP包失败: {e}")
            return None
    
    def get_action_config(self, action_type: str) -> Optional[Dict[str, Any]]:
        """
        获取动作类型对应的配置信息
        
        Args:
            action_type: VDA5050动作类型
            
        Returns:
            Dict: 包含端口和消息类型的配置信息
        """
        config = self.INSTANT_ACTION_CONFIG.get(action_type)
        if config:
            tcp_operation = self.VDA5050_TO_TCP_ACTION_MAPPING.get(action_type)
            result = config.copy()
            result['tcp_operation'] = tcp_operation
            result['action_type'] = action_type
            logger.debug(f"🔍 获取动作配置 - {action_type}: 端口={config['port']}, 类型={config['messageType']}")
            return result
        else:
            logger.warning(f"⚠️  未找到动作类型配置: {action_type}")
            return None
    
    def build_robot_identification_message(self, vehicle_id: str, ip_address: str, 
                                         manufacturer: str = "SEER", 
                                         model: str = "AGV", version: str = "1.0",
                                         company: str = "VDA5050") -> Dict[str, Any]:
        """
        构建机器人标识消息
        
        Args:
            vehicle_id: 车辆ID
            ip_address: IP地址
            manufacturer: 制造商
            model: 型号
            version: 版本
            company: 公司
            
        Returns:
            Dict: 标识消息数据包
        """
        identification = {
            'messageType': 9001,  # 标识消息类型
            'timestamp': int(time.time() * 1000),
            'robot_info': {
                'vehicle_id': vehicle_id,
                'ip_address': ip_address,
                'manufacturer': manufacturer,
                'model': model,
                'version': version,
                'company': company
            }
        }
        
        logger.info(f"🆔 构建机器人标识消息 - 车辆: {vehicle_id}, IP: {ip_address}")
        return identification
    
    def build_response_message(self, original_message_type: int, robot_id: str, 
                              port: int, status: str = "received") -> Dict[str, Any]:
        """
        构建响应消息
        
        Args:
            original_message_type: 原始消息类型
            robot_id: 机器人ID
            port: 端口号
            status: 状态
            
        Returns:
            Dict: 响应消息数据包
        """
        response = {
            'messageType': 9200,  # 确认消息类型
            'timestamp': int(time.time() * 1000),
            'data': {
                'status': status,
                'original_message_type': original_message_type,
                'robot_id': robot_id,
                'port': port
            }
        }
        
        logger.debug(f"📤 构建响应消息 - 机器人: {robot_id}, 端口: {port}, 状态: {status}")
        return response
    
    def extract_network_info(self, tcp_packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        从TCP数据包中提取网络信息
        
        Args:
            tcp_packet: TCP数据包
            
        Returns:
            Dict: 网络信息（IP地址、端口号等）
        """
        target_info = tcp_packet.get('target_info', {})
        
        network_info = {
            'vehicle_id': target_info.get('vehicle_id', ''),
            'ip_address': target_info.get('ip_address', ''),
            'port': target_info.get('port', 0),
            'message_type': tcp_packet.get('protocol_info', {}).get('messageType', 0)
        }
        
        logger.debug(f"🌐 提取网络信息 - IP: {network_info['ip_address']}:{network_info['port']}")
        return network_info
    
    def validate_tcp_packet(self, tcp_packet: Dict[str, Any]) -> Tuple[bool, str]:
        """
        验证TCP数据包的有效性
        
        Args:
            tcp_packet: TCP数据包
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            # 检查必需字段
            if 'target_info' not in tcp_packet:
                return False, "缺少target_info字段"
            
            if 'protocol_info' not in tcp_packet:
                return False, "缺少protocol_info字段"
            
            target_info = tcp_packet['target_info']
            protocol_info = tcp_packet['protocol_info']
            
            # 验证网络信息
            if not target_info.get('ip_address'):
                return False, "IP地址不能为空"
            
            if not isinstance(target_info.get('port'), int) or target_info.get('port') <= 0:
                return False, "端口号必须是正整数"
            
            # 验证协议信息
            if not isinstance(protocol_info.get('messageType'), int):
                return False, "消息类型必须是整数"
            
            logger.debug(f"✅ TCP数据包验证通过")
            return True, "验证通过"
            
        except Exception as e:
            error_msg = f"验证TCP数据包时出错: {e}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def generate_task_id(self, base_id: str = '') -> str:
        """
        生成任务ID
        
        Args:
            base_id: 基础ID
            
        Returns:
            str: 生成的任务ID
        """
        if base_id:
            task_id = f"{base_id}_{self.task_id_counter}"
        else:
            timestamp = str(int(time.time()))
            task_id = f"TASK_{timestamp}_{self.task_id_counter}"
        
        self.task_id_counter += 1
        logger.debug(f"🔢 生成任务ID: {task_id}")
        return task_id
    
    def _get_next_sequence(self) -> int:
        """获取下一个序列号"""
        seq = self.sequence_counter
        self.sequence_counter += 1
        if self.sequence_counter > 65535:  # 16位序列号
            self.sequence_counter = 1
        return seq
    
    def get_supported_actions(self) -> List[str]:
        """
        获取支持的动作类型列表
        
        Returns:
            List[str]: 支持的动作类型
        """
        return list(self.VDA5050_TO_TCP_ACTION_MAPPING.keys())
    
    def get_port_for_action(self, action_type: str) -> Optional[int]:
        """
        获取动作类型对应的端口号
        
        Args:
            action_type: 动作类型
            
        Returns:
            int: 端口号，如果不支持返回None
        """
        config = self.INSTANT_ACTION_CONFIG.get(action_type)
        return config['port'] if config else None
    
    def get_message_type_for_action(self, action_type: str) -> Optional[int]:
        """
        获取动作类型对应的消息类型
        
        Args:
            action_type: 动作类型
            
        Returns:
            int: 消息类型，如果不支持返回None
        """
        config = self.INSTANT_ACTION_CONFIG.get(action_type)
        return config['messageType'] if config else None


# 实用函数
def create_tcp_protocol_handler() -> ManufacturerATCPProtocol:
    """
    创建TCP协议处理器实例
    
    Returns:
        ManufacturerATCPProtocol: TCP协议处理器实例
    """
    return ManufacturerATCPProtocol()


def build_simple_tcp_message(vehicle_id: str, ip_address: str, port: int, 
                            message_type: int, data: Dict[str, Any]) -> bytes:
    """
    构建简单的TCP消息（便捷函数）
    
    Args:
        vehicle_id: 车辆ID
        ip_address: IP地址
        port: 端口号
        message_type: 消息类型
        data: 数据内容
        
    Returns:
        bytes: TCP消息字节流
    """
    handler = create_tcp_protocol_handler()
    return handler.create_tcp_message_bytes(message_type, data)


def build_hex_tcp_packet(message_type: int, hex_data: str, 
                        sync_header: int = 0x5A, version: int = 0x01) -> bytes:
    """
    构建基于十六进制数据的TCP数据包（便捷函数，与JavaScript版本兼容）
    
    Args:
        message_type: 消息类型
        hex_data: 十六进制字符串数据
        sync_header: 同步头（默认0x5A）
        version: 版本号（默认0x01）
        
    Returns:
        bytes: TCP消息字节流
    """
    handler = create_tcp_protocol_handler()
    return handler.create_binary_tcp_packet_hex(message_type, hex_data, sync_header, version)


def parse_tcp_message(data: bytes) -> Optional[Dict[str, Any]]:
    """
    解析TCP消息（便捷函数）
    
    Args:
        data: 原始字节数据
        
    Returns:
        Dict: 解析后的消息，如果失败返回None
    """
    handler = create_tcp_protocol_handler()
    return handler.parse_tcp_packet(data)
