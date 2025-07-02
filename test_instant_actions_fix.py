#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证InstantActions修复的测试脚本
测试：
1. startPause和stopPause的端口配置修复
2. softEmc的生成修复  
3. 新增的抢夺控制权和释放控制权动作
"""

import sys
import os
import json
from datetime import datetime, timezone

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入必要模块
from vda5050.instantActions_message import InstantActionsMessage, InstantActionBuilder
from vda5050.base_message import Action, ActionParameter
from tcp.tcp_instantActions import VDA5050InstantActionsToTCPConverter
from tcp.manufacturer_a import ManufacturerATCPProtocol


def test_pause_resume_config():
    """测试暂停和恢复任务的端口配置"""
    print("=" * 60)
    print("测试1: startPause和stopPause端口配置")
    print("=" * 60)
    
    converter = VDA5050InstantActionsToTCPConverter()
    
    # 测试startPause配置
    start_pause_config = converter.ACTION_CONFIG.get('startPause')
    if start_pause_config:
        print(f"✅ startPause配置: 端口={start_pause_config.port}, 报文类型={start_pause_config.message_type}")
        if start_pause_config.port == 19206 and start_pause_config.message_type == 3002:
            print("✅ startPause配置正确")
        else:
            print("❌ startPause配置错误")
    else:
        print("❌ 未找到startPause配置")
    
    # 测试stopPause配置  
    stop_pause_config = converter.ACTION_CONFIG.get('stopPause')
    if stop_pause_config:
        print(f"✅ stopPause配置: 端口={stop_pause_config.port}, 报文类型={stop_pause_config.message_type}")
        if stop_pause_config.port == 19206 and stop_pause_config.message_type == 3001:
            print("✅ stopPause配置正确")
        else:
            print("❌ stopPause配置错误")
    else:
        print("❌ 未找到stopPause配置")


def test_soft_emc_generation():
    """测试softEmc动作生成"""
    print("\n" + "=" * 60)
    print("测试2: softEmc动作生成")
    print("=" * 60)
    
    try:
        # 使用InstantActionBuilder创建softEmc动作
        soft_emc_action = InstantActionBuilder.create_soft_emc("test_soft_emc_1", True)
        print("✅ 成功创建softEmc动作（status=True）")
        
        # 检查参数
        if soft_emc_action.action_parameters:
            status_param = soft_emc_action.action_parameters[0]
            print(f"   参数: {status_param.key} = {status_param.value}")
            if status_param.key == "status" and status_param.value == True:
                print("✅ softEmc参数正确")
            else:
                print("❌ softEmc参数错误")
        
        # 测试status=False的情况
        soft_emc_action_false = InstantActionBuilder.create_soft_emc("test_soft_emc_2", False)
        print("✅ 成功创建softEmc动作（status=False）")
        
        # 创建完整的InstantActions消息
        instant_actions_msg = InstantActionsMessage(
            header_id=12345,
            actions=[soft_emc_action, soft_emc_action_false],
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            manufacturer="TestManufacturer",
            serial_number="TEST_001"
        )
        
        # 转换为JSON验证
        msg_dict = instant_actions_msg.get_message_dict()
        json_str = json.dumps(msg_dict, indent=2, ensure_ascii=False)
        print("✅ 成功转换为JSON:")
        print(json_str[:200] + "..." if len(json_str) > 200 else json_str)
        
    except Exception as e:
        print(f"❌ softEmc生成失败: {str(e)}")


def test_authority_control_actions():
    """测试控制权管理动作"""
    print("\n" + "=" * 60)
    print("测试3: 控制权管理动作")
    print("=" * 60)
    
    converter = VDA5050InstantActionsToTCPConverter()
    
    # 测试grabAuthority配置
    grab_config = converter.ACTION_CONFIG.get('grabAuthority')
    if grab_config:
        print(f"✅ grabAuthority配置: 端口={grab_config.port}, 报文类型={grab_config.message_type}")
        if grab_config.port == 19207 and grab_config.message_type == 4005:
            print("✅ grabAuthority配置正确")
        else:
            print("❌ grabAuthority配置错误")
    else:
        print("❌ 未找到grabAuthority配置")
    
    # 测试releaseAuthority配置
    release_config = converter.ACTION_CONFIG.get('releaseAuthority')
    if release_config:
        print(f"✅ releaseAuthority配置: 端口={release_config.port}, 报文类型={release_config.message_type}")
        if release_config.port == 19207 and release_config.message_type == 4006:
            print("✅ releaseAuthority配置正确")
        else:
            print("❌ releaseAuthority配置错误")
    else:
        print("❌ 未找到releaseAuthority配置")
    
    # 测试动作创建
    try:
        grab_action = InstantActionBuilder.create_grab_authority("grab_1", "FULL")
        print("✅ 成功创建grabAuthority动作")
        print(f"   动作类型: {grab_action.action_type}")
        print(f"   参数数量: {len(grab_action.action_parameters)}")
        
        release_action = InstantActionBuilder.create_release_authority("release_1")
        print("✅ 成功创建releaseAuthority动作")
        print(f"   动作类型: {release_action.action_type}")
        print(f"   参数数量: {len(release_action.action_parameters)}")
        
    except Exception as e:
        print(f"❌ 控制权动作创建失败: {str(e)}")


def test_tcp_conversion():
    """测试TCP协议转换"""
    print("\n" + "=" * 60)
    print("测试4: TCP协议转换测试")
    print("=" * 60)
    
    try:
        # 创建包含所有测试动作的InstantActions消息
        actions = [
            InstantActionBuilder.create_start_pause("start_pause_1"),
            InstantActionBuilder.create_stop_pause("stop_pause_1"),
            InstantActionBuilder.create_soft_emc("soft_emc_1", True),
            InstantActionBuilder.create_grab_authority("grab_1", "FULL"),
            InstantActionBuilder.create_release_authority("release_1")
        ]
        
        instant_actions_msg = InstantActionsMessage(
            header_id=12345,
            actions=actions,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            manufacturer="TestManufacturer",
            serial_number="TEST_001"
        )
        
        # 转换为TCP协议
        converter = VDA5050InstantActionsToTCPConverter()
        vda_json = instant_actions_msg.get_message_dict()
        tcp_result = converter.convert_vda5050_instant_actions(vda_json)
        
        print("✅ TCP转换成功")
        print(f"转换结果包含 {len(tcp_result)} 个TCP操作")
        
        # 显示每个操作的详情
        for i, operation in enumerate(tcp_result, 1):
            print(f"  操作{i}: 端口={operation.get('port')}, 报文={operation.get('message_type')}, 类型={operation.get('type')}")
        
        # 测试二进制数据包生成
        tcp_protocol = ManufacturerATCPProtocol()
        for operation in tcp_result:
            msg_type = operation.get('message_type', 3066)
            data = operation.get('data', {})
            
            try:
                binary_packet = tcp_protocol.create_binary_tcp_packet(msg_type, data)
                print(f"✅ 成功生成报文类型{msg_type}的二进制数据包，长度: {len(binary_packet)}字节")
            except Exception as e:
                print(f"❌ 报文类型{msg_type}的二进制数据包生成失败: {str(e)}")
        
    except Exception as e:
        print(f"❌ TCP转换失败: {str(e)}")


def test_action_config_analysis():
    """测试动作配置解析"""
    print("\n" + "=" * 60)
    print("测试5: 动作配置解析")
    print("=" * 60)
    
    try:
        # 创建测试数据
        test_data = {
            "headerId": 12345,
            "actions": [
                {"actionId": "action1", "actionType": "startPause"},
                {"actionId": "action2", "actionType": "stopPause"},
                {"actionId": "action3", "actionType": "grabAuthority"},
                {"actionId": "action4", "actionType": "releaseAuthority"}
            ]
        }
        
        converter = VDA5050InstantActionsToTCPConverter()
        configs = converter.analyze_instant_action_configs(test_data)
        
        print(f"✅ 成功解析 {len(configs)} 个动作配置")
        
        expected_configs = {
            "startPause": {"port": 19206, "messageType": 3002},
            "stopPause": {"port": 19206, "messageType": 3001},
            "grabAuthority": {"port": 19207, "messageType": 4005},
            "releaseAuthority": {"port": 19207, "messageType": 4006}
        }
        
        for config in configs:
            action_type = config.get("actionType")
            port = config.get("port")
            msg_type = config.get("messageType")
            
            if action_type in expected_configs:
                expected = expected_configs[action_type]
                if port == expected["port"] and msg_type == expected["messageType"]:
                    print(f"✅ {action_type}: 端口={port}, 报文={msg_type} (正确)")
                else:
                    print(f"❌ {action_type}: 端口={port}, 报文={msg_type} (期望: 端口={expected['port']}, 报文={expected['messageType']})")
            else:
                print(f"⚠️  未知动作类型: {action_type}")
        
    except Exception as e:
        print(f"❌ 动作配置解析失败: {str(e)}")


def main():
    """主测试函数"""
    print("开始InstantActions修复验证测试")
    print("=" * 60)
    
    # 执行所有测试
    test_pause_resume_config()
    test_soft_emc_generation()
    test_authority_control_actions()
    test_tcp_conversion()
    test_action_config_analysis()
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main() 