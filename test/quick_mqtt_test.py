#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速MQTT连接测试 - 验证broker.emqx.io连接
"""

import time
import logging
import json
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import CallbackAPIVersion
except ImportError:
    print("请安装paho-mqtt库: pip install paho-mqtt")
    exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_mqtt_connection():
    """测试MQTT连接"""
    
    # 配置参数
    broker_host = "broker.emqx.io"
    broker_port = 1883
    client_id = f"vda5050_test_{int(time.time())}"
    
    # 测试topic
    test_topic = "/uagv/v2/SEER/VWED-0010/state"
    
    logger.info("🚀 开始MQTT连接测试...")
    logger.info(f"📡 服务器: {broker_host}:{broker_port}")
    logger.info(f"🆔 客户端ID: {client_id}")
    
    try:
        # 创建客户端
        try:
            client = mqtt.Client(
                callback_api_version=CallbackAPIVersion.VERSION2,
                client_id=client_id,
                clean_session=True
            )
        except ImportError:
            client = mqtt.Client(client_id=client_id, clean_session=True)
        
        # 连接状态
        connection_result = {"connected": False, "error": None}
        
        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                connection_result["connected"] = True
                logger.info("✅ MQTT连接成功！")
            else:
                connection_result["error"] = f"连接失败，返回码: {rc}"
                logger.error(f"❌ {connection_result['error']}")
        
        def on_disconnect(client, userdata, rc, properties=None):
            logger.info(f"🔌 连接断开，返回码: {rc}")
        
        def on_message(client, userdata, msg):
            logger.info(f"📨 收到消息 - Topic: {msg.topic}")
            try:
                data = json.loads(msg.payload.decode('utf-8'))
                logger.info(f"📄 消息内容: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                logger.info(f"📄 消息内容: {msg.payload.decode('utf-8')}")
        
        # 设置回调
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # 连接服务器
        logger.info("🔗 正在连接MQTT服务器...")
        client.connect(broker_host, broker_port, 60)
        client.loop_start()
        
        # 等待连接
        timeout = 15
        while not connection_result["connected"] and not connection_result["error"] and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        if connection_result["connected"]:
            logger.info("🎯 订阅测试topic...")
            result = client.subscribe(test_topic, qos=0)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ 订阅成功: {test_topic}")
            else:
                logger.error(f"❌ 订阅失败: {test_topic}")
            
            # 发送测试消息
            logger.info("📤 发送测试状态消息...")
            test_message = {
                "vehicle_id": "VWED-0010",
                "manufacturer": "SEER",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "position": {"x": 10.5, "y": 20.3, "theta": 45.0},
                "battery_level": 85.5,
                "operating_mode": "AUTOMATIC",
                "safety_state": "NORMAL",
                "task_status": "WAITING",
                "test_message": True
            }
            
            payload = json.dumps(test_message, ensure_ascii=False)
            result = client.publish(test_topic, payload, qos=0)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("✅ 测试消息发送成功！")
            else:
                logger.error(f"❌ 测试消息发送失败，错误码: {result.rc}")
            
            # 等待可能的回显消息
            logger.info("⏳ 等待3秒查看是否有消息...")
            time.sleep(3)
            
        elif connection_result["error"]:
            logger.error(f"❌ 连接测试失败: {connection_result['error']}")
            return False
        else:
            logger.error("❌ 连接超时")
            return False
        
        # 断开连接
        client.loop_stop()
        client.disconnect()
        logger.info("✅ MQTT连接测试完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🧪 VDA5050 MQTT连接测试工具")
    logger.info("=" * 60)
    
    success = test_mqtt_connection()
    
    if success:
        logger.info("🎉 测试成功！broker.emqx.io连接正常")
        logger.info("💡 提示：您可以在MQTTX中使用以下配置:")
        logger.info("   服务器: broker.emqx.io:1883")
        logger.info("   客户端ID: vda5050")
        logger.info("   订阅Topic: /uagv/v2/SEER/VWED-0010/state")
    else:
        logger.error("❌ 测试失败！请检查网络连接")
    
    logger.info("=" * 60) 