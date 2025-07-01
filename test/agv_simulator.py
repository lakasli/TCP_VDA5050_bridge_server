#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGV模拟器 - 用于测试VDA5050-MQTT-TCP桥接服务器
模拟AGV的TCP客户端行为，包括连接服务器、发送状态数据、接收指令等
"""
import os
import json
import socket
import threading
import time
import random
import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, List

# 确保logs目录存在
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'agv_simulator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AGVSimulator:
    """AGV模拟器 - 基于VWED-0010.yaml配置"""
    
    def __init__(self, server_ip: str = 'localhost', agv_id: str = 'VWED-0010'):
        self.server_ip = server_ip
        self.agv_id = agv_id
        self.is_running = False
        self.connections = {}
        
        # AGV基本信息（对应配置文件robot_info）
        self.robot_info = {
            'vehicle_id': agv_id,
            'manufacturer': 'SEER',
            'serial_number': agv_id,
            'model': 'AGV-Virtual-Test',
            'firmware_version': 'v1.0.0',
            'hardware_version': 'v1.0.0'
        }
        
        # 物理参数（对应配置文件physical_parameters）
        self.physical_params = {
            'speed_min': 0.0,
            'speed_max': 2.0,
            'acceleration_max': 1.0,
            'deceleration_max': 1.5,
            'width': 0.8,
            'length': 1.2,
            'max_load_mass': 50.0,
            'turning_radius': 0.0
        }
        
        # AGV运行状态数据
        self.agv_state = {
            'vehicle_id': agv_id,
            'manufacturer': self.robot_info['manufacturer'],
            'model': self.robot_info['model'],
            'firmware_version': self.robot_info['firmware_version'],
            'position': {
                'x': random.uniform(0, 100),
                'y': random.uniform(0, 100),
                'theta': random.uniform(0, 360)
            },
            'velocity': {
                'vx': 0.0,
                'vy': 0.0,
                'omega': 0.0
            },
            'battery_level': random.randint(80, 100),
            'operating_mode': 'AUTOMATIC',
            'safety_state': 'NORMAL',
            'errors': [],
            'warnings': [],
            'current_task': None,
            'task_status': 'WAITING',
            'controller': None,
            'control_timestamp': None,
            'load_status': {
                'has_load': False,
                'load_weight': 0.0,
                'load_type': None
            }
        }
        
        # TCP端口配置（对应VWED-0010.yaml配置文件）
        self.tcp_ports = {
            19205: 'relocation',     # 重定位控制（navigation_control）
            19206: 'movement',       # 运动控制（motion_control）
            19207: 'authority',      # 权限控制（authority_control）
            19210: 'safety',         # 安全控制（safety_control）
            19301: 'state'           # 状态上报（state_reporting）
        }
        
    def start(self):
        """启动AGV模拟器"""
        logger.info(f"启动AGV模拟器 - ID: {self.agv_id}")
        self.is_running = True
        
        # 连接到所有TCP端口
        for port, port_type in self.tcp_ports.items():
            thread = threading.Thread(
                target=self._connect_to_port,
                args=(port, port_type),
                daemon=True
            )
            thread.start()
        
        # 启动状态上报线程
        state_thread = threading.Thread(
            target=self._state_reporter,
            daemon=True
        )
        state_thread.start()
        
        logger.info("AGV模拟器启动完成")
    
    def stop(self):
        """停止AGV模拟器"""
        logger.info("正在停止AGV模拟器...")
        self.is_running = False
        
        # 关闭所有连接
        for port, conn in self.connections.items():
            try:
                conn.close()
            except:
                pass
        
        logger.info("AGV模拟器已停止")
    
    def _connect_to_port(self, port: int, port_type: str):
        """连接到指定端口"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.server_ip, port))
            self.connections[port] = sock
            
            logger.info(f"连接成功 - 端口: {port}, 类型: {port_type}")
            
            # 监听服务器消息
            self._listen_for_messages(sock, port, port_type)
            
        except Exception as e:
            logger.error(f"连接失败 - 端口: {port}, 错误: {e}")
    
    def _listen_for_messages(self, sock: socket.socket, port: int, port_type: str):
        """监听服务器消息"""
        try:
            sock.settimeout(1.0)
            
            while self.is_running:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    
                    # 解析服务器消息
                    message = self._parse_tcp_message(data)
                    if message:
                        logger.info(f"收到服务器消息 - 端口: {port}, 类型: {port_type}")
                        logger.info(f"消息内容: {json.dumps(message, ensure_ascii=False, indent=2)}")
                        
                        # 处理不同类型的消息
                        self._handle_server_message(message, port_type)
                    else:
                        logger.warning(f"无法解析服务器消息 - 端口: {port}, 数据长度: {len(data)}")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"接收消息错误 - 端口: {port}, 错误: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"监听消息异常 - 端口: {port}, 错误: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
    
    def _parse_tcp_message(self, data: bytes) -> Dict[str, Any]:
        """解析TCP消息（支持JSON和二进制格式）"""
        try:
            # 首先尝试直接解析JSON格式
            try:
                json_str = data.decode('utf-8')
                return json.loads(json_str)
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            
            # 尝试解析二进制TCP数据包格式
            if len(data) < 16:
                logger.warning(f"数据包太短，长度: {len(data)}")
                return None
            
            # 解析包头 (16字节)
            sync_header = data[0]
            version = data[1]
            sequence = int.from_bytes(data[2:4], 'big')
            data_length = int.from_bytes(data[4:8], 'big')
            message_type = int.from_bytes(data[8:10], 'big')
            reserved = data[10:16]
            
            logger.info(f"解析TCP数据包 - 同步头: 0x{sync_header:02X}, 版本: {version}, 序列: {sequence}, 数据长度: {data_length}, 消息类型: {message_type}")
            
            # 提取数据部分
            if len(data) >= 16 + data_length:
                payload_data = data[16:16+data_length]
            else:
                payload_data = data[16:]
                logger.warning(f"数据包不完整，期望{data_length}字节，实际{len(payload_data)}字节")
            
            # 尝试解析JSON数据
            if payload_data:
                try:
                    payload_str = payload_data.decode('utf-8')
                    payload_json = json.loads(payload_str)
                    
                    # 返回解析后的消息结构
                    return {
                        'messageType': message_type,
                        'timestamp': payload_json.get('timestamp', 0),
                        'data': payload_json.get('data', {}),
                        'sequence': sequence,
                        'format': 'binary_tcp'
                    }
                except Exception as e:
                    logger.error(f"解析数据区JSON失败: {e}")
                    return {
                        'messageType': message_type,
                        'sequence': sequence,
                        'raw_data': payload_data.hex(),
                        'format': 'binary_tcp'
                    }
            
            return {
                'messageType': message_type,
                'sequence': sequence,
                'format': 'binary_tcp'
            }
            
        except Exception as e:
            logger.error(f"解析TCP消息失败: {e}")
            return None

    def _handle_server_message(self, message: Dict[str, Any], port_type: str):
        """处理服务器消息"""
        try:
            message_type = message.get('messageType', 0)
            logger.info(f"处理消息 - 端口类型: {port_type}, 消息类型: {message_type}")
            
            # 根据消息类型处理不同指令
            if message_type == 2002:  # 重定位
                self._handle_reloc_command(message)
            elif message_type == 2004:  # 取消重定位
                self._handle_cancel_reloc_command(message)
            elif message_type == 3001:  # 暂停任务
                self._handle_pause_command(message)
            elif message_type == 3002:  # 继续任务
                self._handle_resume_command(message)
            elif message_type == 3003:  # 取消订单
                self._handle_cancel_order_command(message)
            elif message_type == 3055:  # 平动
                self._handle_translate_command(message)
            elif message_type == 3056:  # 转动
                self._handle_turn_command(message)
            elif message_type == 3057:  # 托盘旋转
                self._handle_rotate_load_command(message)
            elif message_type == 3066:  # 托盘抬升/下降
                self._handle_pick_drop_command(message)
            elif message_type == 4005:  # 抢夺控制权
                self._handle_grab_control_command(message)
            elif message_type == 4009:  # 清除错误
                self._handle_clear_errors_command(message)
            elif message_type == 6004:  # 软急停
                self._handle_soft_emergency_command(message)
            else:
                logger.info(f"未知消息类型: {message_type}, 端口类型: {port_type}")
                self._handle_unknown_command(message)
                
        except Exception as e:
            logger.error(f"处理服务器消息失败: {e}")
    
    def _handle_pick_drop_command(self, message: Dict[str, Any]):
        """处理pick/drop指令"""
        logger.info("执行pick/drop指令")
        
        # 模拟执行时间
        execution_time = random.uniform(5, 15)
        logger.info(f"预计执行时间: {execution_time:.1f}秒")
        
        # 更新AGV状态
        self.agv_state['current_task'] = message
        self.agv_state['task_status'] = 'EXECUTING'
        
        # 模拟执行过程
        time.sleep(execution_time)
        
        # 完成任务
        self.agv_state['task_status'] = 'COMPLETED'
        self.agv_state['current_task'] = None
        
        logger.info("pick/drop指令执行完成")
    
    def _handle_translate_command(self, message: Dict[str, Any]):
        """处理translate指令（single_field格式，参数：dist）"""
        logger.info("执行translate指令")
        
        # 根据配置文件，translate使用single_field格式，参数名为dist
        distance = message.get('data', {}).get('value', 1.0)
        if isinstance(distance, str):
            try:
                distance = float(distance)
            except ValueError:
                distance = 1.0
        
        logger.info(f"移动距离: {distance:.2f}米")
        
        # 计算移动时间（基于最大速度）
        max_speed = self.physical_params['speed_max']
        move_time = distance / max_speed
        
        logger.info(f"最大速度: {max_speed}m/s, 预计时间: {move_time:.1f}秒")
        
        # 更新状态
        self.agv_state['current_task'] = message
        self.agv_state['task_status'] = 'EXECUTING'
        
        # 模拟移动（沿当前朝向前进）
        current_theta = math.radians(self.agv_state['position']['theta'])
        start_x = self.agv_state['position']['x']
        start_y = self.agv_state['position']['y']
        target_x = start_x + distance * math.cos(current_theta)
        target_y = start_y + distance * math.sin(current_theta)
        
        # 模拟移动过程
        steps = max(int(move_time * 10), 1)  # 每0.1秒更新一次位置
        for i in range(steps):
            if not self.is_running:
                break
            
            # 线性插值更新位置
            progress = (i + 1) / steps
            self.agv_state['position']['x'] = start_x + (target_x - start_x) * progress
            self.agv_state['position']['y'] = start_y + (target_y - start_y) * progress
            
            # 更新速度
            current_speed = distance / move_time * (1 - abs(0.5 - progress) * 2)  # 梯形速度曲线
            self.agv_state['velocity']['vx'] = current_speed * math.cos(current_theta)
            self.agv_state['velocity']['vy'] = current_speed * math.sin(current_theta)
            
            time.sleep(0.1)
        
        # 完成移动
        self.agv_state['position']['x'] = target_x
        self.agv_state['position']['y'] = target_y
        self.agv_state['velocity'] = {'vx': 0.0, 'vy': 0.0, 'omega': 0.0}
        self.agv_state['task_status'] = 'COMPLETED'
        self.agv_state['current_task'] = None
        
        logger.info("translate指令执行完成")
    
    def _handle_turn_command(self, message: Dict[str, Any]):
        """处理turn指令（single_field格式，参数：angle）"""
        logger.info("执行turn指令")
        
        # 根据配置文件，turn使用single_field格式，参数名为angle
        turn_angle = message.get('data', {}).get('value', 0.0)
        if isinstance(turn_angle, str):
            try:
                turn_angle = float(turn_angle)
            except ValueError:
                turn_angle = 0.0
        
        logger.info(f"转向角度: {turn_angle}°")
        
        # 计算转向时间（基于角速度限制）
        max_angular_speed = 90.0  # 度/秒
        turn_time = abs(turn_angle) / max_angular_speed
        
        logger.info(f"最大角速度: {max_angular_speed}°/s, 预计时间: {turn_time:.1f}秒")
        
        # 更新状态
        self.agv_state['current_task'] = message
        self.agv_state['task_status'] = 'EXECUTING'
        
        # 记录起始角度
        start_theta = self.agv_state['position']['theta']
        target_theta = start_theta + turn_angle
        
        # 模拟转向过程
        steps = max(int(turn_time * 10), 1)  # 每0.1秒更新一次角度
        for i in range(steps):
            if not self.is_running:
                break
            
            # 线性插值更新角度
            progress = (i + 1) / steps
            current_theta = start_theta + turn_angle * progress
            self.agv_state['position']['theta'] = current_theta % 360
            
            # 更新角速度
            current_omega = turn_angle / turn_time * (1 - abs(0.5 - progress) * 2)  # 梯形速度曲线
            self.agv_state['velocity']['omega'] = math.radians(current_omega)
            
            time.sleep(0.1)
        
        # 完成转向
        self.agv_state['position']['theta'] = target_theta % 360
        self.agv_state['velocity']['omega'] = 0.0
        self.agv_state['task_status'] = 'COMPLETED'
        self.agv_state['current_task'] = None
        
        logger.info(f"turn指令执行完成，当前角度: {self.agv_state['position']['theta']:.1f}°")
    
    def _handle_reloc_command(self, message: Dict[str, Any]):
        """处理reloc指令"""
        logger.info("执行reloc指令")
        
        # 模拟重定位过程
        reloc_time = random.uniform(10, 30)
        logger.info(f"重定位预计时间: {reloc_time:.1f}秒")
        
        self.agv_state['current_task'] = message
        self.agv_state['task_status'] = 'EXECUTING'
        
        time.sleep(reloc_time)
        
        # 更新位置（模拟重定位结果）
        self.agv_state['position']['x'] += random.uniform(-5, 5)
        self.agv_state['position']['y'] += random.uniform(-5, 5)
        self.agv_state['position']['theta'] += random.uniform(-10, 10)
        
        self.agv_state['task_status'] = 'COMPLETED'
        self.agv_state['current_task'] = None
        
        logger.info("reloc指令执行完成")
    
    def _handle_pause_command(self, message: Dict[str, Any]):
        """处理pause指令"""
        logger.info("执行pause指令")
        
        pause_duration = message.get('data', {}).get('duration', 10)
        logger.info(f"暂停时间: {pause_duration}秒")
        
        self.agv_state['current_task'] = message
        self.agv_state['task_status'] = 'PAUSED'
        
        time.sleep(pause_duration)
        
        self.agv_state['task_status'] = 'COMPLETED'
        self.agv_state['current_task'] = None
        
        logger.info("pause指令执行完成")
    
    def _handle_resume_command(self, message: Dict[str, Any]):
        """处理resume指令"""
        logger.info("执行resume指令")
        
        if self.agv_state['task_status'] == 'PAUSED':
            self.agv_state['task_status'] = 'EXECUTING'
            logger.info("任务已恢复执行")
        else:
            logger.info("当前没有暂停的任务")
        
        self.agv_state['current_task'] = None
    
    def _handle_cancel_reloc_command(self, message: Dict[str, Any]):
        """处理取消重定位指令"""
        logger.info("执行取消重定位指令")
        
        if self.agv_state['current_task'] and self.agv_state['task_status'] == 'EXECUTING':
            self.agv_state['task_status'] = 'CANCELLED'
            logger.info("重定位任务已取消")
        
        self.agv_state['current_task'] = None
    
    def _handle_cancel_order_command(self, message: Dict[str, Any]):
        """处理取消订单指令"""
        logger.info("执行取消订单指令")
        
        if self.agv_state['current_task']:
            self.agv_state['task_status'] = 'CANCELLED'
            logger.info("当前订单已取消")
        
        self.agv_state['current_task'] = None
    
    def _handle_rotate_load_command(self, message: Dict[str, Any]):
        """处理托盘旋转指令"""
        logger.info("执行托盘旋转指令")
        
        rotation_angle = message.get('data', {}).get('angle', 90)
        rotation_time = abs(rotation_angle) / 180  # 假设180度/秒
        
        logger.info(f"旋转角度: {rotation_angle}°, 预计时间: {rotation_time:.1f}秒")
        
        self.agv_state['current_task'] = message
        self.agv_state['task_status'] = 'EXECUTING'
        
        time.sleep(rotation_time)
        
        self.agv_state['task_status'] = 'COMPLETED'
        self.agv_state['current_task'] = None
        
        logger.info("托盘旋转指令执行完成")
    
    def _handle_grab_control_command(self, message: Dict[str, Any]):
        """处理抢夺控制权指令（single_field格式）"""
        logger.info("收到抢夺控制权指令")
        
        # 根据配置文件，grab_authority使用single_field格式: {"value": %value%}
        control_value = message.get('data', {}).get('value', '未知控制者')
        logger.info(f"控制权请求值: {control_value}")
        
        # 模拟抢夺控制权成功
        self.agv_state['controller'] = control_value
        self.agv_state['control_timestamp'] = time.time()
        
        logger.info(f"控制权已转移给: {control_value}")
        
        # 发送确认响应（release_authority格式，也是single_field）
        response = {
            'messageType': 4006,  # 控制权确认
            'timestamp': int(time.time() * 1000),
            'data': {
                'value': f"control_granted_to_{control_value}",
                'vehicle_id': self.agv_id,
                'status': 'success'
            }
        }
        
        logger.info(f"发送控制权确认: {json.dumps(response, ensure_ascii=False)}")
    
    def _handle_clear_errors_command(self, message: Dict[str, Any]):
        """处理清除错误指令"""
        logger.info("执行清除错误指令")
        
        cleared_errors = len(self.agv_state['errors'])
        cleared_warnings = len(self.agv_state['warnings'])
        
        self.agv_state['errors'].clear()
        self.agv_state['warnings'].clear()
        
        logger.info(f"已清除 {cleared_errors} 个错误和 {cleared_warnings} 个警告")
    
    def _handle_soft_emergency_command(self, message: Dict[str, Any]):
        """处理软急停指令"""
        logger.info("执行软急停指令")
        
        # 立即停止所有运动
        self.agv_state['velocity'] = {'vx': 0.0, 'vy': 0.0, 'omega': 0.0}
        self.agv_state['safety_state'] = 'EMERGENCY_STOP'
        self.agv_state['task_status'] = 'EMERGENCY_STOPPED'
        
        logger.info("AGV已进入紧急停止状态")
    
    def _handle_unknown_command(self, message: Dict[str, Any]):
        """处理未知指令"""
        message_type = message.get('messageType', 0)
        logger.info(f"收到未知指令，消息类型: {message_type}")
        logger.info(f"消息内容: {json.dumps(message, ensure_ascii=False, indent=2)}")
        
        # 发送未知指令响应
        response = {
            'messageType': 9999,  # 未知指令响应
            'timestamp': int(time.time() * 1000),
            'data': {
                'status': 'unknown_command',
                'original_message_type': message_type,
                'vehicle_id': self.agv_id
            }
        }
        
        logger.info(f"发送未知指令响应: {json.dumps(response, ensure_ascii=False)}")
    
    def _state_reporter(self):
        """状态上报线程"""
        while self.is_running:
            try:
                # 更新动态数据
                self._update_dynamic_state()
                
                # 向状态端口发送数据
                state_port = 19301
                if state_port in self.connections:
                    state_data = self._generate_state_data()
                    message = json.dumps(state_data, ensure_ascii=False)
                    
                    try:
                        self.connections[state_port].send(message.encode('utf-8'))
                        logger.info("状态数据已发送")
                    except Exception as e:
                        logger.error(f"发送状态数据失败: {e}")
                
                # 每2秒上报一次状态
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"状态上报异常: {e}")
                time.sleep(5)
    
    def _update_dynamic_state(self):
        """更新动态状态数据"""
        # 模拟电池消耗
        if self.agv_state['task_status'] == 'EXECUTING':
            self.agv_state['battery_level'] = max(0, self.agv_state['battery_level'] - 0.1)
        
        # 模拟小幅度位置变化（传感器噪声）
        if self.agv_state['task_status'] != 'EXECUTING':
            self.agv_state['position']['x'] += random.uniform(-0.1, 0.1)
            self.agv_state['position']['y'] += random.uniform(-0.1, 0.1)
            self.agv_state['position']['theta'] += random.uniform(-1, 1)
        
        # 模拟随机警告
        if random.random() < 0.05:  # 5%概率产生警告
            warnings = [
                "低电量警告",
                "传感器校准提醒",
                "维护周期到期",
                "通信延迟检测"
            ]
            if len(self.agv_state['warnings']) < 3:
                self.agv_state['warnings'].append(random.choice(warnings))
        
        # 清除旧警告
        if len(self.agv_state['warnings']) > 0 and random.random() < 0.1:
            self.agv_state['warnings'].pop(0)
    
    def _generate_state_data(self) -> Dict[str, Any]:
        """生成状态数据（基于VWED-0010.yaml配置）"""
        return {
            # 基本标识信息
            'vehicle_id': self.agv_state['vehicle_id'],
            'manufacturer': self.agv_state['manufacturer'],
            'model': self.agv_state['model'],
            'firmware_version': self.agv_state['firmware_version'],
            'serial_number': self.robot_info['serial_number'],
            
            # 时间戳
            'timestamp': datetime.now(timezone.utc).isoformat(),
            
            # 位置和运动状态
            'position': self.agv_state['position'].copy(),
            'velocity': self.agv_state['velocity'].copy(),
            
            # 物理参数
            'physical_limits': {
                'speed_max': self.physical_params['speed_max'],
                'acceleration_max': self.physical_params['acceleration_max'],
                'deceleration_max': self.physical_params['deceleration_max'],
                'max_load_mass': self.physical_params['max_load_mass']
            },
            
            # 运行状态
            'battery_level': self.agv_state['battery_level'],
            'operating_mode': self.agv_state['operating_mode'],
            'safety_state': self.agv_state['safety_state'],
            
            # 任务和控制状态
            'current_task': self.agv_state['current_task'],
            'task_status': self.agv_state['task_status'],
            'controller': self.agv_state['controller'],
            'control_timestamp': self.agv_state['control_timestamp'],
            
            # 载荷状态
            'load_status': self.agv_state['load_status'].copy(),
            
            # 错误和警告
            'errors': self.agv_state['errors'].copy(),
            'warnings': self.agv_state['warnings'].copy(),
            
            # AGV类型规格
            'agv_specification': {
                'agv_kinematic': 'DIFF',
                'agv_class': 'CARRIER',
                'localization_types': ['NATURAL', 'REFLECTOR'],
                'navigation_types': ['AUTONOMOUS']
            },
            
            # 数据类型标识
            'data_type': 'state'
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AGV模拟器')
    parser.add_argument('--server', default='localhost', help='服务器IP地址')
    parser.add_argument('--agv-id', default='VWED-0010', help='AGV ID')
    
    args = parser.parse_args()
    
    # 创建AGV模拟器
    simulator = AGVSimulator(args.server, args.agv_id)
    
    try:
        # 启动模拟器
        simulator.start()
        
        logger.info("AGV模拟器运行中，按Ctrl+C停止...")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"AGV模拟器运行异常: {e}")
    finally:
        simulator.stop()


if __name__ == "__main__":
    main() 