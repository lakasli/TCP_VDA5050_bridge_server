#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT-TCP桥接服务器
支持VDA5050协议的AGV与MQTT代理之间的双向通信
"""

import os
import sys
import time
import json
import yaml
import socket
import threading
import logging
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)



# 导入MQTT客户端
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("警告: paho-mqtt未安装，MQTT功能将不可用")

# 导入TCP协议处理模块
try:
    from tcp.manufacturer_a import ManufacturerATCPProtocol
    TCP_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"导入TCP模块失败: {e}")
    TCP_MODULES_AVAILABLE = False



# 配置日志 - 只输出到文件，避免干扰动态显示
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/vda5050_server.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class DynamicTableDisplay:
    """动态表格显示类 - 在控制台中实时显示AGV状态"""
    
    def __init__(self):
        self.is_running = False
        self.display_thread = None
        self.last_update_time = 0
        self.update_interval = 2.0  # 更新间隔（秒）
        
        # 控制台控制
        self.clear_command = 'cls' if os.name == 'nt' else 'clear'
        

        
    def start_display(self, tcp_manager, mqtt_client=None):
        """启动动态显示"""
        self.tcp_manager = tcp_manager
        self.mqtt_client = mqtt_client
        self.is_running = True
        
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        
    def stop_display(self):
        """停止动态显示"""
        self.is_running = False
        if self.display_thread:
            self.display_thread.join(timeout=1.0)
            
    def _display_loop(self):
        """显示循环"""
        while self.is_running:
            try:
                current_time = time.time()
                if current_time - self.last_update_time >= self.update_interval:
                    self._update_display()
                    self.last_update_time = current_time
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"显示循环错误: {e}")
                
    def _update_display(self):
        """更新显示内容"""
        try:
            # 清屏
            os.system(self.clear_command)
            
            # 显示标题
            self._print_header()
            
            # 显示CPU负载信息
            self._print_cpu_load_info()
            
            # 显示AGV状态表格
            self._print_agv_status_table()
            
            # 显示MQTT状态
            self._print_mqtt_status()
            
            # 显示系统信息
            self._print_system_info()
            
        except Exception as e:
            logger.error(f"更新显示失败: {e}")
            
    def _print_header(self):
        """打印标题"""
        print("=" * 120)
        print("VDA5050 MQTT-TCP 桥接服务器 - 实时状态监控")
        print("=" * 120)
        print(f"[更新时间] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
    def _print_agv_status_table(self):
        """打印AGV状态表格"""
        print("[AGV 连接状态表格]")
        print("-" * 120)
        
        # 表头
        header = f"{'AGV ID':<15} {'IP地址':<13} {'制造商':<10} {'状态':<13} {'连接端口':<41} {'最后通信':<8}"
        print(header)
        print("-" * 120)
            
        # 获取AGV信息
        connected_agvs = self.tcp_manager.get_connected_agvs()
        
        for agv_id, config in self.tcp_manager.all_agv_configs.items():
            try:
                # 获取基础信息
                network_config = config.get('network', {})
                robot_info = config.get('robot_info', {})
                
                ip_address = network_config.get('ip_address', '未配置')
                manufacturer = robot_info.get('manufacturer', '未知')
                
                # 连接状态
                if agv_id in connected_agvs:
                    status = "[已连接]"
                    # 获取连接端口
                    connected_ports = []
                    if agv_id in self.tcp_manager.connections:
                        connected_ports = list(self.tcp_manager.connections[agv_id].keys())
                    
                    ports_str = f"{connected_ports} ({len(connected_ports)}/5)"
                    
                    # 最后通信时间
                    last_comm = self._get_last_communication_time(agv_id)
                    
                elif agv_id in getattr(self.tcp_manager, 'failed_agvs', []):
                    status = "[重连中]"
                    ports_str = "等待重连..."
                    last_comm = "连接失败"
                else:
                    status = "[未启动]"
                    ports_str = "未尝试连接"
                    last_comm = "无数据"
                
                # 打印行
                row = f"{agv_id:<15} {ip_address:<15} {manufacturer:<12} {status:<12} {ports_str:<42} {last_comm:<8}"
                print(row)
                
            except Exception as e:
                print(f"[错误] 处理AGV {agv_id} 信息时出错: {e}")
                # 打印基础信息
                row = f"{agv_id:<15} {'错误':<15} {'错误':<12} {'[错误]':<12} {'配置错误':<42} {'无数据':<8}"
                print(row)
                      
        print()

    def _print_mqtt_status(self):
        """打印MQTT状态"""
        print("[MQTT 连接状态]")
        print("-" * 60)
        
        if self.mqtt_client:
            # 获取MQTT连接信息
            mqtt_host = getattr(self.mqtt_client, '_host', '未知')
            mqtt_port = getattr(self.mqtt_client, '_port', '未知')
            
            if hasattr(self.mqtt_client, 'is_connected') and self.mqtt_client.is_connected():
                print(f"[已连接] MQTT状态 | [地址] {mqtt_host}:{mqtt_port}")
            else:
                print(f"[未连接] MQTT状态 | [地址] {mqtt_host}:{mqtt_port}")
        else:
            print("[未配置] MQTT状态")
        print()
        
    def _print_system_info(self):
        """打印系统信息"""
        print("[系统信息]")
        print("-" * 60)
        
        # 线程信息 - 并排显示
        active_threads = threading.active_count()
        
        # 重连线程状态
        reconnect_threads = 0
        if hasattr(self.tcp_manager, 'reconnect_threads'):
            reconnect_threads = len([t for t in self.tcp_manager.reconnect_threads.values() if t.is_alive()])
        
        print(f"[活动线程数] {active_threads:<8} | [重连线程数] {reconnect_threads}")
        
        print()
        print("[提示] 按 Ctrl+C 退出服务 | [日志文件] logs/vda5050_server.log")
        print("=" * 120)
        
    def _get_last_communication_time(self, agv_id: str) -> str:
        """获取最后通信时间"""
        try:
            # 这里可以根据实际情况获取最后通信时间
            # 暂时返回当前时间
            return datetime.now().strftime('    %H:%M:%S')
        except:
            return "无数据"
    
    def _get_cpu_load(self) -> Dict[str, float]:
        """获取CPU负载信息"""
        try:
            
            # 获取CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 获取CPU核心数
            cpu_count = psutil.cpu_count()
            
            # 获取每个核心的使用率
            cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            
            # 获取内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 获取磁盘使用率（Windows和Linux路径不同）
            try:
                if os.name == 'nt':  # Windows
                    disk = psutil.disk_usage('C:\\')
                else:  # Linux/Unix
                    disk = psutil.disk_usage('/')
                disk_percent = disk.percent
            except:
                disk_percent = 0.0
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'cpu_per_core': cpu_per_core,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent
            }
        except Exception as e:
            logger.error(f"获取CPU负载信息失败: {e}")
            return {
                'cpu_percent': 0.0,
                'cpu_count': 0,
                'cpu_per_core': [],
                'memory_percent': 0.0,
                'disk_percent': 0.0
            }
    

    
    def _print_cpu_load_info(self):
        """打印CPU负载信息"""
        try:
            # 获取CPU负载信息
            cpu_info = self._get_cpu_load()
            

            
            # 合并为一行显示
            cpu_percent = cpu_info['cpu_percent']
            memory_percent = cpu_info['memory_percent']
            disk_percent = cpu_info['disk_percent']
            cpu_count = cpu_info['cpu_count']
            print(f"[CPU 综合负载监控] CPU: {cpu_percent:5.1f}% | 内存: {memory_percent:5.1f}% | 磁盘: {disk_percent:5.1f}% | 核心: {cpu_count}")
            print()
        except Exception as e:
            logger.error(f"显示CPU负载信息失败: {e}")
            print("[错误] CPU负载信息显示失败")
            print()
    






class TCPClientManager:
    """TCP客户端管理器 - 主动连接到AGV"""
    
    def __init__(self):
        self.connections = {}  # {agv_id: {port: socket}}
        self.is_running = False
        self.all_agv_configs = {}  # {agv_id: config}
        self.failed_agvs = []  # 连接失败的AGV列表
        self.reconnect_threads = {}
        self.polling_thread = None
        
        # 数据缓冲区 - 用于处理TCP粘包问题
        self.data_buffers = {}  # {agv_id: {port: bytes}}
        
        # 扫描并加载所有AGV配置
        try:
            self.all_agv_configs = self._scan_all_agv_configs()
            logger.info(f"成功加载 {len(self.all_agv_configs)} 个AGV配置")
            
            # 只在调试模式下显示详细配置信息
            if logger.isEnabledFor(logging.DEBUG):
                for agv_id, config in self.all_agv_configs.items():
                    network = config.get('network', {})
                    robot_info = config.get('robot_info', {})
                    logger.debug(f"AGV配置: {agv_id} - IP: {network.get('ip_address', '未配置')} - 制造商: {robot_info.get('manufacturer', '未知')}")
                
        except Exception as e:
            logger.error(f"加载AGV配置失败: {e}")
            self.all_agv_configs = {}
        
        # 如果没有配置文件，创建一个默认的调试信息
        if not self.all_agv_configs:
            logger.warning("未找到任何AGV配置文件，请检查robot_config目录")
        

    
    def _scan_all_agv_configs(self) -> Dict[str, Dict]:
        """扫描robot_config文件夹下的所有AGV配置文件（优化版）"""
        configs = {}
        config_dir = "robot_config"
        
        if not os.path.exists(config_dir):
            logger.error(f"配置目录不存在: {config_dir}")
            return configs
        
        try:
            files = [f for f in os.listdir(config_dir) if f.endswith(('.yaml', '.yml'))]
            logger.info(f"发现 {len(files)} 个配置文件")
            
            for filename in files:
                config_path = os.path.join(config_dir, filename)
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    
                    if not config_data:
                        logger.warning(f"配置文件为空: {filename}")
                        continue
                    
                    # 提取AGV ID
                    robot_info = config_data.get('robot_info', {})
                    agv_id = robot_info.get('serial_number', filename.split('.')[0])
                    
                    # 验证必要的配置项
                    network = config_data.get('network', {})
                    ip_address = network.get('ip_address')
                    
                    if not ip_address:
                        logger.warning(f"配置文件 {filename} 缺少IP地址配置")
                    
                    configs[agv_id] = config_data
                    logger.debug(f"成功加载AGV配置: {agv_id} <- {filename}")
                    
                except yaml.YAMLError as e:
                    logger.error(f"YAML解析错误 {config_path}: {e}")
                except Exception as e:
                    logger.error(f"加载配置文件失败 {config_path}: {e}")
                    
        except Exception as e:
            logger.error(f"扫描配置目录失败: {e}")
        
        return configs
    
    def start(self):
        """启动TCP客户端管理器"""
        self.is_running = True
        
        # 尝试连接所有AGV
        self._connect_all_agvs()
        
        # 启动重连轮询线程
        self.polling_thread = threading.Thread(target=self._polling_reconnect, daemon=True)
        self.polling_thread.start()
        
        logger.info("TCP客户端管理器已启动")
    
    def stop(self):
        """停止TCP客户端管理器"""
        self.is_running = False
        
        # 停止所有连接
        for agv_id in list(self.connections.keys()):
            self._disconnect_agv(agv_id)
        
        # 等待轮询线程结束
        if self.polling_thread:
            self.polling_thread.join(timeout=2.0)
        
        logger.info("TCP客户端管理器已停止")
    
    def _connect_all_agvs(self):
        """尝试连接所有AGV（并行优化版）"""
        def connect_single_agv(agv_id, config):
            success = self._connect_agv(agv_id, config)
            if not success:
                self.failed_agvs.append(agv_id)
            return agv_id, success
        
        # 并行连接所有AGV
        with ThreadPoolExecutor(max_workers=min(len(self.all_agv_configs), 4)) as executor:
            futures = [
                executor.submit(connect_single_agv, agv_id, config) 
                for agv_id, config in self.all_agv_configs.items()
            ]
            # 等待所有连接完成
            for future in futures:
                future.result()
    
    def _connect_agv(self, agv_id: str, config: Dict) -> bool:
        """连接单个AGV（动态端口版）"""
        try:
            ip_address = config.get('network', {}).get('ip_address')
            if not ip_address:
                logger.error(f"AGV {agv_id} 未配置IP地址")
                return False

            # 动态提取端口
            ports = []
            tcp_ports = config.get('protocol_adapters', {}).get('seer', {}).get('tcp_ports', {})
            # state_reporting
            if 'state_reporting' in tcp_ports:
                ports.append(tcp_ports['state_reporting'])
            # command_control
            cc = tcp_ports.get('command_control', {})
            for key in ['relocation', 'movement', 'authority', 'safety']:
                if key in cc:
                    ports.append(cc[key])
            ports = list(set(ports))  # 去重

            if not ports:
                logger.error(f"AGV {agv_id} 未配置任何端口")
                return False

            connected_ports = []

            def connect_port(port):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.0)
                    result = sock.connect_ex((ip_address, port))
                    if result == 0:
                        return port, sock
                    else:
                        sock.close()
                        return port, None
                except Exception as e:
                    logger.debug(f"连接AGV {agv_id}:{port} 失败: {e}")
                    return port, None

            with ThreadPoolExecutor(max_workers=len(ports)) as executor:
                futures = [executor.submit(connect_port, port) for port in ports]
                results = [future.result() for future in futures]

            for port, sock in results:
                if sock:
                    if agv_id not in self.connections:
                        self.connections[agv_id] = {}
                    self.connections[agv_id][port] = sock
                    connected_ports.append(port)
                    recv_thread = threading.Thread(
                        target=self._receive_data,
                        args=(agv_id, port, sock),
                        daemon=True
                    )
                    recv_thread.start()

            if connected_ports:
                logger.info(f"AGV {agv_id} 连接成功，端口: {connected_ports}")
                if agv_id in self.failed_agvs:
                    self.failed_agvs.remove(agv_id)
                if hasattr(self, 'vda5050_server') and self.vda5050_server:
                    self.vda5050_server._on_agv_connected(agv_id)
                return True
            else:
                logger.warning(f"AGV {agv_id} 所有端口连接失败")
                return False

        except Exception as e:
            logger.error(f"连接AGV {agv_id} 时发生错误: {e}")
            return False
    
    def _disconnect_agv(self, agv_id: str):
        """断开AGV连接"""
        if agv_id in self.connections:
            for port, sock in self.connections[agv_id].items():
                try:
                    sock.close()
                except:
                    pass
            del self.connections[agv_id]
            logger.info(f"AGV {agv_id} 连接已断开")
            
            # 通知VDA5050服务器AGV已断开连接
            if hasattr(self, 'vda5050_server') and self.vda5050_server:
                self.vda5050_server._on_agv_disconnected(agv_id)
    
    def _polling_reconnect(self):
        """轮询重连失败的AGV"""
        while self.is_running:
            try:
                if self.failed_agvs:
                    logger.info(f"尝试重连失败的AGV: {self.failed_agvs}")
                    
                    # 复制列表以避免迭代时修改
                    failed_copy = self.failed_agvs.copy()
                    
                    for agv_id in failed_copy:
                        if agv_id in self.all_agv_configs:
                            config = self.all_agv_configs[agv_id]
                            success = self._connect_agv(agv_id, config)
                            if success:
                                logger.info(f"AGV {agv_id} 重连成功")
                
                # 等待30秒后再次尝试
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"重连轮询错误: {e}")
                time.sleep(5)
    
    def _receive_data(self, agv_id: str, port: int, sock: socket.socket):
        """接收AGV数据"""
        try:
            # 初始化数据缓冲区
            if agv_id not in self.data_buffers:
                self.data_buffers[agv_id] = {}
            if port not in self.data_buffers[agv_id]:
                self.data_buffers[agv_id][port] = b''
            
            while self.is_running:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    
                    # 将数据添加到缓冲区
                    self.data_buffers[agv_id][port] += data
                    
                    # 处理缓冲区中的完整数据包
                    self._process_buffered_data(agv_id, port)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"接收AGV {agv_id}:{port} 数据错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"AGV {agv_id}:{port} 接收线程错误: {e}")
        finally:
            # 清理连接和缓冲区
            if agv_id in self.connections and port in self.connections[agv_id]:
                try:
                    sock.close()
                except:
                    pass
                del self.connections[agv_id][port]
                
                # 清理数据缓冲区
                if agv_id in self.data_buffers and port in self.data_buffers[agv_id]:
                    del self.data_buffers[agv_id][port]
                
                # 如果没有其他连接，将AGV加入失败列表
                if not self.connections[agv_id]:
                    del self.connections[agv_id]
                    if agv_id not in self.failed_agvs:
                        self.failed_agvs.append(agv_id)
                        
                        # 通知VDA5050服务器AGV已断开连接
                        if hasattr(self, 'vda5050_server') and self.vda5050_server:
                            self.vda5050_server._on_agv_disconnected(agv_id)
    
    def _process_buffered_data(self, agv_id: str, port: int):
        """处理缓冲区中的数据，检测并提取完整的数据包"""
        try:
            buffer = self.data_buffers[agv_id][port]
            
            while len(buffer) >= 16:  # 最小数据包大小
                # 查找同步头 0x5A
                sync_pos = buffer.find(0x5A)
                if sync_pos == -1:
                    # 没有找到同步头，清空缓冲区
                    buffer = b''
                    break
                
                # 移除同步头之前的无效数据
                if sync_pos > 0:
                    buffer = buffer[sync_pos:]
                
                # 检查是否有足够的数据来读取头部
                if len(buffer) < 16:
                    break
                
                try:
                    # 解析数据包头部（按照虚拟AGV的协议格式）
                    # 格式：同步头(1B) + 版本(1B) + 序列号(2B) + 数据长度(4B) + 消息类型(2B) + 保留字段(6B)
                    sync_header = buffer[0]
                    version = buffer[1]
                    sequence = int.from_bytes(buffer[2:4], byteorder='big')
                    data_length = int.from_bytes(buffer[4:8], byteorder='big')
                    message_type = int.from_bytes(buffer[8:10], byteorder='big')
                    
                    # 验证数据长度是否合理 (1-100KB)
                    if data_length < 1 or data_length > 100000:
                        # 数据长度不合理，跳过这个字节继续查找
                        buffer = buffer[1:]
                        continue
                    
                    # 检查是否有完整的数据包
                    total_packet_size = 16 + data_length  # 头部16字节 + 数据长度
                    if len(buffer) < total_packet_size:
                        # 数据包不完整，等待更多数据
                        break
                    
                    # 提取完整的数据包
                    packet_data = buffer[16:16+data_length]  # 跳过16字节头部
                    
                    # 处理数据包
                    self._process_complete_packet(agv_id, port, {
                        'sync_header': sync_header,
                        'data_length': data_length,
                        'message_type': message_type,
                        'data': packet_data
                    })
                    
                    # 从缓冲区移除已处理的数据包
                    buffer = buffer[total_packet_size:]
                    
                except Exception as e:
                    logger.error(f"解析数据包头部失败: {e}")
                    # 跳过这个字节继续查找
                    buffer = buffer[1:]
                    continue
            
            # 更新缓冲区
            self.data_buffers[agv_id][port] = buffer
            
        except Exception as e:
            logger.error(f"处理缓冲数据失败 AGV {agv_id}:{port}: {e}")
    
    def _process_complete_packet(self, agv_id: str, port: int, packet_info: Dict):
        """处理完整的数据包"""
        try:
            sync_header = packet_info['sync_header']
            data_length = packet_info['data_length']
            message_type = packet_info['message_type']
            raw_data = packet_info['data']
            
            logger.debug(f"处理完整数据包 AGV {agv_id}:{port} - 同步头:0x{sync_header:02X}, 长度:{data_length}, 类型:{message_type}")
            
            # 根据端口类型处理数据
            if port == 19301:  # 状态上报端口
                self._process_state_data(agv_id, raw_data, message_type)
            elif port == 19205:  # 重定位端口
                self._process_relocation_data(agv_id, raw_data)
            elif port == 19206:  # 移动控制端口
                self._process_movement_data(agv_id, raw_data)
            elif port == 19207:  # 权限控制端口
                self._process_authority_data(agv_id, raw_data)
            elif port == 19210:  # 安全端口
                self._process_safety_data(agv_id, raw_data)
            else:
                logger.warning(f"未知端口 {port} 的数据")
                
        except Exception as e:
            logger.error(f"处理完整数据包失败 AGV {agv_id}:{port}: {e}")
    
    def _process_state_data(self, agv_id: str, data: bytes, message_type: int = None):
        """处理状态数据并发布到MQTT（修正版，直接处理payload数据）"""
        try:
            # data参数已经是从TCP包中提取出来的payload数据（不包含包头）
            # 尝试将payload解析为JSON
            try:
                json_str = data.decode('utf-8')
                json_data = json.loads(json_str)
                
                logger.info(f"成功解析AGV {agv_id} 状态JSON数据")
                logger.info(f"AGV {agv_id} 状态数据: {json_data}")
                
                # 转换为VDA5050格式并发布
                if hasattr(self, 'vda5050_server') and self.vda5050_server:
                    vda5050_data = self._convert_huaqing_to_vda5050(json_data, agv_id)
                    self.vda5050_server.publish_state_message(agv_id, vda5050_data)
                    # 同时发布可视化数据
                    if 'position' in json_data or 'agv_position' in json_data:
                        self.vda5050_server.publish_visualization_message(agv_id, vda5050_data)
                        
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                # 如果无法解析为JSON，尝试其他格式
                logger.warning(f"AGV {agv_id} 状态数据不是有效的JSON: {e}")
                logger.debug(f"原始数据: {data.hex()}")
                
                # 尝试解析为文本
                try:
                    text_str = data.decode('utf-8', errors='ignore')
                    logger.info(f"AGV {agv_id} 状态文本数据: {text_str}")
                except Exception as text_e:
                    logger.warning(f"AGV {agv_id} 状态数据无法解析为文本: {text_e}")
                    
        except Exception as e:
            logger.error(f"处理状态数据失败: {e}")
            logger.debug(f"原始数据: {data.hex()}")
    
    def _process_relocation_data(self, agv_id: str, data: bytes):
        """处理重定位数据"""
        logger.debug(f"处理重定位数据 AGV {agv_id}: {len(data)} bytes")
    
    def _process_movement_data(self, agv_id: str, data: bytes):
        """处理移动控制数据"""
        logger.debug(f"处理移动控制数据 AGV {agv_id}: {len(data)} bytes")
    
    def _process_authority_data(self, agv_id: str, data: bytes):
        """处理权限控制数据"""
        logger.debug(f"处理权限控制数据 AGV {agv_id}: {len(data)} bytes")
    
    def _process_safety_data(self, agv_id: str, data: bytes):
        """处理安全数据"""
        logger.debug(f"处理安全数据 AGV {agv_id}: {len(data)} bytes")

    def _convert_huaqing_to_vda5050(self, huaqing_data: Dict, agv_id: str) -> Dict:
        """将HUAQING AGV数据转换为VDA5050格式"""
        try:
            # 获取AGV配置
            agv_config = self.all_agv_configs.get(agv_id, {})
            robot_info = agv_config.get('robot_info', {})
            
            # 基础VDA5050状态数据
            vda5050_data = {
                "orderId": "",
                "orderUpdateId": 0,
                "zoneSetId": "",
                "lastNodeId": "",
                "lastNodeSequenceId": 0,
                "driving": huaqing_data.get('task_status', 0) > 0,
                "paused": huaqing_data.get('pause', False),
                "newBaseRequest": False,
                "distanceSinceLastNode": 0.0,
                "operatingMode": "AUTOMATIC",
                "nodeStates": [],
                "edgeStates": [],
                "actionStates": [],
                "errors": [],
                "information": []
            }
            
            # 处理位置信息
            if 'agv_position' in huaqing_data:
                pos_data = huaqing_data['agv_position']
                vda5050_data["agvPosition"] = {
                    "x": pos_data.get('x', 0.0),
                    "y": pos_data.get('y', 0.0),
                    "theta": pos_data.get('yaw', 0.0),
                    "mapId": pos_data.get('map_id', 'warehouse_map_001'),
                    "positionInitialized": True,
                    "localizationScore": 1.0,
                    "deviationRange": 0.1
                }
            
            # 处理速度信息
            if 'velocity' in huaqing_data:
                vel_data = huaqing_data['velocity']
                vda5050_data["velocity"] = {
                    "vx": vel_data.get('vx', 0.0),
                    "vy": vel_data.get('vy', 0.0),
                    "omega": vel_data.get('omega', 0.0)
                }
            
            # 处理电池信息
            if 'battery_percentage' in huaqing_data:
                vda5050_data["batteryState"] = {
                    "batteryCharge": huaqing_data.get('battery_percentage', 0.0),
                    "batteryVoltage": huaqing_data.get('battery_voltage', 0.0),
                    "charging": huaqing_data.get('auto_charge', False)
                }
            
            # 处理载荷信息
            vda5050_data["loads"] = []
            
            # 处理安全状态
            vda5050_data["safetyState"] = {
                "eStop": "NONE",
                "fieldViolation": False
            }
            
            return vda5050_data
            
        except Exception as e:
            logger.error(f"转换HUAQING数据到VDA5050格式失败: {e}")
            return {}
    
    def get_connected_agvs(self) -> List[str]:
        """获取已连接的AGV列表"""
        return list(self.connections.keys())
    
    def send_to_agv(self, agv_id: str, port: int, data: Dict[str, Any]) -> bool:
        """发送数据到指定AGV"""
        if agv_id not in self.connections:
            logger.warning(f"AGV {agv_id} 未连接")
            return False
        
        if port not in self.connections[agv_id]:
            logger.warning(f"AGV {agv_id} 端口 {port} 未连接")
            return False
        
        try:
            sock = self.connections[agv_id][port]
            
            # 使用TCP协议构建二进制数据包
            if TCP_MODULES_AVAILABLE:
                # 创建TCP协议处理器
                tcp_protocol = ManufacturerATCPProtocol()
                
                # 将VDA5050数据转换为TCP消息格式
                # 根据端口确定消息类型
                if port == 19206:  # 订单端口
                    message_type = 3000  # VDA5050订单消息类型
                elif port == 19207:  # 即时动作端口
                    message_type = 4000  # VDA5050即时动作消息类型
                else:
                    message_type = 3000  # 默认订单类型
                
                # 构建TCP消息
                tcp_message = tcp_protocol.create_binary_tcp_packet(message_type, data)
                
                # 发送二进制数据包
                sock.send(tcp_message)
                logger.debug(f"发送TCP数据包到AGV {agv_id}:{port} (类型:{message_type:02X}): {len(tcp_message)}字节")
            else:
                # 降级处理：直接发送JSON
                json_data = json.dumps(data, ensure_ascii=False)
                packet = json_data.encode('utf-8')
                sock.send(packet)
                logger.warning(f"TCP模块不可用，直接发送JSON到AGV {agv_id}:{port}")
            
            return True
                
        except Exception as e:
            logger.error(f"发送数据到AGV {agv_id}:{port} 失败: {e}")
            return False
    
    def send_to_agv_with_type(self, agv_id: str, port: int, message_type: int, data: Dict[str, Any]) -> bool:
        """发送带消息类型的数据到指定AGV"""
        if agv_id not in self.connections:
            logger.warning(f"AGV {agv_id} 未连接")
            return False
        
        if port not in self.connections[agv_id]:
            logger.warning(f"AGV {agv_id} 端口 {port} 未连接")
            return False
        
        try:
            sock = self.connections[agv_id][port]
            
            # 使用TCP协议构建二进制数据包
            if TCP_MODULES_AVAILABLE:
                # 创建TCP协议处理器
                tcp_protocol = ManufacturerATCPProtocol()
                
                # 构建TCP消息
                tcp_message = tcp_protocol.create_binary_tcp_packet(message_type, data)
                
                # 发送二进制数据包
                sock.send(tcp_message)
                logger.debug(f"发送TCP数据包到AGV {agv_id}:{port} (类型:{message_type:02X}): {len(tcp_message)}字节")
            else:
                # 降级处理：直接发送JSON
                data_with_type = {"message_type": message_type, "data": data}
                json_data = json.dumps(data_with_type, ensure_ascii=False)
                packet = json_data.encode('utf-8')
                sock.send(packet)
                logger.warning(f"TCP模块不可用，直接发送JSON到AGV {agv_id}:{port}")
            
            return True
                
        except Exception as e:
            logger.error(f"发送数据到AGV {agv_id}:{port} 失败: {e}")
            return False
                



class VDA5050Server:
    """VDA5050服务器 - 处理MQTT和TCP之间的消息转换"""
    
    def __init__(self, mqtt_config: Dict[str, Any]):
        self.mqtt_config = mqtt_config
        self.mqtt_client = None
        self.is_running = False
        self.tcp_manager = None  # 添加TCP管理器引用
        self.display = DynamicTableDisplay()
        
        # 初始化MQTT客户端
        self._init_mqtt_client()
    
    def set_tcp_manager(self, tcp_manager):
        """设置TCP管理器引用"""
        self.tcp_manager = tcp_manager
        tcp_manager.vda5050_server = self  # 设置反向引用
    
    def _init_mqtt_client(self):
        """初始化MQTT客户端"""
        try:
            # 使用配置中的客户端ID前缀
            client_id_prefix = self.mqtt_config.get('client_id_prefix', 'vda5050_server')
            client_id = f"{client_id_prefix}_{int(time.time())}"
            self.mqtt_client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            
            # 设置回调函数
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            # 连接到MQTT代理
            self.mqtt_client.connect(
                self.mqtt_config['host'],
                self.mqtt_config['port'],
                self.mqtt_config.get('keepalive', 60)
            )
            
            # 启动MQTT循环
            self.mqtt_client.loop_start()
            
        except Exception as e:
            logger.error(f"初始化MQTT客户端失败: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT连接回调"""
        if rc == 0:
            logger.info("MQTT连接成功")
            # 订阅VDA5050主题
            self._subscribe_vda5050_topics()
        else:
            logger.error(f"MQTT连接失败，错误代码: {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, flags, rc, properties=None):
        """MQTT断开连接回调"""
        logger.warning(f"MQTT连接断开，错误代码: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"收到MQTT消息: {topic}")
            
            # 解析VDA5050消息并转换为TCP
            self._process_vda5050_message(topic, payload)
                
        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")
    
    def _subscribe_vda5050_topics(self):
        """订阅VDA5050主题"""
        try:
            # 订阅所有AGV的order和instantActions主题
            topics = [
                "uagv/v2/+/+/order",
                "uagv/v2/+/+/instantActions"
            ]
            
            for topic in topics:
                self.mqtt_client.subscribe(topic)
                logger.info(f"订阅MQTT主题: {topic}")
                    
        except Exception as e:
            logger.error(f"订阅MQTT主题失败: {e}")
    
    def _process_vda5050_message(self, topic: str, payload: str):
        """处理VDA5050消息"""
        try:
            # 解析主题
            topic_parts = topic.split('/')
            if len(topic_parts) < 5:
                logger.warning(f"无效的主题格式: {topic}")
                return
            
            manufacturer = topic_parts[2]
            serial_number = topic_parts[3]
            message_type = topic_parts[4]
            
            # 解析JSON数据
            data = json.loads(payload)
            
            # 根据消息类型处理
            if message_type == "order":
                self._process_order_message(manufacturer, serial_number, data)
            elif message_type == "instantActions":
                self._process_instant_actions_message(manufacturer, serial_number, data)
                    
        except Exception as e:
            logger.error(f"处理VDA5050消息失败: {e}")
    
    def _process_order_message(self, manufacturer: str, serial_number: str, data: Dict):
        """处理订单消息"""
        try:
            # 简化处理：直接转发JSON数据
            agv_id = serial_number
            if agv_id in self.tcp_manager.get_connected_agvs():
                self.tcp_manager.send_to_agv(agv_id, 19206, data)
                logger.info(f"发送订单到AGV {agv_id}")
            else:
                logger.warning(f"AGV {agv_id} 未连接，无法发送订单")
                
        except Exception as e:
            logger.error(f"处理订单消息失败: {e}")
    
    def _process_instant_actions_message(self, manufacturer: str, serial_number: str, data: Dict):
        """处理即时动作消息"""
        try:
            # 简化处理：直接转发JSON数据
            agv_id = serial_number
            if agv_id in self.tcp_manager.get_connected_agvs():
                # 根据动作类型选择端口
                port = 19206  # 默认端口
                self.tcp_manager.send_to_agv(agv_id, port, data)
                logger.info(f"发送即时动作到AGV {agv_id}")
            else:
                logger.warning(f"AGV {agv_id} 未连接，无法发送即时动作")
                
        except Exception as e:
            logger.error(f"处理即时动作消息失败: {e}")
    
    def start(self):
        """启动服务器（优化版）"""
        self.is_running = True
        
        # 启动TCP管理器
        self.tcp_manager.start()
        
        # 延迟启动动态显示，避免启动时阻塞
        def start_display_delayed():
            time.sleep(2)  # 等待2秒让连接稳定
            if self.is_running and self.display:
                self.display.start_display(self.tcp_manager, self.mqtt_client)
        
        if self.display:  # 只有在显示对象存在时才启动显示线程
            display_thread = threading.Thread(target=start_display_delayed, daemon=True)
            display_thread.start()
        
        logger.info("VDA5050服务器已启动")
    
    def stop(self):
        """停止服务器"""
        self.is_running = False
        
        # 停止动态显示
        self.display.stop_display()
        
        # 停止TCP管理器
        self.tcp_manager.stop()
        
        # 停止MQTT客户端
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        logger.info("VDA5050服务器已停止")

    def publish_state_message(self, agv_id: str, data: Dict[str, Any]):
        """发布状态消息到MQTT"""
        try:
            if not self.mqtt_client:
                return
            
            # 获取AGV配置信息
            agv_config = self.tcp_manager.all_agv_configs.get(agv_id, {})
            robot_info = agv_config.get('robot_info', {})
            manufacturer = robot_info.get('manufacturer', 'UNKNOWN')
            serial_number = robot_info.get('serial_number', agv_id)
            
            # 构建VDA5050状态消息
            state_message = {
                "headerId": int(time.time()),
                "timestamp": datetime.now().isoformat() + "Z",
                "version": "2.0.0",
                "manufacturer": manufacturer,
                "serialNumber": serial_number,
                "orderId": data.get('orderId', ''),
                "orderUpdateId": data.get('orderUpdateId', 0),
                "zoneSetId": data.get('zoneSetId', ''),
                "lastNodeId": data.get('lastNodeId', ''),
                "lastNodeSequenceId": data.get('lastNodeSequenceId', 0),
                "driving": data.get('driving', False),
                "paused": data.get('paused', False),
                "newBaseRequest": data.get('newBaseRequest', False),
                "distanceSinceLastNode": data.get('distanceSinceLastNode', 0.0),
                "operatingMode": data.get('operatingMode', 'AUTOMATIC'),
                "nodeStates": data.get('nodeStates', []),
                "edgeStates": data.get('edgeStates', []),
                "agvPosition": data.get('agvPosition', {}),
                "velocity": data.get('velocity', {}),
                "loads": data.get('loads', []),
                "actionStates": data.get('actionStates', []),
                "batteryState": data.get('batteryState', {}),
                "errors": data.get('errors', []),
                "information": data.get('information', []),
                "safetyState": data.get('safetyState', {})
            }
            
            # 发布状态消息
            topic = f"uagv/v2/{manufacturer}/{serial_number}/state"
            self.mqtt_client.publish(topic, json.dumps(state_message, ensure_ascii=False))
            logger.debug(f"发布状态消息到MQTT: {topic}")
            
        except Exception as e:
            logger.error(f"发布状态消息失败: {e}")
    
    def publish_connection_message(self, agv_id: str, connection_state: str):
        """发布连接消息到MQTT"""
        try:
            if not self.mqtt_client:
                return
            
            # 获取AGV配置信息
            agv_config = self.tcp_manager.all_agv_configs.get(agv_id, {})
            robot_info = agv_config.get('robot_info', {})
            manufacturer = robot_info.get('manufacturer', 'UNKNOWN')
            serial_number = robot_info.get('serial_number', agv_id)
            
            # 构建VDA5050连接消息
            connection_message = {
                "headerId": int(time.time()),
                "timestamp": datetime.now().isoformat() + "Z",
                "version": "2.0.0",
                "manufacturer": manufacturer,
                "serialNumber": serial_number,
                "connectionState": connection_state
            }
            
            # 发布连接消息
            topic = f"uagv/v2/{manufacturer}/{serial_number}/connection"
            self.mqtt_client.publish(topic, json.dumps(connection_message, ensure_ascii=False))
            logger.info(f"发布连接消息到MQTT: {topic} -> {connection_state}")
            
        except Exception as e:
            logger.error(f"发布连接消息失败: {e}")
    
    def publish_factsheet_message(self, agv_id: str):
        """发布产品说明书消息到MQTT"""
        try:
            if not self.mqtt_client:
                return
            
            # 获取AGV配置信息
            agv_config = self.tcp_manager.all_agv_configs.get(agv_id, {})
            robot_info = agv_config.get('robot_info', {})
            manufacturer = robot_info.get('manufacturer', 'UNKNOWN')
            serial_number = robot_info.get('serial_number', agv_id)
            
            # 构建VDA5050产品说明书消息
            factsheet_message = {
                "headerId": int(time.time()),
                "timestamp": datetime.now().isoformat() + "Z",
                "version": "2.0.0",
                "manufacturer": manufacturer,
                "serialNumber": serial_number,
                "typeSpecification": agv_config.get('physical_parameters', {}).get('type_specification', {}),
                "physicalParameters": agv_config.get('physical_parameters', {}),
                "protocolLimits": agv_config.get('vda5050', {}).get('protocol_limits', {}),
                "protocolFeatures": agv_config.get('vda5050', {}).get('protocol_features', {}),
                "agvGeometry": agv_config.get('physical_parameters', {}).get('agv_geometry', {}),
                "loadSpecification": agv_config.get('physical_parameters', {}).get('load_specification', {})
            }
            
            # 发布产品说明书消息
            topic = f"uagv/v2/{manufacturer}/{serial_number}/factsheet"
            self.mqtt_client.publish(topic, json.dumps(factsheet_message, ensure_ascii=False))
            logger.info(f"发布产品说明书消息到MQTT: {topic}")
            
        except Exception as e:
            logger.error(f"发布产品说明书消息失败: {e}")
    
    def publish_visualization_message(self, agv_id: str, data: Dict[str, Any]):
        """发布可视化消息到MQTT"""
        try:
            if not self.mqtt_client:
                return
            
            # 获取AGV配置信息
            agv_config = self.tcp_manager.all_agv_configs.get(agv_id, {})
            robot_info = agv_config.get('robot_info', {})
            manufacturer = robot_info.get('manufacturer', 'UNKNOWN')
            serial_number = robot_info.get('serial_number', agv_id)
            
            # 构建VDA5050可视化消息
            visualization_message = {
                "headerId": int(time.time()),
                "timestamp": datetime.now().isoformat() + "Z",
                "version": "2.0.0",
                "manufacturer": manufacturer,
                "serialNumber": serial_number,
                "agvPosition": data.get('agvPosition', {}),
                "velocity": data.get('velocity', {}),
                "loads": data.get('loads', [])
            }
            
            # 发布可视化消息
            topic = f"uagv/v2/{manufacturer}/{serial_number}/visualization"
            self.mqtt_client.publish(topic, json.dumps(visualization_message, ensure_ascii=False))
            logger.debug(f"发布可视化消息到MQTT: {topic}")
            
        except Exception as e:
            logger.error(f"发布可视化消息失败: {e}")
    
    def _on_agv_connected(self, agv_id: str):
        """AGV连接成功时的回调"""
        try:
            # 发布连接状态
            self.publish_connection_message(agv_id, "ONLINE")
            
            # 发布产品说明书（只在连接时发布一次）
            self.publish_factsheet_message(agv_id)
            
            logger.info(f"AGV {agv_id} 已连接，发布连接和产品说明书消息")
            
        except Exception as e:
            logger.error(f"处理AGV连接事件失败: {e}")
    
    def _on_agv_disconnected(self, agv_id: str):
        """AGV断开连接时的回调"""
        try:
            # 发布离线状态
            self.publish_connection_message(agv_id, "OFFLINE")
            
            logger.info(f"AGV {agv_id} 已断开连接，发布离线状态")
            
        except Exception as e:
            logger.error(f"处理AGV断开连接事件失败: {e}")


def load_config() -> Optional[Dict[str, Any]]:
    """加载配置文件"""
    try:
        config_path = "mqtt_config/mqtt_config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
    return None


def main():
    """主函数"""
    print("启动VDA5050 MQTT-TCP桥接服务器...")
    
    # 加载配置
    config = load_config()
    if not config:
        print("无法加载配置文件")
        return
    
    # 创建VDA5050服务器
    vda5050_server = VDA5050Server(config.get('mqtt_server', {}))
    
    # 创建TCP客户端管理器
    tcp_manager = TCPClientManager()
    
    # 设置相互引用
    vda5050_server.set_tcp_manager(tcp_manager)
    
    try:
        # 启动服务器
        vda5050_server.start()
        
        print("服务器启动成功")
        print("按 Ctrl+C 停止服务器...")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭服务器...")
        vda5050_server.stop()
        print("服务器已停止")
    except Exception as e:
        print(f"服务器运行错误: {e}")
        vda5050_server.stop()

if __name__ == "__main__":
    main() 