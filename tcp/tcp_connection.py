#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCP连接监听器
负责监听小车状态推送端口，生成VDA5050协议的connection消息
"""

import os
import yaml
import json
import time
import socket
import threading
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timezone

# 导入VDA5050协议相关类
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from protocols.vda5050.connection_message import ConnectionMessage
    from protocols.tcp.manufacturer_a import ManufacturerATCPProtocol
    from mqtt_config_loader import MQTTConfigLoader
except ImportError as e:
    logging.warning(f"导入模块失败，某些功能可能不可用: {e}")

logger = logging.getLogger(__name__)

class RobotConfig:
    """机器人配置类"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config_data = None
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载机器人配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            
            logger.info(f"✅ 机器人配置文件加载成功: {self.config_path}")
            return self.config_data
            
        except Exception as e:
            logger.error(f"❌ 加载机器人配置文件失败: {e}")
            return {}
    
    @property
    def vehicle_id(self) -> str:
        """获取机器人ID"""
        return self.config_data.get('robot_info', {}).get('vehicle_id', 'unknown')
    
    @property
    def manufacturer(self) -> str:
        """获取制造商"""
        return self.config_data.get('robot_info', {}).get('manufacturer', 'SEER')
    
    @property
    def ip_address(self) -> str:
        """获取机器人IP地址"""
        return self.config_data.get('network', {}).get('ip_address', '127.0.0.1')
    
    @property
    def status_port(self) -> int:
        """获取状态推送端口"""
        tcp_ports = self.config_data.get('tcp_ports', {})
        # 优先使用push_service_port，其次是status_port
        return tcp_ports.get('navigation_control', {}).get('push_service_port', 
               tcp_ports.get('basic_communication', {}).get('status_port', 19204))
    
    @property
    def status_message_type(self) -> int:
        """获取状态推送消息类型"""
        return self.config_data.get('message_types', {}).get('status_push', {}).get('robot_status', 9300)


class TCPConnectionManager:
    """TCP连接管理器"""
    
    def __init__(self, robot_config: RobotConfig, mqtt_publisher: Optional[Callable] = None):
        self.robot_config = robot_config
        self.mqtt_publisher = mqtt_publisher
        self.server_socket = None
        self.running = False
        self.client_connections = {}
        self.tcp_protocol = ManufacturerATCPProtocol() if 'ManufacturerATCPProtocol' in globals() else None
        
        # 连接状态跟踪
        self.last_heartbeat_time = {}
        self.connection_timeout = 30  # 30秒超时
        self.heartbeat_check_interval = 10  # 10秒检查一次心跳
        
        # 消息处理统计
        self.message_stats = {
            'total_received': 0,
            'status_messages': 0,
            'heartbeat_messages': 0,
            'unknown_messages': 0
        }
    
    def start(self):
        """启动TCP连接监听器"""
        try:
            self.running = True
            
            # 创建TCP服务器
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定到指定端口
            host = self.robot_config.ip_address
            port = self.robot_config.status_port
            
            self.server_socket.bind((host, port))
            self.server_socket.listen(5)
            
            logger.info(f"🔗 TCP连接监听器启动 - 机器人: {self.robot_config.vehicle_id}")
            logger.info(f"📡 监听地址: {host}:{port}")
            logger.info(f"📨 期望消息类型: {self.robot_config.status_message_type}")
            
            # 启动心跳检查线程
            heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
            heartbeat_thread.start()
            
            # 主监听循环
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    client_key = f"{addr[0]}:{addr[1]}"
                    
                    logger.info(f"🤖 机器人连接: {self.robot_config.vehicle_id} ({client_key})")
                    
                    # 记录连接信息
                    self.client_connections[client_key] = {
                        'socket': client_socket,
                        'address': addr,
                        'connect_time': time.time(),
                        'last_seen': time.time(),
                        'vehicle_id': self.robot_config.vehicle_id
                    }
                    
                    # 发布连接状态
                    self._publish_connection_state("ONLINE")
                    
                    # 启动客户端处理线程
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_key),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"❌ 接受连接失败: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ TCP连接监听器启动失败: {e}")
            raise
    
    def _handle_client(self, client_socket: socket.socket, client_key: str):
        """处理客户端连接"""
        try:
            while self.running and client_key in self.client_connections:
                try:
                    # 接收数据
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    # 更新最后见到时间
                    if client_key in self.client_connections:
                        self.client_connections[client_key]['last_seen'] = time.time()
                    
                    # 处理接收到的数据
                    self._process_received_data(data, client_key)
                    
                except socket.timeout:
                    continue
                except socket.error as e:
                    logger.warning(f"⚠️  客户端通信错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ 处理客户端连接失败: {e}")
        finally:
            self._cleanup_client_connection(client_key)
    
    def _process_received_data(self, data: bytes, client_key: str):
        """处理接收到的数据"""
        try:
            self.message_stats['total_received'] += 1
            
            # 解析数据包
            parsed_data = None
            if self.tcp_protocol:
                parsed_data = self.tcp_protocol.parse_tcp_packet(data)
            else:
                # 简单的JSON解析尝试
                try:
                    json_str = data.decode('utf-8')
                    parsed_data = json.loads(json_str)
                except:
                    pass
            
            if not parsed_data:
                logger.warning(f"⚠️  无法解析数据包 - 长度: {len(data)}")
                self.message_stats['unknown_messages'] += 1
                return
            
            message_type = parsed_data.get('message_type', parsed_data.get('messageType', 0))
            logger.debug(f"📨 收到消息 - 类型: {message_type}, 来源: {client_key}")
            
            # 检查是否为状态推送消息
            if message_type == self.robot_config.status_message_type:
                self._handle_status_message(parsed_data, client_key)
                self.message_stats['status_messages'] += 1
            elif message_type == 25940:  # 常见的心跳消息类型
                self._handle_heartbeat_message(parsed_data, client_key)
                self.message_stats['heartbeat_messages'] += 1
            else:
                logger.debug(f"📋 未处理的消息类型: {message_type}")
                self.message_stats['unknown_messages'] += 1
            
            # 定期打印统计信息
            if self.message_stats['total_received'] % 50 == 0:
                self._print_message_stats()
                
        except Exception as e:
            logger.error(f"❌ 处理接收数据失败: {e}")
    
    def _handle_status_message(self, parsed_data: Dict[str, Any], client_key: str):
        """处理状态消息"""
        try:
            logger.info(f"📊 收到机器人状态消息 - 车辆: {self.robot_config.vehicle_id}")
            
            # 从消息数据中提取状态信息
            data_content = parsed_data.get('data', {})
            
            # 确保连接状态为在线
            self._publish_connection_state("ONLINE")
            
        except Exception as e:
            logger.error(f"❌ 处理状态消息失败: {e}")
    
    def _handle_heartbeat_message(self, parsed_data: Dict[str, Any], client_key: str):
        """处理心跳消息"""
        try:
            logger.debug(f"💓 收到心跳消息 - 车辆: {self.robot_config.vehicle_id}")
            
            # 记录心跳时间
            self.last_heartbeat_time[client_key] = time.time()
            
            # 确保连接状态为在线
            self._publish_connection_state("ONLINE")
            
        except Exception as e:
            logger.error(f"❌ 处理心跳消息失败: {e}")
    
    def _heartbeat_monitor(self):
        """心跳监控线程"""
        while self.running:
            try:
                current_time = time.time()
                disconnected_clients = []
                
                for client_key, client_info in self.client_connections.items():
                    last_seen = client_info.get('last_seen', 0)
                    if current_time - last_seen > self.connection_timeout:
                        disconnected_clients.append(client_key)
                
                # 清理超时的连接
                for client_key in disconnected_clients:
                    logger.warning(f"⏰ 连接超时 - 客户端: {client_key}")
                    self._cleanup_client_connection(client_key)
                
                # 如果没有活跃连接，发布离线状态
                if not self.client_connections:
                    self._publish_connection_state("OFFLINE")
                
                time.sleep(self.heartbeat_check_interval)
                
            except Exception as e:
                logger.error(f"❌ 心跳监控错误: {e}")
    
    def _cleanup_client_connection(self, client_key: str):
        """清理客户端连接"""
        try:
            if client_key in self.client_connections:
                client_info = self.client_connections[client_key]
                client_socket = client_info['socket']
                
                try:
                    client_socket.close()
                except:
                    pass
                
                del self.client_connections[client_key]
                
                logger.info(f"🔌 机器人断开连接: {self.robot_config.vehicle_id} ({client_key})")
                
                # 如果没有其他连接，发布离线状态
                if not self.client_connections:
                    self._publish_connection_state("OFFLINE")
                    
        except Exception as e:
            logger.error(f"❌ 清理客户端连接失败: {e}")
    
    def _publish_connection_state(self, state: str):
        """发布连接状态到MQTT"""
        try:
            if not self.mqtt_publisher:
                return
            
            # 创建VDA5050连接消息
            if 'ConnectionMessage' in globals():
                connection_msg = ConnectionMessage(
                    header_id=int(time.time()),
                    connection_state=state,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    version="2.0.0",
                    manufacturer=self.robot_config.manufacturer,
                    serial_number=self.robot_config.vehicle_id
                )
                message_dict = connection_msg.get_message_dict()
            else:
                # 创建简单的连接消息
                message_dict = {
                    "headerId": int(time.time()),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "2.0.0",
                    "manufacturer": self.robot_config.manufacturer,
                    "serialNumber": self.robot_config.vehicle_id,
                    "connectionState": state
                }
            
            # 构建MQTT主题
            topic = f"vda5050/{self.robot_config.vehicle_id}/connection"
            
            # 发布消息
            self.mqtt_publisher(topic, json.dumps(message_dict, ensure_ascii=False))
            
            logger.info(f"📡 发布连接状态: {self.robot_config.vehicle_id} -> {state}")
            
        except Exception as e:
            logger.error(f"❌ 发布连接状态失败: {e}")
    
    def _print_message_stats(self):
        """打印消息统计信息"""
        try:
            stats = self.message_stats
            logger.info(f"📊 消息统计 - 总计: {stats['total_received']}, "
                       f"状态: {stats['status_messages']}, "
                       f"心跳: {stats['heartbeat_messages']}, "
                       f"未知: {stats['unknown_messages']}")
        except Exception as e:
            logger.error(f"❌ 打印统计信息失败: {e}")
    
    def stop(self):
        """停止TCP连接监听器"""
        try:
            self.running = False
            
            # 关闭所有客户端连接
            for client_key in list(self.client_connections.keys()):
                self._cleanup_client_connection(client_key)
            
            # 关闭服务器socket
            if self.server_socket:
                self.server_socket.close()
            
            # 发布离线状态
            self._publish_connection_state("OFFLINE")
            
            logger.info(f"🛑 TCP连接监听器已停止 - 机器人: {self.robot_config.vehicle_id}")
            
        except Exception as e:
            logger.error(f"❌ 停止TCP连接监听器失败: {e}")


class TCPConnectionListener:
    """TCP连接监听器"""
    
    def __init__(self, config_dir: str = "robot_config", mqtt_config_file: str = "mqtt_config/mqtt_config.yaml"):
        self.config_dir = config_dir
        self.mqtt_config_file = mqtt_config_file
        self.connection_managers = {}
        self.running = False
        
        # MQTT相关
        self.mqtt_client = None
        self.mqtt_config_loader = None
        self.mqtt_config = {}
        
        # 加载配置
        self._load_mqtt_config()
    
    def _load_mqtt_config(self):
        """加载MQTT配置"""
        try:
            if 'MQTTConfigLoader' in globals():
                self.mqtt_config_loader = MQTTConfigLoader(self.mqtt_config_file)
                if self.mqtt_config_loader.validate_config():
                    self.mqtt_config = self.mqtt_config_loader.get_full_config()
                    logger.info("✅ MQTT配置加载成功")
            else:
                logger.warning("⚠️  MQTT配置加载器不可用，使用默认配置")
        except Exception as e:
            logger.error(f"❌ 加载MQTT配置失败: {e}")
    
    def _setup_mqtt_client(self):
        """设置MQTT客户端"""
        try:
            import paho.mqtt.client as mqtt
            
            # 获取MQTT配置
            server_config = self.mqtt_config.get("mqtt_server", {})
            auth_config = self.mqtt_config.get("mqtt_auth", {})
            
            # 创建MQTT客户端
            client_id = self.mqtt_config_loader.create_client_id() if self.mqtt_config_loader else "tcp_connection_service"
            self.mqtt_client = mqtt.Client(client_id=client_id)
            
            # 设置认证
            username = auth_config.get("username")
            password = auth_config.get("password")
            if username and password:
                self.mqtt_client.username_pw_set(username, password)
            
            # 连接到MQTT服务器
            host = server_config.get("host", "localhost")
            port = server_config.get("port", 1883)
            keepalive = server_config.get("keepalive", 60)
            
            self.mqtt_client.connect(host, port, keepalive)
            self.mqtt_client.loop_start()
            
            logger.info(f"📡 MQTT客户端连接成功: {host}:{port}")
            
        except Exception as e:
            logger.error(f"❌ MQTT客户端设置失败: {e}")
            raise

    def _mqtt_publisher(self, topic: str, payload: str):
        """MQTT消息发布器"""
        try:
            if self.mqtt_client:
                qos = self.mqtt_config.get("mqtt_options", {}).get("qos_level", 1)
                retain = self.mqtt_config.get("message_config", {}).get("retain", False)
                
                result = self.mqtt_client.publish(topic, payload, qos=qos, retain=retain)
                if result.rc == 0:
                    logger.debug(f"📤 MQTT消息发布成功: {topic}")
                else:
                    logger.warning(f"⚠️  MQTT消息发布失败: {topic}, 错误码: {result.rc}")
            else:
                logger.warning("⚠️  MQTT客户端未连接，无法发布消息")
        except Exception as e:
            logger.error(f"❌ MQTT消息发布失败: {e}")
    
    def start(self):
        """启动监听器"""
        try:
            self.running = True
            
            # 设置MQTT客户端
            self._setup_mqtt_client()
            
            # 扫描配置文件
            if not os.path.exists(self.config_dir):
                raise FileNotFoundError(f"配置目录不存在: {self.config_dir}")
                
            config_files = [f for f in os.listdir(self.config_dir) if f.endswith('.yaml')]
            
            if not config_files:
                raise FileNotFoundError(f"配置目录中没有找到YAML文件: {self.config_dir}")
            
            logger.info(f"🔍 找到 {len(config_files)} 个机器人配置文件")
            
            # 为每个机器人创建连接管理器
            for config_file in config_files:
                config_path = os.path.join(self.config_dir, config_file)
                robot_config = RobotConfig(config_path)
                
                # 创建连接管理器
                connection_manager = TCPConnectionManager(
                    robot_config=robot_config,
                    mqtt_publisher=self._mqtt_publisher
                )
                
                # 启动连接管理器（在单独线程中）
                manager_thread = threading.Thread(
                    target=connection_manager.start,
                    daemon=True
                )
                manager_thread.start()
                
                self.connection_managers[robot_config.vehicle_id] = connection_manager
                
                logger.info(f"🤖 启动连接监听器: {robot_config.vehicle_id} -> 端口 {robot_config.status_port}")
            
            logger.info(f"✅ TCP连接监听器启动完成 - 监听 {len(self.connection_managers)} 个机器人")
            
        except Exception as e:
            logger.error(f"❌ TCP连接监听器启动失败: {e}")
            raise
    
    def stop(self):
        """停止监听器"""
        try:
            self.running = False
            
            # 停止所有连接管理器
            for vehicle_id, manager in self.connection_managers.items():
                try:
                    manager.stop()
                    logger.info(f"🛑 停止连接监听器: {vehicle_id}")
                except Exception as e:
                    logger.error(f"❌ 停止连接监听器失败 {vehicle_id}: {e}")
            
            # 停止MQTT客户端
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                logger.info("📡 MQTT客户端已断开")
                
            logger.info("✅ TCP连接监听器已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止TCP连接监听器失败: {e}")


def main():
    """主函数 - 用于测试"""
    import logging
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建TCP连接监听器
    listener = TCPConnectionListener()
    
    try:
        listener.start()
        
        print("🚀 TCP连接监听器已启动")
        print("💡 监听机器人状态推送，生成VDA5050连接消息")
        print("🛑 按 Ctrl+C 停止服务")
        
        # 保持运行
        while listener.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 正在停止服务...")
        listener.stop()
        print("✅ 服务已停止")
    except Exception as e:
        print(f"❌ 服务错误: {e}")
        listener.stop()


if __name__ == "__main__":
    main()