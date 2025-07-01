#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT状态监控器 - 专门监听AGV状态消息
用于验证虚拟小车是否正确上报状态到MQTT服务器
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any
import sys
import os

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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'mqtt_state_monitor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MQTTStateMonitor:
    """MQTT状态监控器"""
    
    def __init__(self, broker_host: str = '172.31.232.152', broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = f"state_monitor_{int(time.time())}"
        self.client = None
        self.is_connected = False
        self.message_count = 0
        
        # AGV配置
        self.manufacturer = 'SEER'
        self.serial_number = 'VWED-0010'
        
        # 监听的Topic
        self.topics = {
            'state': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/state',
            'visualization': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/visualization',
            'connection': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/connection'
        }
        
    def connect(self):
        """连接MQTT代理"""
        try:
            # 使用新的API版本
            try:
                self.client = mqtt.Client(
                    callback_api_version=CallbackAPIVersion.VERSION2,
                    client_id=self.client_id,
                    clean_session=True
                )
            except ImportError:
                self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
            
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
            
            # 订阅AGV状态topic
            self._subscribe_topics()
            
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
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """MQTT断开连接回调"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"MQTT连接意外断开，返回码: {rc}")
        else:
            logger.info("MQTT连接正常断开")
    
    def _on_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            self.message_count += 1
            
            # 解析消息
            message_data = json.loads(payload)
            
            # 根据topic类型显示不同信息
            if 'state' in topic:
                self._show_state_message(topic, message_data)
            elif 'visualization' in topic:
                self._display_visualization_message(message_data, topic)
            elif 'connection' in topic:
                self._display_connection_message(message_data, topic)
            else:
                logger.info(f"收到其他消息 - Topic: {topic}")
                logger.info(f"消息内容: {json.dumps(message_data, ensure_ascii=False, indent=2)}")
            
        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")
            logger.error(f"原始消息 - Topic: {msg.topic}, Payload: {msg.payload}")
    
    def _show_state_message(self, topic, data):
        """显示状态消息"""
        logger.info("=" * 60)
        logger.info(f"[STATS] 收到AGV状态消息 #{self.message_count} - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"Topic: {topic}")
        
        # 显示基本信息
        if 'header_id' in data:
            logger.info(f"消息ID: {data['header_id']}")
        
        if 'timestamp' in data:
            logger.info(f"时间戳: {data['timestamp']}")
        
        if 'vehicle_id' in data:
            logger.info(f"车辆ID: {data['vehicle_id']}")
        
        if 'manufacturer' in data:
            logger.info(f"制造商: {data['manufacturer']}")
        
        # 显示位置信息
        if 'position' in data and data['position']:
            pos = data['position']
            logger.info(f"位置: x={pos.get('x', 'N/A')}, y={pos.get('y', 'N/A')}, theta={pos.get('theta', 'N/A')}")
        
        # 显示速度信息
        if 'velocity' in data and data['velocity']:
            vel = data['velocity']
            logger.info(f"速度: vx={vel.get('vx', 'N/A')}, vy={vel.get('vy', 'N/A')}, omega={vel.get('omega', 'N/A')}")
        
        # 显示运行模式
        if 'operating_mode' in data:
            logger.info(f"[MODE] 运行模式: {data['operating_mode']}")
        
        # 显示安全状态
        if 'safety_state' in data:
            safety_icon = "[OK]" if data['safety_state'] == 'NORMAL' else "[WARNING]"
            logger.info(f"安全状态: {safety_icon} {data['safety_state']}")
        
        # 显示电池电量
        if 'battery_level' in data:
            logger.info(f"电池电量: {data['battery_level']}%")
        
        # 显示错误和警告
        if 'errors' in data and data['errors']:
            logger.error(f"错误: {', '.join(data['errors'])}")
        
        if 'warnings' in data and data['warnings']:
            logger.warning(f"[WARNING] 警告: {', '.join(data['warnings'])}")
        
        # 显示当前任务
        if 'current_task' in data and data['current_task']:
            logger.info(f"当前任务: {data['current_task']}")
        
        # 显示任务状态
        if 'task_status' in data:
            logger.info(f"任务状态: {data['task_status']}")
        
        logger.info("=" * 60)
    
    def _display_visualization_message(self, data: Dict[str, Any], topic: str):
        """显示可视化消息"""
        logger.info(f"🎨 收到可视化消息 #{self.message_count}")
        logger.info(f"Topic: {topic}")
        if 'agv_position' in data:
            pos = data['agv_position']
            logger.info(f"📍 可视化位置: X={pos.get('x', 0):.2f}, Y={pos.get('y', 0):.2f}")
    
    def _display_connection_message(self, data: Dict[str, Any], topic: str):
        """显示连接消息"""
        logger.info(f"🔗 收到连接消息 #{self.message_count}")
        logger.info(f"Topic: {topic}")
        if 'connectionState' in data:
            state_icon = "🟢" if data['connectionState'] == 'ONLINE' else "🔴"
            logger.info(f"{state_icon} 连接状态: {data['connectionState']}")
    
    def _subscribe_topics(self):
        """订阅所有相关topic"""
        for topic_name, topic in self.topics.items():
            result = self.client.subscribe(topic, qos=0)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ 已订阅{topic_name}消息: {topic}")
            else:
                logger.error(f"❌ 订阅{topic_name}消息失败: {topic}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MQTT状态监控器')
    parser.add_argument('--broker', default='172.31.232.152', help='MQTT代理地址')
    parser.add_argument('--port', type=int, default=1883, help='MQTT代理端口')
    
    args = parser.parse_args()
    
    # 创建状态监控器
    monitor = MQTTStateMonitor(args.broker, args.port)
    
    try:
        # 连接MQTT代理
        if not monitor.connect():
            return
        
        logger.info("[START] MQTT状态监控器启动成功！")
        logger.info("[LISTEN] 正在监听AGV状态消息...")
        logger.info("[CTRL+C] 按Ctrl+C停止监控")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"监控器运行异常: {e}")
    finally:
        monitor.disconnect()
        logger.info("状态监控器已停止")


if __name__ == "__main__":
    main() 