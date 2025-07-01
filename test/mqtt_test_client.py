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
                 client_id: str = 'mqtt_test_client'):
        self.broker_host = broker_host
        self.broker_port = broker_port
        # 添加时间戳避免客户端ID冲突
        self.client_id = f"{client_id}_{int(time.time())}"
        self.client = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # AGV配置 - 与AGV模拟器保持一致
        self.manufacturer = 'SEER'
        self.serial_number = 'VWED-0010'
        
        # Topic模板
        self.topics = {
            'order': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/order',
            'instantActions': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/instantActions',
            'state': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/state',
            'visualization': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/visualization',
            'connection': f'/uagv/v2/{self.manufacturer}/{self.serial_number}/connection'
        }
        
    def connect(self):
        """连接MQTT代理"""
        try:
            # 使用新的API版本避免弃用警告
            try:
                from paho.mqtt.client import CallbackAPIVersion
                self.client = mqtt.Client(
                    callback_api_version=CallbackAPIVersion.VERSION2,
                    client_id=self.client_id,
                    clean_session=True
                )
            except ImportError:
                # 兼容旧版本
                self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
            
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # 设置连接参数
            self.client.reconnect_delay_set(min_delay=1, max_delay=60)
            
            logger.info(f"正在连接MQTT代理: {self.broker_host}:{self.broker_port}")
            logger.info(f"使用客户端ID: {self.client_id}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 等待连接建立
            timeout = 15
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
            self.reconnect_attempts = 0
            logger.info("MQTT连接建立成功")
        else:
            self.is_connected = False
            logger.error(f"MQTT连接失败，返回码: {rc}")
            # 详细错误信息
            error_messages = {
                1: "协议版本不正确",
                2: "无效的客户端标识符", 
                3: "服务器不可用",
                4: "错误的用户名或密码",
                5: "未授权",
                6: "连接被拒绝 - 其他原因"
            }
            if rc in error_messages:
                logger.error(f"错误详情: {error_messages[rc]}")
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """MQTT断开连接回调"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"MQTT连接意外断开，返回码: {rc}")
            # 启动重连
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                wait_time = min(self.reconnect_attempts * 2, 30)
                logger.info(f"将在{wait_time}秒后尝试重连（第{self.reconnect_attempts}次）")
                threading.Thread(target=self._delayed_reconnect, args=(wait_time,), daemon=True).start()
            else:
                logger.error("达到最大重连次数，停止重连")
        else:
            logger.info("MQTT连接正常断开")
    
    def _delayed_reconnect(self, delay: int):
        """延迟重连"""
        try:
            time.sleep(delay)
            if not self.is_connected:
                logger.info("尝试重新连接MQTT服务器...")
                self.client.reconnect()
        except Exception as e:
            logger.error(f"重连失败: {e}")
    
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
    parser.add_argument('--broker', default='broker.emqx.io', help='MQTT代理地址')
    parser.add_argument('--port', type=int, default=1883, help='MQTT代理端口')
    parser.add_argument('--client-id', default='mqtt_test_client', help='MQTT客户端ID')
    
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