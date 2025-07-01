#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT测试客户端 - 用于向VDA5050-MQTT-TCP桥接服务器发送VDA5050协议消息
模拟MQTTX客户端行为，发送Order和InstantActions消息
"""

import json
import time
import random
import logging
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入VDA5050消息类
from vda5050 import OrderMessage, InstantActionsMessage

# MQTT客户端导入
try:
    import paho.mqtt.client as mqtt
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'mqtt_test_client.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MQTTTestClient:
    """MQTT测试客户端"""
    
    def __init__(self, broker_host: str = '172.31.232.152', broker_port: int = 1883, 
                 client_id: str = None):
        self.broker_host = broker_host
        self.broker_port = broker_port
        # 生成唯一的客户端ID，避免冲突
        self.client_id = client_id or f"mqtt_test_client_{uuid.uuid4().hex[:8]}"
        self.client = None
        self.is_connected = False
        
        # AGV配置
        self.manufacturer = 'Demo_Manufacturer'
        self.serial_number = 'AGV_001'
        
        # Topic模板
        self.topics = {
            'order': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/order',
            'instantActions': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/instantActions',
            'state': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/state',
            'visualization': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/visualization',
            'connection': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/connection'
        }
        
    def connect(self, max_retries: int = 3):
        """连接MQTT代理，带重试机制"""
        for attempt in range(max_retries):
            try:
                # 如果是重试，生成新的客户端ID
                if attempt > 0:
                    self.client_id = f"mqtt_test_client_{uuid.uuid4().hex[:8]}"
                    logger.info(f"第{attempt + 1}次连接尝试，使用新客户端ID: {self.client_id}")
                
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
                
                # 订阅上行topic（从AGV返回的消息）
                self._subscribe_uplink_topics()
                
                return True
                
            except Exception as e:
                logger.error(f"第{attempt + 1}次连接失败: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    logger.info(f"等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error("所有连接尝试都失败了")
                    
        return False
    
    def _reconnect(self):
        """重连逻辑"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and not self.is_connected:
            try:
                retry_count += 1
                wait_time = retry_count * 2  # 递增等待时间
                logger.info(f"第{retry_count}次重连尝试，等待{wait_time}秒...")
                time.sleep(wait_time)
                
                # 创建新的客户端实例
                self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.on_message = self._on_message
                
                logger.info(f"使用新客户端ID重连: {self.client_id}")
                self.client.connect(self.broker_host, self.broker_port, 60)
                self.client.loop_start()
                
                # 等待连接建立
                timeout = 5
                while not self.is_connected and timeout > 0:
                    time.sleep(0.1)
                    timeout -= 0.1
                
                if self.is_connected:
                    logger.info("重连成功！")
                    self._subscribe_uplink_topics()
                    break
                    
            except Exception as e:
                logger.error(f"重连失败: {e}")
                
        if not self.is_connected:
            logger.error("重连失败，请检查网络连接和MQTT服务器状态")
    
    def disconnect(self):
        """断开MQTT连接"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            logger.info("MQTT连接已断开")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT连接回调"""
        if rc == 0:
            self.is_connected = True
            logger.info("MQTT连接建立成功")
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT断开连接回调"""
        self.is_connected = False
        logger.warning(f"MQTT连接断开，返回码: {rc}")
        
        # 详细的错误码说明
        if rc != 0:
            error_messages = {
                1: "协议版本错误",
                2: "客户端标识符无效", 
                3: "服务器不可用",
                4: "用户名或密码错误",
                5: "未授权",
                7: "客户端ID冲突或协议问题"
            }
            if rc in error_messages:
                logger.error(f"断开原因: {error_messages[rc]}")
                
            # 如果是客户端ID冲突，生成新的ID并尝试重连
            if rc == 7:
                logger.info("检测到客户端ID冲突，生成新ID并重连...")
                self.client_id = f"mqtt_test_client_{uuid.uuid4().hex[:8]}"
                time.sleep(2)  # 等待2秒后重连
                threading.Thread(target=self._reconnect, daemon=True).start()
    
    def _on_message(self, client, userdata, msg):
        """MQTT消息接收回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"收到AGV消息 - Topic: {topic}")
            
            # 解析消息
            message_data = json.loads(payload)
            logger.info(f"消息内容: {json.dumps(message_data, ensure_ascii=False, indent=2)}")
            
        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")
    
    def _subscribe_uplink_topics(self):
        """订阅上行topic（AGV -> MQTTX）"""
        uplink_topics = [
            (self.topics['state'], 0),
            (self.topics['visualization'], 0),
            (self.topics['connection'], 0),
        ]
        
        for topic, qos in uplink_topics:
            self.client.subscribe(topic, qos)
            logger.info(f"订阅上行topic: {topic}")
    
    def send_order(self, order_data: Dict[str, Any] = None):
        """发送Order消息"""
        try:
            if not self.is_connected:
                logger.error("MQTT未连接，无法发送消息")
                return False
            
            if not order_data:
                order_data = self._generate_sample_order()
            
            topic = self.topics['order']
            payload = json.dumps(order_data, ensure_ascii=False)
            
            result = self.client.publish(topic, payload, qos=0)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Order消息发送成功 - Topic: {topic}")
                logger.info(f"Order内容: {json.dumps(order_data, ensure_ascii=False, indent=2)}")
                return True
            else:
                logger.error(f"Order消息发送失败 - 错误码: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"发送Order消息异常: {e}")
            return False
    
    def send_instant_actions(self, actions_data: Dict[str, Any] = None):
        """发送InstantActions消息"""
        try:
            if not self.is_connected:
                logger.error("MQTT未连接，无法发送消息")
                return False
            
            if not actions_data:
                actions_data = self._generate_sample_instant_actions()
            
            topic = self.topics['instantActions']
            payload = json.dumps(actions_data, ensure_ascii=False)
            
            result = self.client.publish(topic, payload, qos=0)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"InstantActions消息发送成功 - Topic: {topic}")
                logger.info(f"Actions内容: {json.dumps(actions_data, ensure_ascii=False, indent=2)}")
                return True
            else:
                logger.error(f"InstantActions消息发送失败 - 错误码: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"发送InstantActions消息异常: {e}")
            return False
    
    def _generate_sample_order(self) -> Dict[str, Any]:
        """生成示例Order消息"""
        # 生成随机路径点
        num_nodes = random.randint(3, 5)
        nodes = []
        edges = []
        
        for i in range(num_nodes):
            # 生成节点
            node = {
                "nodeId": f"node_{i+1}",
                "sequenceId": i,
                "released": True,
                "nodePosition": {
                    "x": random.uniform(0, 100),
                    "y": random.uniform(0, 100),
                    "theta": random.uniform(0, 360),
                    "allowed_deviation_xy": 0.5,
                    "allowed_deviation_theta": 5.0
                },
                "actions": []
            }
            
            # 为某些节点添加动作
            if i > 0 and random.random() < 0.6:  # 60%概率添加动作
                action_types = ['pick', 'drop', 'wait']
                action_type = random.choice(action_types)
                
                action = {
                    "actionType": action_type,
                    "actionId": f"action_{i}_{action_type}",
                    "actionDescription": f"Execute {action_type} operation",
                    "blocking_type": "HARD"
                }
                
                if action_type == 'wait':
                    action["actionParameters"] = [
                        {"key": "duration", "value": str(random.randint(5, 15))}
                    ]
                elif action_type in ['pick', 'drop']:
                    action["actionParameters"] = [
                        {"key": "stationType", "value": "conveyor"},
                        {"key": "loadId", "value": f"load_{random.randint(1000, 9999)}"}
                    ]
                
                node["actions"].append(action)
            
            nodes.append(node)
            
            # 生成边（除了最后一个节点）
            if i < num_nodes - 1:
                edge = {
                    "edgeId": f"edge_{i+1}_{i+2}",
                    "sequenceId": i,
                    "released": True,
                    "startNodeId": f"node_{i+1}",
                    "endNodeId": f"node_{i+2}",
                    "maxSpeed": random.uniform(1.0, 3.0),
                    "actions": []
                }
                edges.append(edge)
        
        # 构建完整的Order消息
        order_data = {
            "headerId": random.randint(1000, 9999),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0",
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "orderId": f"order_{int(time.time())}",
            "orderUpdateId": 0,
            "zoneSetId": "zone_set_1",
            "nodes": nodes,
            "edges": edges
        }
        
        return order_data
    
    def _generate_sample_instant_actions(self) -> Dict[str, Any]:
        """生成示例InstantActions消息"""
        # 随机生成1-3个即时动作
        num_actions = random.randint(1, 3)
        actions = []
        
        action_types = [
            'pick', 'drop', 'translate', 'turn', 'reloc', 
            'startPause', 'stopPause', 'clearErrors'
        ]
        
        for i in range(num_actions):
            action_type = random.choice(action_types)
            
            action = {
                "actionType": action_type,
                "actionId": f"instant_{action_type}_{int(time.time())}_{i}",
                "actionDescription": f"Instant {action_type} action",
                "blocking_type": "HARD"
            }
            
            # 根据动作类型添加参数
            if action_type == 'translate':
                action["actionParameters"] = [
                    {"key": "x", "value": str(random.uniform(0, 100))},
                    {"key": "y", "value": str(random.uniform(0, 100))},
                    {"key": "theta", "value": str(random.uniform(0, 360))}
                ]
            elif action_type == 'turn':
                action["actionParameters"] = [
                    {"key": "theta", "value": str(random.uniform(0, 360))}
                ]
            elif action_type in ['pick', 'drop']:
                action["actionParameters"] = [
                    {"key": "stationType", "value": "conveyor"},
                    {"key": "loadId", "value": f"load_{random.randint(1000, 9999)}"}
                ]
            elif action_type == 'startPause':
                action["actionParameters"] = [
                    {"key": "duration", "value": str(random.randint(10, 60))}
                ]
            
            actions.append(action)
        
        # 构建完整的InstantActions消息
        instant_actions_data = {
            "headerId": random.randint(1000, 9999),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0",
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "actions": actions
        }
        
        return instant_actions_data


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MQTT测试客户端')
    parser.add_argument('--broker', default='172.31.232.152', help='MQTT代理地址')
    parser.add_argument('--port', type=int, default=1883, help='MQTT代理端口')
    parser.add_argument('--client-id', default=None, help='MQTT客户端ID (默认自动生成唯一ID)')
    
    args = parser.parse_args()
    
    # 创建MQTT测试客户端  
    client = MQTTTestClient(args.broker, args.port, args.client_id)
    
    try:
        # 连接MQTT代理
        if not client.connect():
            return
        
        logger.info("可用命令:")
        logger.info("  1 - 发送Order消息")
        logger.info("  2 - 发送InstantActions消息")
        logger.info("  q - 退出")
        
        while True:
            try:
                command = input("\n请输入命令: ").strip()
                
                if command == '1':
                    client.send_order()
                elif command == '2':
                    client.send_instant_actions()
                elif command.lower() == 'q':
                    logger.info("退出测试客户端")
                    break
                else:
                    logger.warning("未知命令，请重新输入")
                
                time.sleep(0.5)  # 短暂延迟
                
            except KeyboardInterrupt:
                logger.info("收到退出信号")
                break
            except Exception as e:
                logger.error(f"测试异常: {e}")
            
    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    except Exception as e:
        logger.error(f"测试客户端运行异常: {e}")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()