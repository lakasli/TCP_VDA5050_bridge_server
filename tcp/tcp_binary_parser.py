#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP二进制协议解析器
基于vda5050_editor.html的设计思路实现
"""

import struct
import json
import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)

class TCPBinaryParser:
    """TCP二进制协议解析器"""
    
    # 协议常量 - 统一使用0x5A作为同步头
    SYNC_HEADER = 0x5A  # 同步头：0x5A
    DEFAULT_VERSION = 0x01
    RESERVED_BYTES = b'\x00\x00\x00\x00\x00\x00'
    
    def __init__(self):
        self.sequence_counter = 0
        # 添加调试信息
        logger.info(f"TCPBinaryParser初始化，同步头配置: 0x{self.SYNC_HEADER:02X}")
        
    def hex_to_string(self, hex_data: str) -> str:
        """
        将16进制字符串转换为可读字符串
        只转换可打印的ASCII字符，其他字符用点表示
        """
        try:
            # 移除空格并验证16进制格式
            clean_hex = hex_data.replace(' ', '').replace('\n', '').replace('\r', '')
            if not all(c in '0123456789ABCDEFabcdef' for c in clean_hex):
                return hex_data
            
            result = ''
            for i in range(0, len(clean_hex), 2):
                if i + 1 < len(clean_hex):
                    hex_byte = clean_hex[i:i+2]
                    char_code = int(hex_byte, 16)
                    # 只转换可打印的ASCII字符
                    if 32 <= char_code <= 126:
                        result += chr(char_code)
                    else:
                        result += '.'
            return result
        except Exception as e:
            logger.error(f"16进制转字符串失败: {e}")
            return hex_data
    
    def parse_tcp_packet(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        解析TCP数据包
        返回解析后的数据字典
        """
        try:
            if len(data) < 16:  # 最小包长度：头部16字节
                logger.warning(f"数据包太短，长度: {len(data)}")
                return None
            
            # 解析包头
            sync_header = data[0]
            version = data[1]
            sequence = struct.unpack('>H', data[2:4])[0]  # 大端序
            data_length = struct.unpack('>I', data[4:8])[0]  # 大端序
            message_type = struct.unpack('>H', data[8:10])[0]  # 大端序
            reserved = data[10:16]
            
            # 验证同步头
            if sync_header != self.SYNC_HEADER:
                logger.warning(f"同步头不正确: {sync_header:02X}, 期望: {self.SYNC_HEADER:02X}")
                return None
            
            # 验证数据长度
            if len(data) < 16 + data_length:
                logger.warning(f"数据包不完整，期望长度: {16 + data_length}, 实际长度: {len(data)}")
                return None
            
            # 提取数据区
            payload = data[16:16+data_length]
            
            # 尝试解析数据区
            parsed_data = self._parse_payload(payload, message_type)
            
            return {
                'sync_header': f'{sync_header:02X}',
                'version': f'{version:02X}',
                'sequence': sequence,
                'data_length': data_length,
                'message_type': message_type,
                'reserved': reserved.hex().upper(),
                'payload_raw': payload.hex().upper(),
                'payload_parsed': parsed_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"解析TCP数据包失败: {e}")
            return None
    
    def _parse_payload(self, payload: bytes, message_type: int) -> Dict[str, Any]:
        """
        解析数据区内容
        根据消息类型进行不同的解析
        """
        try:
            # 首先尝试作为JSON解析
            try:
                json_str = payload.decode('utf-8')
                return {
                    'type': 'json',
                    'data': json.loads(json_str),
                    'raw_text': json_str
                }
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            
            # 尝试作为文本解析
            try:
                text_str = payload.decode('utf-8')
                if all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in text_str):
                    return {
                        'type': 'text',
                        'data': text_str,
                        'raw_text': text_str
                    }
            except UnicodeDecodeError:
                pass
            
            # 作为二进制数据处理
            hex_str = payload.hex().upper()
            readable_text = self.hex_to_string(hex_str)
            
            return {
                'type': 'binary',
                'data': {
                    'hex': hex_str,
                    'readable': readable_text,
                    'length': len(payload)
                },
                'raw_text': f'Binary data ({len(payload)} bytes)'
            }
            
        except Exception as e:
            logger.error(f"解析数据区失败: {e}")
            return {
                'type': 'error',
                'data': payload.hex().upper(),
                'raw_text': f'Parse error: {str(e)}'
            }
    
    def build_tcp_packet(self, message_type: int, data: str, version: int = None) -> bytes:
        """
        构建TCP数据包
        """
        try:
            if version is None:
                version = self.DEFAULT_VERSION
            
            # 处理数据
            if data:
                # 尝试JSON编码
                try:
                    json_data = json.loads(data)
                    payload = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
                except json.JSONDecodeError:
                    # 如果不是JSON，直接编码为UTF-8
                    payload = data.encode('utf-8')
            else:
                payload = b''
            
            # 构建包头
            packet = struct.pack('>B', self.SYNC_HEADER)  # 同步头
            packet += struct.pack('>B', version)  # 版本号
            packet += struct.pack('>H', self.sequence_counter)  # 序号
            packet += struct.pack('>I', len(payload))  # 数据区长度
            packet += struct.pack('>H', message_type)  # 报文类型
            packet += self.RESERVED_BYTES  # 保留区域
            packet += payload  # 数据区
            
            # 增加序号
            self.sequence_counter = (self.sequence_counter + 1) % 65536
            
            return packet
            
        except Exception as e:
            logger.error(f"构建TCP数据包失败: {e}")
            return b''
    
    def format_packet_display(self, packet: bytes) -> str:
        """
        格式化数据包显示
        """
        try:
            hex_str = packet.hex().upper()
            # 每2个字符添加一个空格
            formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
            # 每16个字节换行
            lines = []
            hex_bytes = formatted.split(' ')
            for i in range(0, len(hex_bytes), 16):
                line_bytes = hex_bytes[i:i+16]
                line = ' '.join(line_bytes)
                lines.append(line)
            return '\n'.join(lines)
        except Exception as e:
            logger.error(f"格式化数据包显示失败: {e}")
            return packet.hex().upper()
    
    def get_message_type_name(self, message_type: int) -> str:
        """
        获取消息类型名称
        """
        message_types = {
            2002: "重定位",
            2004: "取消重定位",
            3001: "暂停任务",
            3002: "继续任务",
            3003: "取消订单",
            3055: "平动",
            3056: "转动",
            3057: "托盘旋转",
            3066: "托盘操作",
            4009: "清除错误",
            6004: "软急停"
        }
        return message_types.get(message_type, f"未知类型({message_type})")
    
    def extract_status_from_payload(self, parsed_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从解析后的数据中提取状态信息
        """
        try:
            if parsed_data.get('type') == 'json':
                json_data = parsed_data.get('data', {})
                if isinstance(json_data, dict):
                    # 提取常见的状态字段
                    status_info = {}
                    
                    # 位置信息
                    if 'x' in json_data and 'y' in json_data:
                        status_info['position'] = {
                            'x': json_data.get('x'),
                            'y': json_data.get('y'),
                            'theta': json_data.get('theta', 0)
                        }
                    
                    # 电池信息
                    if 'battery' in json_data:
                        status_info['battery'] = json_data['battery']
                    
                    # 速度信息
                    if 'velocity' in json_data:
                        status_info['velocity'] = json_data['velocity']
                    
                    # 状态信息
                    if 'status' in json_data:
                        status_info['status'] = json_data['status']
                    
                    return status_info if status_info else None
            
            return None
            
        except Exception as e:
            logger.error(f"提取状态信息失败: {e}")
            return None 