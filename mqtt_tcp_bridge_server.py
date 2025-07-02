#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050-MQTT-TCP协议转换服务器
实现VDA5050协议与TCP协议之间的双向转换，通过MQTT与上层系统通信
"""

# Windows编码兼容性设置
import os
import sys
if sys.platform.startswith('win'):
    # 设置控制台编码
    if hasattr(os, 'system'):
        os.system('chcp 65001 >nul 2>&1')  # 设置控制台为UTF-8编码
    
    # 重新配置标准输出编码
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

import json
import socket
import threading
import time
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import queue
import struct

# 尝试导入yaml，如果失败则使用默认配置
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("yaml库导入失败")

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入VDA5050相关模块
from vda5050 import (
    OrderMessage, InstantActionsMessage, StateMessage, 
    VisualizationMessage, ConnectionMessage
)

# 导入TCP转换器
from tcp.tcp_order import VDA5050ToTCPConverter
from tcp.tcp_instantActions import VDA5050InstantActionsToTCPConverter
from tcp.tcp_state import AGVToVDA5050Converter
from tcp.tcp_visualization import TCPStateToVisualizationConverter

# 导入厂商A的TCP协议处理器
from tcp.manufacturer_a import ManufacturerATCPProtocol

# MQTT客户端导入
try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import CallbackAPIVersion
except ImportError:
    print("请安装paho-mqtt库: pip install paho-mqtt")
    sys.exit(1)


# 确保logs目录存在
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志 - 修复Windows编码问题
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'vda5050_server.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置控制台输出编码（Windows兼容性）
if sys.platform.startswith('win'):
    import codecs
    # 尝试设置控制台编码为UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, OSError):
        # 如果失败，使用codecs包装器
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
logger = logging.getLogger(__name__)


class MQTTClientManager:
    """MQTT客户端管理器"""
    
    def __init__(self, broker_host: str, broker_port: int, client_id: str = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        # 生成唯一的客户端ID，避免与MQTTX冲突
        self.client_id = client_id or f"vda5050_tcp_server_{uuid.uuid4().hex[:8]}"
        self.client = None
        self.is_connected = False
        self.message_queue = queue.Queue()
        
        # VDA5050 topic模板
        self.topic_templates = {
            'order': '/uagv/v2/{manufacturer}/{serial_number}/order',
            'instantActions': '/uagv/v2/{manufacturer}/{serial_number}/instantActions',
            'state': '/uagv/v2/{manufacturer}/{serial_number}/state',
            'visualization': '/uagv/v2/{manufacturer}/{serial_number}/visualization',
            'connection': '/uagv/v2/{manufacturer}/{serial_number}/connection'
        }
        
    def connect(self):
        """连接MQTT代理"""
        try:
            self.client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
                clean_session=True
            )
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            logger.info(f"正在连接MQTT代理: {self.broker_host}:{self.broker_port}")
            logger.info(f"使用客户端ID: {self.client_id}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 等待连接建立
            timeout = 10
            while not self.is_connected and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
                
            if not self.is_connected:
                raise Exception("MQTT连接超时")
                
            logger.info("MQTT连接成功")
            return True
            
        except Exception as e:
            logger.error(f"MQTT连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开MQTT连接"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT连接已断开")
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT连接回调"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT连接建立成功")
            # 订阅下行topic（从MQTTX发送到AGV的消息）
            self.subscribe_downlink_topics()
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
            # 详细的错误码说明
            error_messages = {
                1: "连接被拒绝 - 协议版本不正确",
                2: "连接被拒绝 - 无效的客户端标识符",
                3: "连接被拒绝 - 服务器不可用",
                4: "连接被拒绝 - 错误的用户名或密码",
                5: "连接被拒绝 - 未授权",
                7: "连接被拒绝 - 客户端ID冲突或其他协议问题"
            }
            if rc in error_messages:
                logger.error(f"详细错误信息: {error_messages[rc]}")
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """MQTT断开连接回调"""
        self.is_connected = False
        logger.warning(f"MQTT连接断开，返回码: {rc}")
        
        # 如果是非正常断开，尝试重连
        if rc != 0:
            logger.info("检测到意外断开，尝试重连...")
            threading.Thread(target=self._reconnect, daemon=True).start()
    
    def _reconnect(self):
        """重连逻辑"""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries and not self.is_connected:
            try:
                retry_count += 1
                wait_time = min(retry_count * 2, 30)  # 指数退避，最大30秒
                logger.info(f"第{retry_count}次重连尝试，等待{wait_time}秒...")
                time.sleep(wait_time)
                
                if self.client:
                    self.client.reconnect()
                    
            except Exception as e:
                logger.error(f"重连失败: {e}")
                
        if not self.is_connected:
            logger.error("重连失败，请检查网络连接和MQTT服务器状态")
    
    def _on_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"收到MQTT消息 - Topic: {topic}")
            
            # 将消息放入队列供主服务器处理
            message_data = {
                'topic': topic,
                'payload': json.loads(payload),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            self.message_queue.put(message_data)
            
        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")
    
    def subscribe_downlink_topics(self):
        """订阅下行topic（MQTTX -> AGV）"""
        topics = [
            ('/uagv/v2/+/+/order', 0),
            ('/uagv/v2/+/+/instantActions', 0),
        ]
        
        for topic, qos in topics:
            self.client.subscribe(topic, qos)
            logger.info(f"订阅topic: {topic}")
    
    def publish_uplink_message(self, message_type: str, manufacturer: str, 
                              serial_number: str, message_data: Dict[str, Any]):
        """发布上行消息（AGV -> MQTTX）"""
        try:
            if not self.is_connected:
                logger.warning("MQTT未连接，无法发布消息")
                return False
            
            topic = self.topic_templates[message_type].format(
                manufacturer=manufacturer,
                serial_number=serial_number
            )
            
            payload = json.dumps(message_data, ensure_ascii=False)
            
            result = self.client.publish(topic, payload, qos=0)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"发布MQTT消息成功 - Topic: {topic}")
                return True
            else:
                logger.error(f"发布MQTT消息失败 - Topic: {topic}, 错误码: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"发布MQTT消息异常: {e}")
            return False
    
    def get_message(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """从消息队列获取消息"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None


class TCPServerManager:
    """TCP服务器管理器"""
    
    def __init__(self, agv_ip: str):
        self.agv_ip = agv_ip
        self.servers = {}
        self.client_connections = {}
        self.is_running = False
        
        # 初始化TCP协议处理器
        self.tcp_protocol = ManufacturerATCPProtocol()
        
        # TCP端口映射（根据实际AGV配置）
        self.tcp_ports = {
            19204: 'stateAPI',      
            19205: 'controlAPI',     
            19206: 'navigationAPI',          
            19207: 'configAPI',         
            19210: 'otherAPI',          
            19301: 'pushAPI'        
        }
        
        # 控制权抢夺配置
        self.control_grab_config = {
            'port': 19207,
            'message_type': 4005,
            'nick_name': 'srd-seer-mizhan'
        }

    def start_servers(self):
        """启动所有TCP服务器"""
        self.is_running = True
        
        for port, port_type in self.tcp_ports.items():
            thread = threading.Thread(
                target=self._start_tcp_server,
                args=(port, port_type),
                daemon=True
            )
            thread.start()
            logger.info(f"启动TCP服务器 - 端口: {port}, 类型: {port_type}")
    
    def stop_servers(self):
        """停止所有TCP服务器"""
        self.is_running = False
        
        # 关闭所有连接
        for port, connections in self.client_connections.items():
            for conn in connections:
                try:
                    conn.close()
                except:
                    pass
        
        # 关闭所有服务器
        for port, server in self.servers.items():
            try:
                server.close()
            except:
                pass
        
        logger.info("所有TCP服务器已停止")
    
    def _start_tcp_server(self, port: int, port_type: str):
        """启动单个TCP服务器"""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', port))
            server.listen(5)
            server.settimeout(1.0)  # 设置超时以便检查is_running
            
            self.servers[port] = server
            self.client_connections[port] = []
            
            logger.info(f"TCP服务器已启动 - 端口: {port}")
            
            while self.is_running:
                try:
                    client_socket, client_address = server.accept()
                    self.client_connections[port].append(client_socket)
                    
                    logger.info(f"AGV连接成功 - 端口: {port}, 地址: {client_address}")
                    
                    # 如果是19207端口，立即发送控制权抢夺指令
                    if port == self.control_grab_config['port']:
                        self._send_control_grab_command(client_socket, port)
                    
                    # 为每个连接创建处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, port, port_type, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.is_running:
                        logger.error(f"TCP服务器错误 - 端口: {port}, 错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"启动TCP服务器失败 - 端口: {port}, 错误: {e}")
    
    def _handle_client(self, client_socket: socket.socket, port: int, 
                      port_type: str, client_address):
        """处理AGV客户端连接"""
        connection_id = f"{client_address[0]}:{client_address[1]}:{port}"
        logger.info(f"创建AGV连接处理线程 - 连接ID: {connection_id}")
        
        try:
            client_socket.settimeout(30.0)  # 30秒超时
            
            while self.is_running:
                try:
                    # 接收AGV发送的数据
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    # 解析TCP数据
                    tcp_data = self._parse_tcp_data(data, port_type)
                    if tcp_data:
                        # 添加连接信息
                        tcp_data['connection_id'] = connection_id
                        tcp_data['client_address'] = client_address
                        
                        # 将TCP数据转换为VDA5050并发送到MQTT
                        self._process_agv_data(tcp_data, port_type)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"处理AGV数据错误 - 端口: {port}, 错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"AGV连接处理异常 - 端口: {port}, 错误: {e}")
        finally:
            try:
                client_socket.close()
                if client_socket in self.client_connections.get(port, []):
                    self.client_connections[port].remove(client_socket)
            except:
                pass
            logger.info(f"AGV连接已断开 - 端口: {port}, 地址: {client_address}, 连接ID: {connection_id}")
    
    def _parse_tcp_data(self, data: bytes, port_type: str) -> Optional[Dict[str, Any]]:
        """解析AGV发送的TCP数据"""
        try:
            # 这里需要根据实际AGV的TCP协议格式进行解析
            # 示例：假设数据是JSON格式
            json_str = data.decode('utf-8').strip()
            parsed_data = json.loads(json_str)
            
            # 添加数据类型标识
            parsed_data['data_type'] = port_type
            parsed_data['received_time'] = datetime.now(timezone.utc).isoformat()
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"解析TCP数据失败: {e}")
            return None
    
    def _process_agv_data(self, tcp_data: Dict[str, Any], port_type: str):
        """处理AGV数据并转换为VDA5050"""
        # 这个方法将被主服务器重写
        pass
    
    def _construct_tcp_packet_with_type(self, message_type: int, data: Dict[str, Any]) -> bytes:
        """构造带有报文类型的TCP数据包（使用厂商A协议格式）"""
        try:
            # 使用厂商A的TCP协议处理器构造完整的二进制数据包
            tcp_packet = self.tcp_protocol.create_binary_tcp_packet(message_type, data)
            return tcp_packet
            
        except Exception as e:
            logger.error(f"构造TCP数据包失败: {e}")
            return b''
    
    def _send_control_grab_command(self, client_socket: socket.socket, port: int):
        """发送控制权抢夺指令"""
        try:
            # 构造控制权抢夺数据
            control_data = {
                "nick_name": self.control_grab_config['nick_name']
            }
            
            # 构造完整的TCP数据包（使用厂商A的二进制格式）
            tcp_packet = self._construct_tcp_packet_with_type(
                self.control_grab_config['message_type'],
                control_data
            )
            
            if tcp_packet:
                # 发送数据包
                client_socket.send(tcp_packet)
                
                # 调试打印：实际发送的TCP数据包
                logger.info("=" * 60)
                logger.info("【控制权抢夺】实际发送的TCP数据包详情:")
                logger.info(f"目标端口: {port}")
                logger.info(f"报文类型: {self.control_grab_config['message_type']}")
                logger.info(f"数据内容: {json.dumps(control_data, ensure_ascii=False)}")
                logger.info(f"数据包长度: {len(tcp_packet)} 字节")
                logger.info(f"十六进制数据: {tcp_packet.hex().upper()}")
                
                # 解析数据包结构用于调试
                if len(tcp_packet) >= 16:
                    sync_header = tcp_packet[0]
                    version = tcp_packet[1]
                    sequence = int.from_bytes(tcp_packet[2:4], 'big')
                    data_len = int.from_bytes(tcp_packet[4:8], 'big')
                    msg_type = int.from_bytes(tcp_packet[8:10], 'big')
                    reserved = tcp_packet[10:16].hex().upper()
                    
                    if len(tcp_packet) >= 16 + data_len:
                        data_content = tcp_packet[16:16+data_len].decode('utf-8')
                    else:
                        data_content = "数据不完整"
                    
                    logger.info("二进制数据包结构解析:")
                    logger.info(f"  - 同步头: 0x{sync_header:02X}")
                    logger.info(f"  - 版本: 0x{version:02X}")
                    logger.info(f"  - 序列号: {sequence}")
                    logger.info(f"  - 数据长度: {data_len}")
                    logger.info(f"  - 报文类型: {msg_type}")
                    logger.info(f"  - 保留字段: {reserved}")
                    logger.info(f"  - 数据内容: {data_content}")
                
                logger.info("=" * 60)
                logger.info(f"控制权抢夺指令发送成功 - 端口: {port}")
                
            else:
                logger.error(f"构造控制权抢夺数据包失败 - 端口: {port}")
                
        except Exception as e:
            logger.error(f"发送控制权抢夺指令失败 - 端口: {port}, 错误: {e}")

    def send_to_agv(self, port: int, data: Dict[str, Any]) -> bool:
        """向AGV发送TCP数据"""
        try:
            connections = self.client_connections.get(port, [])
            if not connections:
                logger.warning(f"端口 {port} 没有AGV连接")
                return False
            
            # 将数据转换为TCP格式（使用简单JSON格式，保持兼容性）
            tcp_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            # 发送到所有连接的AGV
            success_count = 0
            for conn in connections[:]:  # 使用副本避免修改时出错
                try:
                    conn.send(tcp_data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"发送TCP数据失败: {e}")
                    # 移除失效连接
                    connections.remove(conn)
                    try:
                        conn.close()
                    except:
                        pass
            
            if success_count > 0:
                logger.info(f"向AGV发送TCP数据成功 - 端口: {port}, 连接数: {success_count}")
                return True
            else:
                logger.warning(f"向AGV发送TCP数据失败 - 端口: {port}")
                return False
                
        except Exception as e:
            logger.error(f"发送TCP数据异常: {e}")
            return False
    
    def send_to_agv_with_type(self, port: int, message_type: int, data: Dict[str, Any]) -> bool:
        """向AGV发送带报文类型的TCP数据（使用厂商A二进制格式）"""
        try:
            connections = self.client_connections.get(port, [])
            if not connections:
                logger.warning(f"端口 {port} 没有AGV连接")
                return False
            
            # 构造带报文类型的TCP数据包（使用厂商A格式）
            tcp_packet = self._construct_tcp_packet_with_type(message_type, data)
            if not tcp_packet:
                logger.error(f"构造TCP数据包失败 - 端口: {port}")
                return False
            
            # 发送到所有连接的AGV
            success_count = 0
            for conn in connections[:]:  # 使用副本避免修改时出错
                try:
                    conn.send(tcp_packet)
                    success_count += 1
                    
                    # 调试打印
                    logger.info(f"发送二进制TCP数据包 - 端口: {port}, 报文类型: {message_type}")
                    logger.info(f"数据内容: {json.dumps(data, ensure_ascii=False)}")
                    logger.info(f"十六进制数据: {tcp_packet.hex().upper()}")
                    
                except Exception as e:
                    logger.error(f"发送TCP数据失败: {e}")
                    # 移除失效连接
                    connections.remove(conn)
                    try:
                        conn.close()
                    except:
                        pass
            
            if success_count > 0:
                logger.info(f"向AGV发送二进制TCP数据成功 - 端口: {port}, 连接数: {success_count}")
                return True
            else:
                logger.warning(f"向AGV发送二进制TCP数据失败 - 端口: {port}")
                return False
                
        except Exception as e:
            logger.error(f"发送二进制TCP数据异常: {e}")
            return False


class ProtocolConverter:
    """协议转换器"""
    
    def __init__(self):
        # 初始化各种转换器
        self.order_converter = VDA5050ToTCPConverter()
        self.instant_actions_converter = VDA5050InstantActionsToTCPConverter()
        self.state_converter = AGVToVDA5050Converter()
        self.visualization_converter = TCPStateToVisualizationConverter()
    
    def vda5050_order_to_tcp(self, order_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将VDA5050 Order转换为TCP数据"""
        try:
            tcp_result = self.order_converter.convert_vda5050_order_to_tcp_move_task_list(order_data)
            # Order统一发送到19206端口，使用消息类型3066
            return [{'port': 19206, 'message_type': 3066, 'data': tcp_result}]
        except Exception as e:
            logger.error(f"Order转换失败: {e}")
            return []
    
    def vda5050_instant_actions_to_tcp(self, actions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将VDA5050 InstantActions转换为TCP数据"""
        try:
            # 使用TCP即时动作转换器分析配置
            action_configs = self.instant_actions_converter.analyze_instant_action_configs(actions_data)
            
            port_data = []
            for config in action_configs:
                # 转换单个动作
                action = actions_data.get('actions', [])[config['index']] if config['index'] < len(actions_data.get('actions', [])) else {}
                
                # 构造VDA5050格式数据用于转换
                single_action_data = {
                    'headerId': actions_data.get('headerId', 0),
                    'timestamp': actions_data.get('timestamp', ''),
                    'version': actions_data.get('version', '2.0.0'),
                    'manufacturer': actions_data.get('manufacturer', ''),
                    'serialNumber': actions_data.get('serialNumber', ''),
                    'actions': [action]
                }
                
                # 转换为TCP数据
                tcp_result = self.instant_actions_converter.convert_vda5050_instant_actions(single_action_data)
                
                # 提取实际数据部分
                if isinstance(tcp_result, dict):
                    if 'instant_actions' in tcp_result:
                        # 多个动作的情况
                        for action_result in tcp_result['instant_actions']:
                            port_data.append({
                                'port': action_result['port'],
                                'message_type': action_result['messageType'],
                                'data': action_result['data']
                            })
                    else:
                        # 单个动作的情况
                        port_data.append({
                            'port': config['port'],
                            'message_type': config['messageType'],
                            'data': tcp_result
                        })
            
            return port_data
            
        except Exception as e:
            logger.error(f"InstantActions转换失败: {e}")
            return []
    
    def tcp_state_to_vda5050(self, tcp_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """将TCP State数据转换为VDA5050 State"""
        try:
            state_message = self.state_converter.convert_agv_data_to_vda5050_state(tcp_data)
            return state_message.get_message_dict()
        except Exception as e:
            logger.error(f"State转换失败: {e}")
            return None
    
    def tcp_state_to_visualization(self, tcp_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """将TCP State数据转换为VDA5050 Visualization"""
        try:
            viz_message = self.visualization_converter.convert_tcp_state_to_visualization(tcp_data)
            return viz_message.get_message_dict()
        except Exception as e:
            logger.error(f"Visualization转换失败: {e}")
            return None
    
    def create_connection_message(self, agv_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建VDA5050 Connection消息"""
        try:
            connection_msg = ConnectionMessage(
                header_id=int(time.time()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                version="2.0.0",
                manufacturer=agv_data.get('manufacturer', 'AGV_Manufacturer'),
                serial_number=agv_data.get('vehicle_id', 'AGV_001'),
                connection_state="ONLINE"
            )
            return connection_msg.get_message_dict()
        except Exception as e:
            logger.error(f"Connection消息创建失败: {e}")
            return {}


class VDA5050Server:
    """VDA5050协议转换服务器主类"""
    
    def __init__(self, mqtt_config: Dict[str, Any], agv_ip: str):
        self.mqtt_config = mqtt_config
        self.agv_ip = agv_ip
        
        # 初始化组件
        self.mqtt_manager = MQTTClientManager(
            mqtt_config['host'].replace('mqtt://', ''),
            mqtt_config['port'],
            mqtt_config.get('client_id')  # 使用get方法，允许None值
        )
        
        self.tcp_manager = TCPServerManager(agv_ip)
        self.converter = ProtocolConverter()
        
        # 状态管理
        self.is_running = False
        
        # 多机器人管理 - 每个AGV连接对应一个信息记录
        self.agv_connections = {}  # {connection_id: agv_info}
        self.agv_info_by_vehicle_id = {}  # {vehicle_id: agv_info}
        self.default_agv_info = {
            'manufacturer': 'Demo_Manufacturer',
            'serial_number': 'AGV_001'
        }
        
        # 重写TCP管理器的数据处理方法
        self.tcp_manager._process_agv_data = self._process_agv_tcp_data
    
    def start(self):
        """启动服务器"""
        logger.info("正在启动VDA5050协议转换服务器...")
        
        try:
            # 连接MQTT
            if not self.mqtt_manager.connect():
                raise Exception("MQTT连接失败")
            
            # 启动TCP服务器
            self.tcp_manager.start_servers()
            
            # 启动主消息处理循环
            self.is_running = True
            self._start_message_loop()
            
            logger.info("VDA5050协议转换服务器启动成功")
            
            # 启动后立即打印初始状态
            logger.info("=" * 60)
            logger.info("【多AGV桥接服务】")
            logger.info("- 支持同时连接多个AGV")
            logger.info("- 自动识别AGV身份和路由消息")
            logger.info("- MQTT Topic格式: /uagv/v2/{manufacturer}/{serial_number}/{message_type}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            self.stop()
    
    def stop(self):
        """停止服务器"""
        logger.info("正在停止VDA5050协议转换服务器...")
        
        self.is_running = False
        
        # 停止MQTT
        self.mqtt_manager.disconnect()
        
        # 停止TCP服务器
        self.tcp_manager.stop_servers()
        
        logger.info("VDA5050协议转换服务器已停止")
    
    def _start_message_loop(self):
        """启动主消息处理循环"""
        def message_loop():
            last_status_print = 0
            status_print_interval = 300  # 每5分钟打印一次状态
            
            while self.is_running:
                try:
                    # 处理MQTT消息（下行：MQTTX -> AGV）
                    mqtt_message = self.mqtt_manager.get_message(timeout=0.1)
                    if mqtt_message:
                        self._handle_mqtt_message(mqtt_message)
                    
                    # 定期打印AGV连接状态
                    current_time = time.time()
                    if current_time - last_status_print >= status_print_interval:
                        self.print_connected_agvs()
                        last_status_print = current_time
                    
                    time.sleep(0.01)  # 避免过度占用CPU
                    
                except Exception as e:
                    logger.error(f"消息循环异常: {e}")
                    time.sleep(1)
        
        message_thread = threading.Thread(target=message_loop, daemon=True)
        message_thread.start()
    
    def _handle_mqtt_message(self, message_data: Dict[str, Any]):
        """处理MQTT消息（下行：MQTTX -> AGV）"""
        try:
            topic = message_data['topic']
            payload = message_data['payload']
            
            # 解析topic获取目标AGV信息
            target_agv = self._parse_topic_for_agv_info(topic)
            if not target_agv:
                logger.warning(f"无法解析topic中的AGV信息: {topic}")
                return
            
            logger.info(f"处理MQTT消息: {topic} -> 目标AGV: {target_agv['manufacturer']}/{target_agv['serial_number']}")
            
            if '/order' in topic:
                # 处理Order消息 - 增加详细打印功能
                self._handle_order_message(topic, payload, target_agv)
                    
            elif '/instantActions' in topic:
                # 处理InstantActions消息 - 增加详细打印功能
                self._handle_instant_actions_message(topic, payload, target_agv)
            
            else:
                logger.warning(f"未知的MQTT topic: {topic}")
                
        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")
    
    def _parse_topic_for_agv_info(self, topic: str) -> Optional[Dict[str, str]]:
        """从topic中解析AGV信息"""
        try:
            # 期望格式: /uagv/v2/{manufacturer}/{serial_number}/{message_type}
            parts = topic.strip('/').split('/')
            if len(parts) >= 4 and parts[0] == 'uagv' and parts[1] == 'v2':
                return {
                    'manufacturer': parts[2],
                    'serial_number': parts[3]
                }
            return None
        except Exception as e:
            logger.error(f"解析topic失败: {e}")
            return None
    
    def _handle_order_message(self, topic: str, payload: Dict[str, Any], target_agv: Dict[str, str]):
        """处理VDA5050 Order消息并打印详细信息"""
        try:
            logger.info("=" * 80)
            logger.info("【VDA5050 ORDER 消息处理】")
            logger.info("=" * 80)
            
            # 1. 打印原始VDA5050 Order消息
            logger.info("[MQTT] 收到VDA5050 Order消息:")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            # 提取关键信息
            order_id = payload.get('orderId', 'N/A')
            order_update_id = payload.get('orderUpdateId', 'N/A')
            zone_set_id = payload.get('zoneSetId', 'N/A')
            nodes_count = len(payload.get('nodes', []))
            edges_count = len(payload.get('edges', []))
            
            logger.info("[Order] 关键信息:")
            logger.info(f"   - Order ID: {order_id}")
            logger.info(f"   - Order Update ID: {order_update_id}")
            logger.info(f"   - Zone Set ID: {zone_set_id}")
            logger.info(f"   - 节点数量: {nodes_count}")
            logger.info(f"   - 边数量: {edges_count}")
            
            # 打印节点和动作信息
            if 'nodes' in payload:
                logger.info("[节点] 信息:")
                for i, node in enumerate(payload['nodes']):
                    node_id = node.get('nodeId', 'N/A')
                    sequence_id = node.get('sequenceId', 'N/A')
                    actions = node.get('actions', [])
                    action_types = [action.get('actionType', 'N/A') for action in actions]
                    logger.info(f"   [{i+1}] Node ID: {node_id}, Sequence: {sequence_id}, Actions: {action_types}")
            
            if 'edges' in payload:
                logger.info("[边] 信息:")
                for i, edge in enumerate(payload['edges']):
                    edge_id = edge.get('edgeId', 'N/A')
                    sequence_id = edge.get('sequenceId', 'N/A')
                    start_node = edge.get('startNodeId', 'N/A')
                    end_node = edge.get('endNodeId', 'N/A')
                    actions = edge.get('actions', [])
                    action_types = [action.get('actionType', 'N/A') for action in actions]
                    logger.info(f"   [{i+1}] Edge ID: {edge_id}, Sequence: {sequence_id}, {start_node} -> {end_node}, Actions: {action_types}")
            
            logger.info("-" * 80)
            
            # 2. 转换为TCP协议格式
            logger.info("[转换] 开始VDA5050 -> TCP协议转换...")
            tcp_data_list = self.converter.vda5050_order_to_tcp(payload)
            
            # 3. 打印转换后的TCP协议格式
            logger.info("[TCP] 转换后的协议格式:")
            for i, item in enumerate(tcp_data_list):
                logger.info(f"   TCP数据包 [{i+1}]:")
                logger.info(f"   - 目标端口: {item['port']}")
                logger.info(f"   - 报文类型: {item['message_type']}")
                logger.info(f"   - 数据内容: {json.dumps(item['data'], indent=4, ensure_ascii=False)}")
                
                # 如果是move_task_list格式，打印任务详情
                if isinstance(item['data'], dict) and 'move_task_list' in item['data']:
                    task_list = item['data']['move_task_list']
                    logger.info(f"   - 任务列表 ({len(task_list)} 个任务):")
                    for j, task in enumerate(task_list):
                        task_id = task.get('task_id', 'N/A')
                        source_id = task.get('source_id', 'N/A')
                        target_id = task.get('id', 'N/A')
                        operation = task.get('operation', '移动')
                        logger.info(f"     [{j+1}] {task_id}: {source_id} -> {target_id} ({operation})")
            
            logger.info("-" * 80)
            
            # 4. 发送TCP数据包并记录
            logger.info(f"[发送] TCP数据包到目标AGV: {target_agv['manufacturer']}/{target_agv['serial_number']}")
            for i, item in enumerate(tcp_data_list):
                logger.info(f"   发送数据包 [{i+1}] 到端口 {item['port']}, 报文类型 {item['message_type']}")
                
                # 使用二进制TCP数据包格式发送到指定AGV
                success = self._send_to_specific_agv(
                    target_agv,
                    item['port'], 
                    item['message_type'], 
                    item['data']
                )
                
                status = "[成功]" if success else "[失败]"
                logger.info(f"   结果: {status}")
            
            logger.info("=" * 80)
            logger.info("【VDA5050 ORDER 处理完成】")
            logger.info("=" * 80)
                    
        except Exception as e:
            logger.error(f"处理Order消息失败: {e}")
    
    def _handle_instant_actions_message(self, topic: str, payload: Dict[str, Any], target_agv: Dict[str, str]):
        """处理VDA5050 InstantActions消息并打印详细信息"""
        try:
            logger.info("=" * 80)
            logger.info("【VDA5050 INSTANT ACTIONS 消息处理】")
            logger.info("=" * 80)
            
            # 1. 打印原始VDA5050 InstantActions消息
            logger.info("[MQTT] 收到VDA5050 InstantActions消息:")
            logger.info(f"   Topic: {topic}")
            logger.info(f"   Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
            # 提取关键信息
            header_id = payload.get('headerId', 'N/A')
            actions = payload.get('actions', [])
            actions_count = len(actions)
            
            logger.info("[InstantActions] 关键信息:")
            logger.info(f"   - Header ID: {header_id}")
            logger.info(f"   - 动作数量: {actions_count}")
            
            # 打印动作详情
            if actions:
                logger.info("[动作] 即时动作详情:")
                for i, action in enumerate(actions):
                    action_id = action.get('actionId', 'N/A')
                    action_type = action.get('actionType', 'N/A')
                    action_desc = action.get('actionDescription', 'N/A')
                    blocking_type = action.get('blockingType', 'N/A')
                    logger.info(f"   [{i+1}] ID: {action_id}, Type: {action_type}, Desc: {action_desc}, Blocking: {blocking_type}")
            
            logger.info("-" * 80)
            
            # 2. 转换为TCP协议格式
            logger.info("[转换] 开始VDA5050 -> TCP协议转换...")
            tcp_data_list = self.converter.vda5050_instant_actions_to_tcp(payload)
            
            # 3. 打印转换后的TCP协议格式
            logger.info("[TCP] 转换后的协议格式:")
            for i, item in enumerate(tcp_data_list):
                logger.info(f"   TCP数据包 [{i+1}]:")
                logger.info(f"   - 目标端口: {item['port']}")
                logger.info(f"   - 报文类型: {item['message_type']}")
                
                # 检查是否为空数据
                if isinstance(item['data'], dict) and item['data'].get("__empty_data__"):
                    logger.info(f"   - 数据内容: 空数据区（无内容）")
                else:
                    logger.info(f"   - 数据内容: {json.dumps(item['data'], indent=4, ensure_ascii=False)}")
            
            logger.info("-" * 80)
            
            # 4. 发送TCP数据包并记录
            logger.info(f"[发送] TCP数据包到目标AGV: {target_agv['manufacturer']}/{target_agv['serial_number']}")
            for i, item in enumerate(tcp_data_list):
                logger.info(f"   发送数据包 [{i+1}] 到端口 {item['port']}, 报文类型 {item['message_type']}")
                
                # 使用二进制TCP数据包格式发送到指定AGV
                success = self._send_to_specific_agv(
                    target_agv,
                    item['port'], 
                    item['message_type'], 
                    item['data']
                )
                
                status = "[成功]" if success else "[失败]"
                logger.info(f"   结果: {status}")
            
            logger.info("=" * 80)
            logger.info("【VDA5050 INSTANT ACTIONS 处理完成】")
            logger.info("=" * 80)
                    
        except Exception as e:
            logger.error(f"处理InstantActions消息失败: {e}")
    
    def _process_agv_tcp_data(self, tcp_data: Dict[str, Any], port_type: str):
        """处理AGV TCP数据（上行：AGV -> MQTTX）"""
        try:
            connection_id = tcp_data.get('connection_id', 'unknown')
            logger.info(f"处理AGV TCP数据: {port_type}, 连接ID: {connection_id}")
            
            if port_type == 'pushAPI':
                # 处理State数据（支持两种端口类型以兼容现有配置）
                self._handle_state_data(tcp_data)
            else:
                # 其他类型的数据暂时记录
                vehicle_id = tcp_data.get('vehicle_id', 'unknown')
                logger.info(f"收到AGV数据 - 车辆ID: {vehicle_id}, 类型: {port_type}, 连接ID: {connection_id}")
                logger.debug(f"数据内容: {json.dumps(tcp_data, ensure_ascii=False)}")
                
        except Exception as e:
            logger.error(f"处理AGV TCP数据失败: {e}")
    
    def _handle_state_data(self, tcp_data: Dict[str, Any]):
        """处理AGV状态数据（支持多机器人）"""
        try:
            # 从TCP数据中提取AGV信息
            vehicle_id = tcp_data.get('vehicle_id', 'UNKNOWN_AGV')
            manufacturer = tcp_data.get('manufacturer', self.default_agv_info['manufacturer'])
            connection_id = tcp_data.get('connection_id', 'unknown')
            
            # 获取或创建AGV信息
            agv_info = self._get_or_create_agv_info(vehicle_id, manufacturer, connection_id)
            
            logger.info(f"处理AGV状态数据 - 车辆ID: {vehicle_id}, 制造商: {manufacturer}, 连接ID: {connection_id}")
            
            # 转换为VDA5050 State消息
            state_data = self.converter.tcp_state_to_vda5050(tcp_data)
            if state_data:
                success = self.mqtt_manager.publish_uplink_message(
                    'state',
                    agv_info['manufacturer'],
                    agv_info['serial_number'],
                    state_data
                )
                if success:
                    logger.debug(f"发布State消息成功 - 车辆: {vehicle_id}")
            
            # 转换为VDA5050 Visualization消息
            viz_data = self.converter.tcp_state_to_visualization(tcp_data)
            if viz_data:
                success = self.mqtt_manager.publish_uplink_message(
                    'visualization',
                    agv_info['manufacturer'],
                    agv_info['serial_number'],
                    viz_data
                )
                if success:
                    logger.debug(f"发布Visualization消息成功 - 车辆: {vehicle_id}")
            
            # 创建Connection消息
            conn_data = self.converter.create_connection_message(tcp_data)
            if conn_data:
                success = self.mqtt_manager.publish_uplink_message(
                    'connection',
                    agv_info['manufacturer'],
                    agv_info['serial_number'],
                    conn_data
                )
                if success:
                    logger.debug(f"发布Connection消息成功 - 车辆: {vehicle_id}")
                
        except Exception as e:
            logger.error(f"处理状态数据失败: {e}")
    
    def _get_or_create_agv_info(self, vehicle_id: str, manufacturer: str, connection_id: str) -> Dict[str, str]:
        """获取或创建AGV信息（支持多机器人）"""
        try:
            # 首先尝试根据vehicle_id查找
            if vehicle_id in self.agv_info_by_vehicle_id:
                agv_info = self.agv_info_by_vehicle_id[vehicle_id]
                # 更新连接ID
                agv_info['connection_id'] = connection_id
                self.agv_connections[connection_id] = agv_info
                return agv_info
            
            # 创建新的AGV信息
            agv_info = {
                'manufacturer': manufacturer,
                'serial_number': vehicle_id,
                'connection_id': connection_id,
                'first_seen': datetime.now(timezone.utc).isoformat()
            }
            
            # 存储信息
            self.agv_info_by_vehicle_id[vehicle_id] = agv_info
            self.agv_connections[connection_id] = agv_info
            
            logger.info(f"注册新AGV - 车辆ID: {vehicle_id}, 制造商: {manufacturer}, 连接ID: {connection_id}")
            
            return agv_info
            
        except Exception as e:
            logger.error(f"获取或创建AGV信息失败: {e}")
            # 返回默认信息
            return {
                'manufacturer': manufacturer or self.default_agv_info['manufacturer'],
                'serial_number': vehicle_id or self.default_agv_info['serial_number'],
                'connection_id': connection_id
            }
    
    def get_connected_agvs(self) -> List[Dict[str, str]]:
        """获取当前连接的所有AGV信息"""
        return list(self.agv_info_by_vehicle_id.values())
    
    def get_agv_count(self) -> int:
        """获取当前连接的AGV数量"""
        return len(self.agv_info_by_vehicle_id)
    
    def _send_to_specific_agv(self, target_agv: Dict[str, str], port: int, 
                             message_type: int, data: Dict[str, Any]) -> bool:
        """发送数据到指定的AGV"""
        try:
            target_vehicle_id = target_agv['serial_number']
            
            # 检查目标AGV是否连接
            if target_vehicle_id not in self.agv_info_by_vehicle_id:
                logger.warning(f"目标AGV未连接: {target_vehicle_id}")
                # 尝试广播到所有连接的AGV（兼容模式）
                logger.info(f"切换到广播模式，发送到端口 {port} 的所有连接")
                return self.tcp_manager.send_to_agv_with_type(port, message_type, data)
            
            # 获取目标AGV的连接信息
            agv_info = self.agv_info_by_vehicle_id[target_vehicle_id]
            connection_id = agv_info.get('connection_id')
            
            if not connection_id:
                logger.warning(f"目标AGV连接信息缺失: {target_vehicle_id}")
                return False
            
            # 发送到特定连接（这里简化处理，实际上需要根据connection_id找到具体的socket）
            # 目前先使用广播模式，后续可以优化为精确路由
            logger.info(f"发送数据到目标AGV: {target_vehicle_id} (连接ID: {connection_id})")
            return self.tcp_manager.send_to_agv_with_type(port, message_type, data)
            
        except Exception as e:
            logger.error(f"发送数据到指定AGV失败: {e}")
            return False
    
    def print_connected_agvs(self):
        """打印当前连接的所有AGV信息"""
        agvs = self.get_connected_agvs()
        logger.info("=" * 60)
        logger.info(f"【当前连接的AGV列表】({len(agvs)} 台)")
        logger.info("=" * 60)
        
        if not agvs:
            logger.info("暂无AGV连接")
        else:
            for i, agv in enumerate(agvs, 1):
                logger.info(f"[{i}] 车辆ID: {agv['serial_number']}")
                logger.info(f"    制造商: {agv['manufacturer']}")
                logger.info(f"    连接ID: {agv.get('connection_id', 'N/A')}")
                logger.info(f"    首次连接: {agv.get('first_seen', 'N/A')}")
                logger.info("    " + "-" * 40)
        
        logger.info("=" * 60)


def load_config():
    """加载配置文件"""
    if not YAML_AVAILABLE:
        logger.warning("PyYAML未安装，无法加载配置文件。请安装: pip install PyYAML")
        return None
        
    try:
        # 尝试加载YAML配置文件
        config_file = 'mqtt_config/mqtt_config.yaml'
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config
        else:
            logger.warning(f"配置文件{config_file}不存在，使用默认配置")
            return None
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None

def main():
    """主函数"""
    # 加载配置
    config = load_config()
    
    if config and 'mqtt_server' in config:
        # 使用配置文件的设置
        mqtt_config = {
            'host': config['mqtt_server']['host'],
            'port': config['mqtt_server']['port'],
            'client_id': None  # 让系统自动生成唯一ID
        }
        logger.info("使用配置文件中的MQTT设置")
    else:
        # 使用默认配置，但避免客户端ID冲突
        mqtt_config = {
            'host': '172.31.232.152',  # 与测试组件保持一致
            'port': 1883,
            'client_id': None  # 让系统自动生成唯一ID
        }
        logger.info("使用默认MQTT配置")
    
    # AGV IP配置（可以修改为实际AGV的IP）
    agv_ip = '192.168.1.100'  # 修改为实际AGV IP
    
    # 创建服务器
    server = VDA5050Server(mqtt_config, agv_ip)
    
    try:
        # 启动服务器
        server.start()
        
        logger.info("服务器运行中，按Ctrl+C停止...")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"服务器运行异常: {e}")
    finally:
        server.stop()


if __name__ == "__main__":
    main() 