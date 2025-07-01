#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050与TCP协议转换可视化演示程序
包含六个界面展示不同消息类型的转换功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import random
import sys
import os
from datetime import datetime, timezone
import uuid

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入VDA5050相关模块
from vda5050 import (
    OrderMessage, Node, Edge, Action, ActionParameter, NodePosition,
    InstantActionsMessage, InstantActionBuilder,
    StateMessage, MapInfo, NodeState, EdgeState, ActionState, BatteryState, Error, SafetyState,
    VisualizationMessage, AGVPosition, Velocity,
    ConnectionMessage,
    FactsheetMessage, PhysicalParameters
)

# 导入TCP转换器
from tcp.tcp_order import VDA5050ToTCPConverter
from tcp.tcp_instantActions import VDA5050InstantActionsToTCPConverter
from tcp.tcp_state import AGVToVDA5050Converter
from tcp.tcp_visualization import TCPStateToVisualizationConverter


class VDA5050TCPDemo:
    """VDA5050与TCP协议转换演示程序"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("VDA5050与TCP协议转换演示程序")
        self.root.geometry("1200x800")
        
        # 创建转换器实例
        self.order_converter = VDA5050ToTCPConverter()
        self.instant_actions_converter = VDA5050InstantActionsToTCPConverter()
        self.state_converter = AGVToVDA5050Converter()
        self.visualization_converter = TCPStateToVisualizationConverter()
        
        self.setup_gui()
    
    def setup_gui(self):
        """设置GUI界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建标签页
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 创建六个标签页
        self.create_order_tab(notebook)
        self.create_instant_actions_tab(notebook)
        self.create_state_tab(notebook)
        self.create_visualization_tab(notebook)
        self.create_connection_tab(notebook)
        self.create_factsheet_tab(notebook)
    
    def create_order_tab(self, notebook):
        """创建Order VDA5050→TCP转换标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Order (VDA5050→TCP)")
        
        # 分割窗口
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：VDA5050 Order输入
        left_frame = ttk.LabelFrame(paned, text="VDA5050 Order消息")
        paned.add(left_frame, weight=1)
        
        # 生成按钮
        ttk.Button(left_frame, text="生成随机Order", 
                  command=lambda: self.generate_random_order()).pack(pady=5)
        
        # 输入文本框
        self.order_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.order_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：TCP输出
        right_frame = ttk.LabelFrame(paned, text="TCP协议输出")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为TCP", 
                  command=lambda: self.convert_order_to_tcp()).pack(pady=5)
        
        # 输出文本框
        self.order_output = scrolledtext.ScrolledText(right_frame, height=25, width=50)
        self.order_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_instant_actions_tab(self, notebook):
        """创建InstantActions VDA5050→TCP转换标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="InstantActions (VDA5050→TCP)")
        
        # 分割窗口
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：VDA5050 InstantActions输入
        left_frame = ttk.LabelFrame(paned, text="VDA5050 InstantActions消息")
        paned.add(left_frame, weight=1)
        
        # 生成按钮
        ttk.Button(left_frame, text="生成随机InstantActions", 
                  command=lambda: self.generate_random_instant_actions()).pack(pady=5)
        
        # 输入文本框
        self.instant_actions_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.instant_actions_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：TCP输出
        right_frame = ttk.LabelFrame(paned, text="TCP协议输出")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为TCP", 
                  command=lambda: self.convert_instant_actions_to_tcp()).pack(pady=5)
        
        # 输出文本框
        self.instant_actions_output = scrolledtext.ScrolledText(right_frame, height=25, width=50)
        self.instant_actions_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_state_tab(self, notebook):
        """创建State TCP→VDA5050转换标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="State (TCP→VDA5050)")
        
        # 分割窗口
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：TCP State输入
        left_frame = ttk.LabelFrame(paned, text="TCP State数据")
        paned.add(left_frame, weight=1)
        
        # 生成按钮
        ttk.Button(left_frame, text="生成随机TCP State", 
                  command=lambda: self.generate_random_tcp_state()).pack(pady=5)
        
        # 输入文本框
        self.state_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.state_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：VDA5050输出
        right_frame = ttk.LabelFrame(paned, text="VDA5050 State消息")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为VDA5050", 
                  command=lambda: self.convert_tcp_state_to_vda5050()).pack(pady=5)
        
        # 输出文本框
        self.state_output = scrolledtext.ScrolledText(right_frame, height=25, width=50)
        self.state_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_visualization_tab(self, notebook):
        """创建Visualization TCP→VDA5050转换标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Visualization (TCP→VDA5050)")
        
        # 分割窗口
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：TCP State输入
        left_frame = ttk.LabelFrame(paned, text="TCP State数据")
        paned.add(left_frame, weight=1)
        
        # 生成按钮
        ttk.Button(left_frame, text="生成随机TCP State", 
                  command=lambda: self.generate_random_tcp_state_for_visualization()).pack(pady=5)
        
        # 输入文本框
        self.visualization_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.visualization_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：VDA5050输出
        right_frame = ttk.LabelFrame(paned, text="VDA5050 Visualization消息")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为VDA5050", 
                  command=lambda: self.convert_tcp_state_to_visualization()).pack(pady=5)
        
        # 输出文本框
        self.visualization_output = scrolledtext.ScrolledText(right_frame, height=25, width=50)
        self.visualization_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_connection_tab(self, notebook):
        """创建Connection标签页（仅展示页面）"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Connection (TCP→VDA5050)")
        
        # 标题
        title_label = ttk.Label(frame, text="Connection消息转换", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        
        # 说明文本
        info_text = """
        Connection消息用于建立和维护AGV与控制系统之间的连接。
        
        主要功能：
        • 连接状态管理
        • 心跳检测
        • 连接参数配置
        • 通信质量监控
        
        该模块正在开发中，敬请期待...
        """
        
        info_label = ttk.Label(frame, text=info_text, font=("Arial", 12), justify=tk.LEFT)
        info_label.pack(pady=20, padx=50)
        
        # 示例连接消息
        example_frame = ttk.LabelFrame(frame, text="示例Connection消息")
        example_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        example_text = scrolledtext.ScrolledText(example_frame, height=15)
        example_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 生成示例连接消息
        connection_msg = ConnectionMessage(
            header_id=random.randint(1000, 9999),
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            manufacturer="Demo_Manufacturer",
            serial_number="AGV_DEMO_001",
            connection_state="ONLINE"
        )
        
        example_text.insert(tk.END, json.dumps(connection_msg.get_message_dict(), indent=2, ensure_ascii=False))
        example_text.config(state=tk.DISABLED)
    
    def create_factsheet_tab(self, notebook):
        """创建Factsheet标签页（仅展示页面）"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Factsheet (TCP→VDA5050)")
        
        # 标题
        title_label = ttk.Label(frame, text="Factsheet消息转换", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        
        # 说明文本
        info_text = """
        Factsheet消息包含AGV的技术规格和能力信息。
        
        主要内容：
        • AGV物理参数（尺寸、重量、载重等）
        • 技术规格（最大速度、精度等）
        • 支持的功能和动作类型
        • 协议版本和限制信息
        
        该模块正在开发中，敬请期待...
        """
        
        info_label = ttk.Label(frame, text=info_text, font=("Arial", 12), justify=tk.LEFT)
        info_label.pack(pady=20, padx=50)
        
        # 示例规格说明书
        example_frame = ttk.LabelFrame(frame, text="示例Factsheet消息")
        example_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        example_text = scrolledtext.ScrolledText(example_frame, height=15)
        example_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 生成示例规格说明书
        from vda5050.factsheet_message import TypeSpecification, ProtocolLimits
        
        # 创建类型规格
        type_spec = TypeSpecification(
            series_name="DEMO_AGV_SERIES",
            agv_kinematic="DIFF",
            agv_class="CARRIER",
            max_load_mass=100.0,
            localization_types=["NATURAL", "REFLECTOR"],
            navigation_types=["AUTONOMOUS"],
            series_description="演示AGV系列"
        )
        
        # 创建物理参数
        physical_params = PhysicalParameters(
            speed_min=0.0,
            speed_max=2.0,
            acceleration_max=1.0,
            deceleration_max=1.5,
            height_min=0.1,
            height_max=2.0,
            width=0.8,
            length=1.2
        )
        
        # 创建协议限制
        protocol_limits = ProtocolLimits(
            max_string_lens={"orderId": 100, "nodeId": 50},
            max_array_lens={"nodes": 100, "edges": 100},
            timing={"maxStatesArrayLength": 1000, "minOrderInterval": 1.0}
        )
        
        # 创建协议特性
        protocol_features = {
            "optionalParameters": ["orderId", "orderUpdateId"],
            "agvActions": ["pick", "drop", "move"],
            "drivingDirection": "FORWARD"
        }
        
        # 创建AGV几何信息
        agv_geometry = {
            "wheelDefinitions": [
                {"type": "DRIVE", "isActiveDriven": True, "isActiveSteered": False, "position": {"x": 0.0, "y": 0.0, "theta": 0.0}}
            ],
            "envelopes2d": [
                {"set": "body", "polygonPoints": [{"x": -0.4, "y": -0.6}, {"x": 0.4, "y": -0.6}, {"x": 0.4, "y": 0.6}, {"x": -0.4, "y": 0.6}]}
            ]
        }
        
        # 创建载荷规格
        load_specification = {
            "loadPositions": ["LOAD_POS_1"],
            "loadSets": [
                {
                    "setName": "PALLET",
                    "loadType": "PALLET",
                    "loadPositions": ["LOAD_POS_1"],
                    "maxWeight": 100.0,
                    "minLoadhandlingTime": 5.0,
                    "maxLoadhandlingTime": 30.0
                }
            ]
        }
        
        factsheet_msg = FactsheetMessage(
            header_id=random.randint(1000, 9999),
            type_specification=type_spec,
            physical_parameters=physical_params,
            protocol_limits=protocol_limits,
            protocol_features=protocol_features,
            agv_geometry=agv_geometry,
            load_specification=load_specification,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            manufacturer="Demo_Manufacturer",
            serial_number="AGV_DEMO_001"
        )
        
        example_text.insert(tk.END, json.dumps(factsheet_msg.get_message_dict(), indent=2, ensure_ascii=False))
        example_text.config(state=tk.DISABLED)
    
    def generate_random_order(self):
        """生成随机Order消息"""
        try:
            # 创建随机节点
            nodes = []
            edges = []
            
            # 生成3-5个节点
            num_nodes = random.randint(3, 5)
            for i in range(num_nodes):
                node_id = f"node_{i+1}"
                actions = []
                
                # 随机添加动作
                if random.random() > 0.5:
                    action_types = ["pick", "drop", "wait"]
                    action_type = random.choice(action_types)
                    actions.append(Action(
                        action_id=f"action_{i+1}",
                        action_type=action_type,
                        blocking_type="HARD",
                        action_description=f"{action_type}动作"
                    ))
                
                node_position = NodePosition(
                    x=random.uniform(0, 20),
                    y=random.uniform(0, 15),
                    theta=random.uniform(0, 6.28),
                    map_id="demo_map",
                    allowed_deviation_xy=0.1,
                    allowed_deviation_theta=0.1
                )
                
                nodes.append(Node(
                    node_id=node_id,
                    sequence_id=i,
                    released=True,
                    node_position=node_position,
                    actions=actions
                ))
            
            # 生成边
            for i in range(num_nodes - 1):
                edges.append(Edge(
                    edge_id=f"edge_{i+1}",
                    sequence_id=i,
                    start_node_id=f"node_{i+1}",
                    end_node_id=f"node_{i+2}",
                    released=True,
                    actions=[],
                    max_speed=1.5,
                    max_rotation_speed=0.5
                ))
            
            # 创建Order消息
            order_msg = OrderMessage(
                header_id=random.randint(1000, 9999),
                order_id=f"ORDER_{random.randint(100, 999)}",
                order_update_id=0,
                nodes=nodes,
                edges=edges,
                timestamp=datetime.now(timezone.utc).isoformat(),
                version="2.0.0",
                manufacturer="Demo_Manufacturer",
                serial_number="AGV_DEMO_001"
            )
            
            # 显示在输入框
            self.order_input.delete(1.0, tk.END)
            self.order_input.insert(tk.END, json.dumps(order_msg.get_message_dict(), indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"生成Order消息失败: {str(e)}")
    
    def convert_order_to_tcp(self):
        """转换Order为TCP协议"""
        try:
            # 获取输入的VDA5050 Order
            order_json = self.order_input.get(1.0, tk.END).strip()
            if not order_json:
                messagebox.showwarning("警告", "请先生成或输入Order消息")
                return
            
            order_data = json.loads(order_json)
            
            # 转换为TCP协议
            tcp_result = self.order_converter.convert_vda5050_order_to_tcp_move_task_list(order_data)
            
            # 显示结果
            self.order_output.delete(1.0, tk.END)
            self.order_output.insert(tk.END, json.dumps(tcp_result, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"Order转换失败: {str(e)}")
    
    def generate_random_instant_actions(self):
        """生成随机InstantActions消息"""
        try:
            # 创建随机即时动作
            actions = []
            action_types = ["pick", "drop", "translate", "turn", "reloc", "startPause", "stopPause"]
            
            # 生成1-3个动作
            num_actions = random.randint(1, 3)
            for i in range(num_actions):
                action_type = random.choice(action_types)
                
                if action_type == "translate":
                    action = InstantActionBuilder.create_translate(
                        action_id=f"action_{i+1}",
                        dist=random.uniform(0.5, 5.0),
                        vx=random.uniform(0.1, 1.0)
                    )
                elif action_type == "turn":
                    action = InstantActionBuilder.create_turn(
                        action_id=f"action_{i+1}",
                        angle=random.uniform(0.5, 3.14),
                        vw=random.uniform(0.1, 0.5)
                    )
                elif action_type == "reloc":
                    action = InstantActionBuilder.create_reloc(
                        action_id=f"action_{i+1}",
                        x=random.uniform(0, 20),
                        y=random.uniform(0, 15),
                        angle=random.uniform(0, 6.28)
                    )
                else:
                    # 使用简单动作
                    action = Action(
                        action_id=f"action_{i+1}",
                        action_type=action_type,
                        blocking_type="HARD",
                        action_description=f"{action_type}动作"
                    )
                
                actions.append(action)
            
            # 创建InstantActions消息
            instant_actions_msg = InstantActionsMessage(
                header_id=random.randint(1000, 9999),
                actions=actions,
                timestamp=datetime.now(timezone.utc).isoformat(),
                version="2.0.0",
                manufacturer="Demo_Manufacturer",
                serial_number="AGV_DEMO_001"
            )
            
            # 显示在输入框
            self.instant_actions_input.delete(1.0, tk.END)
            self.instant_actions_input.insert(tk.END, json.dumps(instant_actions_msg.get_message_dict(), indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"生成InstantActions消息失败: {str(e)}")
    
    def convert_instant_actions_to_tcp(self):
        """转换InstantActions为TCP协议"""
        try:
            # 获取输入的VDA5050 InstantActions
            instant_actions_json = self.instant_actions_input.get(1.0, tk.END).strip()
            if not instant_actions_json:
                messagebox.showwarning("警告", "请先生成或输入InstantActions消息")
                return
            
            instant_actions_data = json.loads(instant_actions_json)
            
            # 转换为TCP协议
            tcp_result = self.instant_actions_converter.convert_vda5050_instant_actions(instant_actions_data)
            
            # 显示结果
            self.instant_actions_output.delete(1.0, tk.END)
            self.instant_actions_output.insert(tk.END, json.dumps(tcp_result, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"InstantActions转换失败: {str(e)}")
    
    def generate_random_tcp_state(self):
        """生成随机TCP State数据"""
        try:
            # 生成随机错误和警告列表
            error_messages = ["连接超时", "传感器故障", "导航错误", "电池异常", "机械故障"]
            warning_messages = ["电量低", "信号弱", "温度偏高"]
            
            num_errors = random.randint(0, 2)
            num_warnings = random.randint(0, 2)
            
            tcp_state = {
                "vehicle_id": f"AGV_{random.randint(1, 999):03d}",
                "create_on": datetime.now(timezone.utc).isoformat(),
                "current_map": f"map_{random.randint(1, 10)}",
                "x": round(random.uniform(0, 20), 2),
                "y": round(random.uniform(0, 15), 2),
                "angle": round(random.uniform(0, 360), 1),
                "vx": round(random.uniform(-1, 1), 2),
                "vy": round(random.uniform(-1, 1), 2),
                "w": round(random.uniform(-0.5, 0.5), 2),
                "is_stop": random.choice([True, False]),
                "confidence": round(random.uniform(0.7, 1.0), 2),
                "current_station": f"WS_{random.randint(1, 20):02d}",
                "target_id": f"WS_{random.randint(1, 20):02d}",
                "target_dist": round(random.uniform(0, 50), 1),
                "task_status": random.choice(["IDLE", "DRIVING", "ACTING", "FINISHED"]),
                "task_type": random.choice(["NONE", "pick", "drop", "move"]),
                "battery_level": round(random.uniform(0.2, 1.0), 2),
                "charging": random.choice([True, False]),
                "voltage": round(random.uniform(40, 52), 1),
                "emergency": random.choice([True, False]),
                "blocked": random.choice([True, False]),
                "errors": random.sample(error_messages, num_errors) if num_errors > 0 else [],
                "warnings": random.sample(warning_messages, num_warnings) if num_warnings > 0 else []
            }
            
            # 显示在输入框
            self.state_input.delete(1.0, tk.END)
            self.state_input.insert(tk.END, json.dumps(tcp_state, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"生成TCP State数据失败: {str(e)}")
    
    def convert_tcp_state_to_vda5050(self):
        """转换TCP State为VDA5050"""
        try:
            # 获取输入的TCP State
            tcp_state_json = self.state_input.get(1.0, tk.END).strip()
            if not tcp_state_json:
                messagebox.showwarning("警告", "请先生成或输入TCP State数据")
                return
            
            tcp_state_data = json.loads(tcp_state_json)
            
            # 转换为VDA5050 State
            vda5050_state = self.state_converter.convert_agv_data_to_vda5050_state(tcp_state_data)
            
            # 显示结果
            self.state_output.delete(1.0, tk.END)
            self.state_output.insert(tk.END, json.dumps(vda5050_state.get_message_dict(), indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"TCP State转换失败: {str(e)}")
    
    def generate_random_tcp_state_for_visualization(self):
        """为可视化生成随机TCP State数据"""
        try:
            tcp_state = {
                "vehicle_id": f"AGV_{random.randint(1, 999):03d}",
                "create_on": datetime.now(timezone.utc).isoformat(),
                "current_map": f"factory_floor_{random.randint(1, 5)}",
                "x": round(random.uniform(0, 20), 2),
                "y": round(random.uniform(0, 15), 2),
                "angle": round(random.uniform(0, 360), 1),
                "vx": round(random.uniform(-1, 1), 2),
                "vy": round(random.uniform(-1, 1), 2),
                "w": round(random.uniform(-0.5, 0.5), 2),
                "is_stop": random.choice([True, False]),
                "confidence": round(random.uniform(0.7, 1.0), 2),
                "current_station": f"WS_{random.randint(1, 20):02d}",
                "target_id": f"WS_{random.randint(1, 20):02d}",
                "target_dist": round(random.uniform(0, 50), 1),
                "task_status": random.choice(["IDLE", "DRIVING", "ACTING", "FINISHED"])
            }
            
            # 显示在输入框
            self.visualization_input.delete(1.0, tk.END)
            self.visualization_input.insert(tk.END, json.dumps(tcp_state, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"生成TCP State数据失败: {str(e)}")
    
    def convert_tcp_state_to_visualization(self):
        """转换TCP State为VDA5050 Visualization"""
        try:
            # 获取输入的TCP State
            tcp_state_json = self.visualization_input.get(1.0, tk.END).strip()
            if not tcp_state_json:
                messagebox.showwarning("警告", "请先生成或输入TCP State数据")
                return
            
            tcp_state_data = json.loads(tcp_state_json)
            
            # 转换为VDA5050 Visualization
            visualization_msg = self.visualization_converter.convert_tcp_state_to_visualization(tcp_state_data)
            
            # 显示结果
            self.visualization_output.delete(1.0, tk.END)
            self.visualization_output.insert(tk.END, json.dumps(visualization_msg.get_message_dict(), indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"TCP State转Visualization失败: {str(e)}")


def main():
    """主函数"""
    root = tk.Tk()
    app = VDA5050TCPDemo(root)
    root.mainloop()


if __name__ == "__main__":
    main() 