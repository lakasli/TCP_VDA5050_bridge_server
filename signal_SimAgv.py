#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
虚拟AGV模拟器
基于HUAQING-01.yaml配置，模拟真实AGV的TCP通信行为
- 19301端口：自动上报状态信息
- 其他端口：被动接收TCP数据并回复{"OK"}
"""

import os
import sys
import json
import yaml
import socket
import threading
import time
import logging
import random
import struct
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# 确保logs目录存在
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'virtual_agv.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class VirtualAGVState:
    """虚拟AGV状态管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.robot_info = config.get('robot_info', {})
        
        # AGV基本信息
        self.vehicle_id = self.robot_info.get('vehicle_id', 'HUAQING-01')
        self.manufacturer = self.robot_info.get('manufacturer', 'HUAQING')
        self.serial_number = self.robot_info.get('serial_number', 'HUAQING-01')
        
        # AGV状态
        self.position = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
        self.velocity = {'vx': 0.0, 'vy': 0.0, 'omega': 0.0}
        self.battery_level = 0.85  # 85%
        self.charging = False
        self.errors = []
        self.current_order_id = ""
        self.last_node_id = ""
        self.driving = True  # 默认开启运动
        
        # 运动参数（从配置读取）
        physical_params = self.robot_info.get('physical_parameters', {})
        self.max_speed = physical_params.get('speed_max', 2.0)
        self.max_acceleration = physical_params.get('acceleration_max', 1.0)
        
        # 控制权状态
        self.control_locked = False
        self.control_owner = ""
        
    def update_position(self):
        """更新位置信息（模拟运动）"""
        if self.driving:
            # 简单的运动模拟
            dt = 1.0  # 1秒更新间隔
            
            # 模拟不同的运动模式
            current_time = time.time()
            
            # 根据时间创建不同的运动模式
            if int(current_time) % 30 < 10:  # 前进
                self.velocity['vx'] = min(0.5, self.max_speed * 0.3)
                self.velocity['vy'] = 0.0
                self.velocity['omega'] = 0.0
            elif int(current_time) % 30 < 15:  # 转弯
                self.velocity['vx'] = 0.2
                self.velocity['vy'] = 0.0
                self.velocity['omega'] = 0.3
            elif int(current_time) % 30 < 25:  # 侧移
                self.velocity['vx'] = 0.0
                self.velocity['vy'] = 0.3
                self.velocity['omega'] = 0.0
            else:  # 停止
                self.velocity['vx'] = 0.0
                self.velocity['vy'] = 0.0
                self.velocity['omega'] = 0.0
            
            # 更新位置
            self.position['x'] += self.velocity['vx'] * dt + random.uniform(-0.01, 0.01)
            self.position['y'] += self.velocity['vy'] * dt + random.uniform(-0.01, 0.01)
            self.position['yaw'] += self.velocity['omega'] * dt + random.uniform(-0.01, 0.01)
            
            # 限制角度范围
            while self.position['yaw'] > 3.14159:
                self.position['yaw'] -= 2 * 3.14159
            while self.position['yaw'] < -3.14159:
                self.position['yaw'] += 2 * 3.14159
        else:
            # 停止时速度为0
            self.velocity = {'vx': 0.0, 'vy': 0.0, 'omega': 0.0}
    
    def update_battery(self):
        """更新电池状态"""
        if self.charging:
            self.battery_level = min(1.0, self.battery_level + 0.001)  # 充电
        else:
            if self.driving:
                self.battery_level = max(0.0, self.battery_level - 0.0001)  # 运行耗电
            else:
                self.battery_level = max(0.0, self.battery_level - 0.00005)  # 待机耗电
    
    def get_state_data(self) -> Dict[str, Any]:
        """获取当前状态数据"""
        return {
            "header_id": int(time.time() * 1000) % 1000000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0",
            "manufacturer": self.manufacturer,
            "serial_number": self.serial_number,
            "vehicle_id": self.vehicle_id,
            
            # 位置信息 - 增强的位置数据
            "x": round(self.position['x'], 4),
            "y": round(self.position['y'], 4),
            "yaw": round(self.position['yaw'], 4),
            "map_id": "warehouse_map_001",
            "confidence": 0.95,
            
            # 位置详细信息
            "position": {
                "x": round(self.position['x'], 4),
                "y": round(self.position['y'], 4),
                "yaw": round(self.position['yaw'], 4),
                "map_id": "warehouse_map_001",
                "confidence": 0.95,
                "positioning_state": "LOCALIZED",
                "deviation": {
                    "x": round(random.uniform(0.001, 0.01), 4),
                    "y": round(random.uniform(0.001, 0.01), 4),
                    "yaw": round(random.uniform(0.001, 0.01), 4)
                }
            },
            
            # 速度信息
            "vx": round(self.velocity['vx'], 3),
            "vy": round(self.velocity['vy'], 3),
            "omega": round(self.velocity['omega'], 3),
            
            # 状态信息
            "driving": self.driving,
            "battery_level": round(self.battery_level, 3),
            "charging": self.charging,
            "operating_mode": "AUTOMATIC",
            "node_states": [],
            "edge_states": [],
            "loads": [],
            "action_states": [],
            
            # 订单信息
            "order_id": self.current_order_id,
            "order_update_id": 0,
            "zone_set_id": "",
            "last_node_id": self.last_node_id,
            "last_node_sequence_id": 0,
            
            # 控制权信息
            "current_lock": {
                "locked": self.control_locked,
                "nick_name": self.control_owner,
                "ip": "192.168.9.105" if self.control_locked else ""
            },
            
            # 错误信息
            "errors": self.errors,
            "fatals": [],
            "information": [],
            "warnings": []
        }


class TCPBinaryProtocol:
    """TCP二进制协议处理"""
    
    @staticmethod
    def create_binary_packet(message_type: int, data: Dict[str, Any]) -> bytes:
        """创建二进制TCP数据包"""
        try:
            # 将数据转换为JSON字符串
            json_data = json.dumps(data, ensure_ascii=False)
            data_bytes = json_data.encode('utf-8')
            
            # 构造数据包头
            sync_header = 0x5A  # 同步头
            version = 0x01      # 版本
            sequence = random.randint(1, 65535)  # 序列号
            data_length = len(data_bytes)  # 数据长度
            reserved = b'\x00' * 6  # 保留字段
            
            # 打包数据包头（16字节）
            # 格式：同步头(1B) + 版本(1B) + 序列号(2B) + 数据长度(4B) + 消息类型(2B) + 保留字段(6B)
            header = struct.pack('>BBHIHBBBBBB', 
                               sync_header, version, sequence, data_length,
                               message_type, 0, 0, 0, 0, 0, 0)
            
            # 组合完整数据包
            packet = header + data_bytes
            
            logger.debug(f"创建TCP数据包: 类型={message_type}, 长度={len(packet)}字节")
            return packet
            
        except Exception as e:
            logger.error(f"创建TCP数据包失败: {e}")
            return b''
    
    @staticmethod
    def parse_binary_packet(data: bytes) -> Optional[Dict[str, Any]]:
        """解析二进制TCP数据包"""
        try:
            if len(data) < 16:
                logger.warning(f"数据包太短，长度: {len(data)} < 16")
                return None
            
            # 解析数据包头
            header = struct.unpack('>BBHIHBBBBBB', data[:16])
            sync_header = header[0]
            version = header[1]
            sequence = header[2]
            data_length = header[3]
            message_type = header[4]
            
            logger.info(f"【数据包头解析】:")
            logger.info(f"  同步头: 0x{sync_header:02X} (期望: 0x5A)")
            logger.info(f"  版本: 0x{version:02X}")
            logger.info(f"  序列号: {sequence}")
            logger.info(f"  数据长度: {data_length}")
            logger.info(f"  消息类型: 0x{message_type:04X} ({message_type})")
            
            if sync_header != 0x5A:
                logger.warning(f"无效的同步头: 0x{sync_header:02X}")
                return None
            
            # 验证数据长度
            if data_length < 0 or data_length > 100000:
                logger.warning(f"数据长度不合理: {data_length}")
                return None
            
            # 检查是否有完整的数据包
            if len(data) < 16 + data_length:
                logger.warning(f"数据包不完整，期望长度: {16 + data_length}, 实际长度: {len(data)}")
                return None
            
            # 提取数据部分
            payload = data[16:16+data_length]
            logger.info(f"【数据区提取】:")
            logger.info(f"  数据区长度: {len(payload)} 字节")
            logger.info(f"  数据区十六进制: {payload.hex().upper()}")
            
            # 尝试解析JSON数据
            try:
                payload_str = payload.decode('utf-8')
                logger.info(f"  数据区文本: {payload_str}")
                
                payload_data = json.loads(payload_str)
                logger.info("  JSON解析成功")
                
            except UnicodeDecodeError as e:
                logger.warning(f"  UTF-8解码失败: {e}")
                payload_data = payload.hex().upper()
            except json.JSONDecodeError as e:
                logger.warning(f"  JSON解析失败: {e}")
                payload_data = payload_str if payload else ""
            except Exception as e:
                logger.error(f"  数据解析异常: {e}")
                payload_data = payload.hex().upper()
            
            return {
                'message_type': message_type,
                'sequence': sequence,
                'data_length': data_length,
                'payload': payload_data,
                'raw_data': data.hex().upper(),
                'sync_header': sync_header,
                'version': version
            }
            
        except Exception as e:
            logger.error(f"解析TCP数据包失败: {e}")
            return None


class VirtualAGVTCPServer:
    """虚拟AGV TCP服务器"""
    
    def __init__(self, config_file: str = "robot_config/SIM_AGV.yaml"):
        self.config = self._load_config(config_file)
        self.agv_state = VirtualAGVState(self.config)
        self.protocol = TCPBinaryProtocol()
        
        # TCP服务器配置
        self.servers = {}  # {port: server_socket}
        self.connections = {}  # {port: [connections]}
        self.is_running = False
        
        # 获取网络配置
        network_config = self.config.get('network', {})
        self.agv_ip = network_config.get('ip_address', '127.0.0.1')
        
        # 获取TCP端口配置
        self.tcp_ports = self._get_tcp_ports()
        
        logger.info(f"虚拟AGV初始化完成 - 车辆ID: {self.agv_state.vehicle_id}")
        logger.info(f"监听地址: {self.agv_ip}")
        logger.info(f"TCP端口: {list(self.tcp_ports.keys())}")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"成功加载配置文件: {config_file}")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    def _get_tcp_ports(self) -> Dict[int, str]:
        """获取TCP端口配置"""
        ports = {}
        
        # 从配置文件获取端口
        if 'protocol_adapters' in self.config and 'seer' in self.config['protocol_adapters']:
            tcp_config = self.config['protocol_adapters']['seer'].get('tcp_ports', {})
            
            # 状态上报端口
            if 'state_reporting' in tcp_config:
                ports[tcp_config['state_reporting']] = 'state_reporting'
            
            # 控制端口
            if 'command_control' in tcp_config:
                control_ports = tcp_config['command_control']
                ports[control_ports.get('relocation', 19205)] = 'relocation'
                ports[control_ports.get('movement', 19206)] = 'movement'
                ports[control_ports.get('authority', 19207)] = 'authority'
                ports[control_ports.get('safety', 19210)] = 'safety'
        
        # 默认端口（如果配置文件中没有）
        if not ports:
            ports = {
                19205: 'relocation',
                19206: 'movement', 
                19207: 'authority',
                19210: 'safety',
                19301: 'state_reporting'
            }
        
        return ports
    
    def start(self):
        """启动虚拟AGV服务器"""
        logger.info("正在启动虚拟AGV服务器...")
        
        self.is_running = True
        
        # 启动TCP服务器
        for port, port_type in self.tcp_ports.items():
            self._start_tcp_server(port, port_type)
        
        # 启动状态更新线程
        self._start_state_update_thread()
        
        # 启动状态上报线程（仅针对19301端口）
        self._start_state_reporting_thread()
        
        logger.info("虚拟AGV服务器启动成功")
        logger.info("=" * 60)
        logger.info("【虚拟AGV状态】")
        logger.info(f"车辆ID: {self.agv_state.vehicle_id}")
        logger.info(f"制造商: {self.agv_state.manufacturer}")
        logger.info(f"序列号: {self.agv_state.serial_number}")
        logger.info(f"监听端口: {list(self.tcp_ports.keys())}")
        logger.info("=" * 60)
    
    def stop(self):
        """停止虚拟AGV服务器"""
        logger.info("正在停止虚拟AGV服务器...")
        
        self.is_running = False
        
        # 关闭所有连接
        for port, connections in self.connections.items():
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass
        
        # 关闭所有服务器
        for port, server in self.servers.items():
            try:
                server.close()
                logger.info(f"关闭TCP服务器 - 端口: {port}")
            except:
                pass
        
        logger.info("虚拟AGV服务器已停止")
    
    def _start_tcp_server(self, port: int, port_type: str):
        """启动TCP服务器"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.agv_ip, port))
            server_socket.listen(5)
            
            self.servers[port] = server_socket
            self.connections[port] = []
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(
                target=self._accept_connections,
                args=(server_socket, port, port_type),
                daemon=True
            )
            accept_thread.start()
            
            logger.info(f"TCP服务器启动 - 端口: {port}, 类型: {port_type}")
            
        except Exception as e:
            logger.error(f"启动TCP服务器失败 - 端口: {port}, 错误: {e}")
    
    def _accept_connections(self, server_socket: socket.socket, port: int, port_type: str):
        """接受TCP连接"""
        while self.is_running:
            try:
                client_socket, client_address = server_socket.accept()
                logger.info(f"新连接建立 - 端口: {port}, 客户端: {client_address}")
                
                self.connections[port].append(client_socket)
                
                # 为每个连接启动处理线程
                handle_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, port, port_type, client_address),
                    daemon=True
                )
                handle_thread.start()
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"接受连接失败 - 端口: {port}, 错误: {e}")
                break
    
    def _handle_connection(self, client_socket: socket.socket, port: int, 
                          port_type: str, client_address):
        """处理TCP连接"""
        connection_id = f"{client_address[0]}:{client_address[1]}"
        logger.info(f"开始处理连接 - 端口: {port}, 连接ID: {connection_id}")
        
        try:
            while self.is_running:
                # 接收数据
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # 完整打印接收到的TCP数据包
                logger.info("=" * 80)
                logger.info(f"【收到TCP数据包】- 端口: {port} ({port_type})")
                logger.info(f"客户端地址: {client_address[0]}:{client_address[1]}")
                logger.info(f"数据包长度: {len(data)} 字节")
                logger.info(f"十六进制数据: {data.hex().upper()}")
                
                # 解析数据包
                parsed_data = self.protocol.parse_binary_packet(data)
                if parsed_data:
                    logger.info("【数据包解析成功】")
                    logger.info(f"消息类型: {parsed_data['message_type']}")
                    logger.info(f"序列号: {parsed_data['sequence']}")
                    logger.info(f"数据长度: {parsed_data['data_length']}")
                    
                    # 打印JSON格式的数据内容
                    payload = parsed_data.get('payload', {})
                    if payload:
                        logger.info("【JSON数据内容】:")
                        if isinstance(payload, dict):
                            logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
                        else:
                            logger.info(f"数据内容: {payload}")
                    else:
                        logger.info("【数据内容】: 空数据")
                    
                    # 处理特殊指令
                    self._process_command(parsed_data, port, port_type)
                    
                    # 发送回复
                    response = self._create_response(parsed_data, port, port_type)
                    if response:
                        client_socket.send(response)
                        logger.info(f"【发送回复】- 长度: {len(response)}字节")
                        logger.debug(f"回复数据: {response.hex().upper()}")
                else:
                    # 如果无法解析为二进制协议，尝试文本协议
                    try:
                        text_data = data.decode('utf-8')
                        logger.info("【收到文本数据】:")
                        logger.info(text_data)
                        
                        # 尝试解析为JSON
                        try:
                            json_data = json.loads(text_data)
                            logger.info("【JSON格式数据】:")
                            logger.info(json.dumps(json_data, indent=2, ensure_ascii=False))
                        except json.JSONDecodeError:
                            logger.info("【数据格式】: 普通文本")
                        
                        # 发送简单的JSON回复
                        response = json.dumps({"OK": True, "status": "received"}).encode('utf-8')
                        client_socket.send(response)
                        logger.info(f"【发送文本回复】: {response.decode('utf-8')}")
                    except Exception as e:
                        logger.warning(f"【无法解析数据】: {e}")
                        logger.warning("忽略此数据包")
                
                logger.info("=" * 80)
                
        except Exception as e:
            logger.error(f"处理连接异常 - 端口: {port}, 错误: {e}")
        finally:
            # 清理连接
            try:
                client_socket.close()
                if port in self.connections and client_socket in self.connections[port]:
                    self.connections[port].remove(client_socket)
                    logger.info(f"连接已移除 - 端口: {port}, 连接ID: {connection_id}")
            except Exception as e:
                logger.error(f"清理连接失败: {e}")
            logger.info(f"连接已关闭 - 端口: {port}, 连接ID: {connection_id}")
    
    def _process_command(self, parsed_data: Dict[str, Any], port: int, port_type: str):
        """处理特殊指令"""
        message_type = parsed_data.get('message_type')
        payload = parsed_data.get('payload', {})
        
        try:
            # 控制权抢夺指令
            if message_type == 4005 and port_type == 'authority':
                nick_name = payload.get('nick_name', 'unknown') if isinstance(payload, dict) else 'unknown'
                self.agv_state.control_locked = True
                self.agv_state.control_owner = nick_name
                logger.info(f"控制权已被抢夺 - 所有者: {nick_name}")
            
            # 控制权释放指令
            elif message_type == 4006 and port_type == 'authority':
                self.agv_state.control_locked = False
                self.agv_state.control_owner = ""
                logger.info("控制权已释放")
            
            # 运动控制指令
            elif message_type in [3001, 3002, 3066] and port_type == 'movement':
                if message_type == 3001:  # 恢复运动
                    self.agv_state.driving = True
                    logger.info("开始运动")
                elif message_type == 3002:  # 暂停运动
                    self.agv_state.driving = False
                    logger.info("暂停运动")
                elif message_type == 3066:  # 任务列表
                    if isinstance(payload, dict) and 'move_task_list' in payload:
                        tasks = payload['move_task_list']
                        logger.info(f"收到移动任务列表: {len(tasks)}个任务")
                        self.agv_state.driving = True
            
            # 重定位指令
            elif message_type == 2002 and port_type == 'relocation':
                logger.info("收到重定位指令")
            
            # 清除错误指令
            elif message_type == 4009 and port_type == 'authority':
                self.agv_state.errors.clear()
                logger.info("错误已清除")
            
            # 安全停止指令
            elif message_type == 6004 and port_type == 'safety':
                self.agv_state.driving = False
                self.agv_state.velocity = {'vx': 0.0, 'vy': 0.0, 'omega': 0.0}
                logger.info("安全停止")
            
        except Exception as e:
            logger.error(f"处理指令失败: {e}")
    
    def _create_response(self, parsed_data: Dict[str, Any], port: int, port_type: str) -> bytes:
        """创建回复消息"""
        try:
            message_type = parsed_data.get('message_type')
            
            # 状态上报端口不需要回复
            if port_type == 'state_reporting':
                return b''
            
            # 创建标准回复
            response_data = {
                "OK": True,
                "status": "received",
                "message_type": message_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "vehicle_id": self.agv_state.vehicle_id
            }
            
            # 针对不同指令类型的特殊回复
            if message_type == 4005:  # 控制权抢夺
                response_data["control_granted"] = True
                response_data["owner"] = self.agv_state.control_owner
            elif message_type == 4006:  # 控制权释放
                response_data["control_released"] = True
            elif message_type in [3001, 3002]:  # 运动控制
                response_data["driving"] = self.agv_state.driving
            
            # 创建二进制回复包
            return self.protocol.create_binary_packet(message_type + 1000, response_data)
            
        except Exception as e:
            logger.error(f"创建回复失败: {e}")
            # 发送简单的OK回复
            try:
                return json.dumps({"OK": True}).encode('utf-8')
            except:
                return b'{"OK": true}'
    
    def _start_state_update_thread(self):
        """启动状态更新线程"""
        def state_update_loop():
            while self.is_running:
                try:
                    # 更新AGV状态
                    self.agv_state.update_position()
                    self.agv_state.update_battery()
                    
                    # 模拟一些随机事件
                    if random.random() < 0.001:  # 0.1%概率
                        self.agv_state.charging = not self.agv_state.charging
                        status = "开始充电" if self.agv_state.charging else "停止充电"
                        logger.info(f"状态变化: {status}")
                    
                    time.sleep(1.0)  # 1秒更新一次
                    
                except Exception as e:
                    logger.error(f"状态更新异常: {e}")
                    time.sleep(1.0)
        
        update_thread = threading.Thread(target=state_update_loop, daemon=True)
        update_thread.start()
        logger.info("状态更新线程已启动")
    
    def _start_state_reporting_thread(self):
        """启动状态上报线程（仅针对19301端口）"""
        def state_reporting_loop():
            while self.is_running:
                try:
                    # 检查19301端口是否有连接
                    state_port = None
                    for port, port_type in self.tcp_ports.items():
                        if port_type == 'state_reporting':
                            state_port = port
                            break
                    
                    if state_port and state_port in self.connections:
                        connections = self.connections[state_port]
                        if connections:
                            # 获取当前状态数据
                            state_data = self.agv_state.get_state_data()
                            
                            # 创建状态上报数据包
                            packet = self.protocol.create_binary_packet(9300, state_data)
                            
                            # 发送给所有连接的客户端
                            for conn in connections[:]:  # 使用切片避免迭代时修改
                                try:
                                    conn.send(packet)
                                    logger.info(f"状态上报成功 - 端口: {state_port}, 连接数: {len(connections)}")
                                except Exception as e:
                                    # 连接已断开，移除
                                    logger.warning(f"状态上报失败，移除连接: {e}")
                                    try:
                                        connections.remove(conn)
                                        conn.close()
                                    except:
                                        pass
                        else:
                            logger.debug(f"状态上报端口 {state_port} 暂无连接")
                    
                    # 每秒上报一次
                    time.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"状态上报异常: {e}")
                    time.sleep(1.0)
        
        reporting_thread = threading.Thread(target=state_reporting_loop, daemon=True)
        reporting_thread.start()
        logger.info("状态上报线程已启动")
    
    def print_status(self):
        """打印当前状态"""
        state = self.agv_state.get_state_data()
        
        print("=" * 60)
        print("【虚拟AGV实时状态】")
        print("=" * 60)
        print(f"车辆ID: {state['vehicle_id']}")
        print(f"制造商: {state['manufacturer']}")
        print(f"位置: X={state['x']:.2f}m, Y={state['y']:.2f}m, 偏航角={state['yaw']:.2f}rad")
        print(f"速度: Vx={state['vx']:.2f}m/s, Vy={state['vy']:.2f}m/s, 角速度={state['omega']:.2f}rad/s")
        print(f"电池电量: {state['battery_level']*100:.1f}%")
        print(f"充电状态: {'充电中' if state['charging'] else '未充电'}")
        print(f"运动状态: {'运行中' if state['driving'] else '停止'}")
        print(f"控制权: {'已锁定' if self.agv_state.control_locked else '未锁定'}")
        if self.agv_state.control_locked:
            print(f"控制者: {self.agv_state.control_owner}")
        
        # 连接状态
        total_connections = sum(len(conns) for conns in self.connections.values())
        print(f"TCP连接数: {total_connections}")
        for port, conns in self.connections.items():
            port_type = self.tcp_ports.get(port, 'unknown')
            if conns:
                print(f"  端口 {port} ({port_type}): {len(conns)} 个连接")
                for i, conn in enumerate(conns):
                    try:
                        peer = conn.getpeername()
                        print(f"    连接 {i+1}: {peer[0]}:{peer[1]}")
                    except:
                        print(f"    连接 {i+1}: 无效连接")
            else:
                print(f"  端口 {port} ({port_type}): 0 个连接")
        print("=" * 60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='虚拟AGV模拟器')
    parser.add_argument('--config', default='robot_config/SIM_AGV.yaml', 
                       help='AGV配置文件路径')
    parser.add_argument('--status-interval', type=int, default=10,
                       help='状态打印间隔（秒）')
    
    args = parser.parse_args()
    
    try:
        # 创建虚拟AGV
        virtual_agv = VirtualAGVTCPServer(args.config)
        
        # 启动服务器
        virtual_agv.start()
        
        logger.info("虚拟AGV运行中，按Ctrl+C停止...")
        
        # 定期打印状态
        last_status_time = 0
        
        while True:
            current_time = time.time()
            if current_time - last_status_time >= args.status_interval:
                virtual_agv.print_status()
                last_status_time = current_time
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"程序运行异常: {e}")
    finally:
        if 'virtual_agv' in locals():
            virtual_agv.stop()


if __name__ == "__main__":
    main() 