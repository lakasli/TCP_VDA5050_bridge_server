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
from tcp.manufacturer_a import ManufacturerATCPProtocol


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
        # 创建TCP协议处理器实例，用于统一生成ID
        self.tcp_protocol = ManufacturerATCPProtocol()
        
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
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 生成按钮
        ttk.Button(button_frame, text="生成随机Order", 
                  command=lambda: self.generate_random_order()).pack(side=tk.LEFT, padx=(0, 10))
        
        # 格式化按钮
        ttk.Button(button_frame, text="格式化JSON", 
                  command=lambda: self.format_json_text(self.order_input)).pack(side=tk.LEFT)
        
        # 输入文本框
        self.order_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.order_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：TCP输出
        right_frame = ttk.LabelFrame(paned, text="TCP协议输出")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为TCP", 
                  command=lambda: self.convert_order_to_tcp()).pack(pady=5)
        
        # TCP协议信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 端口号显示框
        port_frame = ttk.LabelFrame(info_frame, text="端口号")
        port_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.order_port_var = tk.StringVar(value="19206")
        self.order_port_label = ttk.Label(port_frame, textvariable=self.order_port_var, 
                                         font=("Arial", 12, "bold"), foreground="blue")
        self.order_port_label.pack(pady=5)
        
        # 报文类型显示框
        msg_type_frame = ttk.LabelFrame(info_frame, text="报文类型")
        msg_type_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.order_msg_type_var = tk.StringVar(value="3066")
        self.order_msg_type_label = ttk.Label(msg_type_frame, textvariable=self.order_msg_type_var,
                                             font=("Arial", 12, "bold"), foreground="green")
        self.order_msg_type_label.pack(pady=5)
        
        # 上半部分：协议转换结果
        protocol_frame = ttk.LabelFrame(right_frame, text="协议转换结果")
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        self.order_output = scrolledtext.ScrolledText(protocol_frame, height=12, width=50)
        self.order_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 中间部分：实际TCP数据包
        packet_frame = ttk.LabelFrame(right_frame, text="实际TCP数据包")
        packet_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 2))
        
        self.order_packet_output = scrolledtext.ScrolledText(packet_frame, height=8, width=50)
        self.order_packet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 下半部分：二进制TCP数据包
        binary_frame = ttk.LabelFrame(right_frame, text="二进制TCP数据包 (16字节包头)")
        binary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        self.order_binary_output = scrolledtext.ScrolledText(binary_frame, height=8, width=50)
        self.order_binary_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
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
        
        # 动作选择框架
        action_frame = ttk.Frame(left_frame)
        action_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 动作类型选择标签
        ttk.Label(action_frame, text="选择动作类型:").pack(side=tk.LEFT, padx=(0, 5))
        
        # 动作类型下拉栏
        self.action_type_var = tk.StringVar()
        action_types = ["pick", "drop", "translate", "turn", "reloc", "startPause", "stopPause"]
        self.action_type_combo = ttk.Combobox(action_frame, textvariable=self.action_type_var, 
                                             values=action_types, state="readonly", width=15)
        self.action_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.action_type_combo.set(action_types[0])  # 设置默认值
        
        # 绑定下拉栏选择事件
        self.action_type_combo.bind('<<ComboboxSelected>>', self.on_action_type_changed)
        
        # 生成按钮
        ttk.Button(action_frame, text="生成InstantActions", 
                  command=lambda: self.generate_selected_instant_actions()).pack(side=tk.LEFT, padx=(0, 10))
        
        # 格式化按钮
        ttk.Button(action_frame, text="格式化JSON", 
                  command=lambda: self.format_json_text(self.instant_actions_input)).pack(side=tk.LEFT)
        
        # 输入文本框
        self.instant_actions_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.instant_actions_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：TCP输出
        right_frame = ttk.LabelFrame(paned, text="TCP协议输出")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为TCP", 
                  command=lambda: self.convert_instant_actions_to_tcp()).pack(pady=5)
        
        # TCP协议信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 端口号显示框
        port_frame = ttk.LabelFrame(info_frame, text="端口号")
        port_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.instant_actions_port_var = tk.StringVar(value="根据动作类型")
        self.instant_actions_port_label = ttk.Label(port_frame, textvariable=self.instant_actions_port_var, 
                                                   font=("Arial", 12, "bold"), foreground="blue")
        self.instant_actions_port_label.pack(pady=5)
        
        # 报文类型显示框
        msg_type_frame = ttk.LabelFrame(info_frame, text="报文类型")
        msg_type_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.instant_actions_msg_type_var = tk.StringVar(value="根据动作类型")
        self.instant_actions_msg_type_label = ttk.Label(msg_type_frame, textvariable=self.instant_actions_msg_type_var,
                                                       font=("Arial", 12, "bold"), foreground="green")
        self.instant_actions_msg_type_label.pack(pady=5)
        
        # 上半部分：协议转换结果
        protocol_frame = ttk.LabelFrame(right_frame, text="协议转换结果")
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        self.instant_actions_output = scrolledtext.ScrolledText(protocol_frame, height=12, width=50)
        self.instant_actions_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 中间部分：实际TCP数据包
        packet_frame = ttk.LabelFrame(right_frame, text="实际TCP数据包")
        packet_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 2))
        
        self.instant_actions_packet_output = scrolledtext.ScrolledText(packet_frame, height=8, width=50)
        self.instant_actions_packet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 下半部分：二进制TCP数据包
        binary_frame = ttk.LabelFrame(right_frame, text="二进制TCP数据包 (16字节包头)")
        binary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        self.instant_actions_binary_output = scrolledtext.ScrolledText(binary_frame, height=8, width=50)
        self.instant_actions_binary_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化时更新显示
        self.update_instant_actions_info("pick")
    
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
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 生成按钮
        ttk.Button(button_frame, text="生成随机TCP State", 
                  command=lambda: self.generate_random_tcp_state()).pack(side=tk.LEFT, padx=(0, 10))
        
        # 格式化按钮
        ttk.Button(button_frame, text="格式化JSON", 
                  command=lambda: self.format_json_text(self.state_input)).pack(side=tk.LEFT)
        
        # 输入文本框
        self.state_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.state_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：VDA5050输出
        right_frame = ttk.LabelFrame(paned, text="VDA5050 State消息")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为VDA5050", 
                  command=lambda: self.convert_tcp_state_to_vda5050()).pack(pady=5)
        
        # TCP源信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 数据源端口显示框
        port_frame = ttk.LabelFrame(info_frame, text="数据源端口")
        port_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.state_port_var = tk.StringVar(value="19301")
        self.state_port_label = ttk.Label(port_frame, textvariable=self.state_port_var, 
                                         font=("Arial", 12, "bold"), foreground="blue")
        self.state_port_label.pack(pady=5)
        
        # 转换方向显示框
        direction_frame = ttk.LabelFrame(info_frame, text="转换方向")
        direction_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.state_direction_var = tk.StringVar(value="TCP→VDA5050")
        self.state_direction_label = ttk.Label(direction_frame, textvariable=self.state_direction_var,
                                              font=("Arial", 12, "bold"), foreground="green")
        self.state_direction_label.pack(pady=5)
        
        # 上半部分：VDA5050转换结果
        protocol_frame = ttk.LabelFrame(right_frame, text="VDA5050转换结果")
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        self.state_output = scrolledtext.ScrolledText(protocol_frame, height=12, width=50)
        self.state_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 下半部分：原始TCP数据包
        packet_frame = ttk.LabelFrame(right_frame, text="原始TCP数据包")
        packet_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        self.state_packet_output = scrolledtext.ScrolledText(packet_frame, height=12, width=50)
        self.state_packet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
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
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 生成按钮
        ttk.Button(button_frame, text="生成随机TCP State", 
                  command=lambda: self.generate_random_tcp_state_for_visualization()).pack(side=tk.LEFT, padx=(0, 10))
        
        # 格式化按钮
        ttk.Button(button_frame, text="格式化JSON", 
                  command=lambda: self.format_json_text(self.visualization_input)).pack(side=tk.LEFT)
        
        # 输入文本框
        self.visualization_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.visualization_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：VDA5050输出
        right_frame = ttk.LabelFrame(paned, text="VDA5050 Visualization消息")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为VDA5050", 
                  command=lambda: self.convert_tcp_state_to_visualization()).pack(pady=5)
        
        # TCP源信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 数据源端口显示框
        port_frame = ttk.LabelFrame(info_frame, text="数据源端口")
        port_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.visualization_port_var = tk.StringVar(value="19301")
        self.visualization_port_label = ttk.Label(port_frame, textvariable=self.visualization_port_var, 
                                                 font=("Arial", 12, "bold"), foreground="blue")
        self.visualization_port_label.pack(pady=5)
        
        # 转换方向显示框
        direction_frame = ttk.LabelFrame(info_frame, text="转换方向")
        direction_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.visualization_direction_var = tk.StringVar(value="TCP→VDA5050")
        self.visualization_direction_label = ttk.Label(direction_frame, textvariable=self.visualization_direction_var,
                                                      font=("Arial", 12, "bold"), foreground="green")
        self.visualization_direction_label.pack(pady=5)
        
        # 上半部分：VDA5050转换结果
        protocol_frame = ttk.LabelFrame(right_frame, text="VDA5050转换结果")
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        self.visualization_output = scrolledtext.ScrolledText(protocol_frame, height=12, width=50)
        self.visualization_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 下半部分：原始TCP数据包
        packet_frame = ttk.LabelFrame(right_frame, text="原始TCP数据包")
        packet_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        self.visualization_packet_output = scrolledtext.ScrolledText(packet_frame, height=12, width=50)
        self.visualization_packet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_connection_tab(self, notebook):
        """创建Connection TCP→VDA5050转换标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Connection (TCP→VDA5050)")
        
        # 分割窗口
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：TCP Connection输入
        left_frame = ttk.LabelFrame(paned, text="TCP Connection数据")
        paned.add(left_frame, weight=1)
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 生成按钮
        ttk.Button(button_frame, text="生成随机TCP Connection", 
                  command=lambda: self.generate_random_tcp_connection()).pack(side=tk.LEFT, padx=(0, 10))
        
        # 格式化按钮
        ttk.Button(button_frame, text="格式化JSON", 
                  command=lambda: self.format_json_text(self.connection_input)).pack(side=tk.LEFT)
        
        # 输入文本框
        self.connection_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.connection_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：VDA5050输出
        right_frame = ttk.LabelFrame(paned, text="VDA5050 Connection消息")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为VDA5050", 
                  command=lambda: self.convert_tcp_connection_to_vda5050()).pack(pady=5)
        
        # TCP源信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 数据源端口显示框
        port_frame = ttk.LabelFrame(info_frame, text="数据源端口")
        port_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.connection_port_var = tk.StringVar(value="19200")
        self.connection_port_label = ttk.Label(port_frame, textvariable=self.connection_port_var, 
                                              font=("Arial", 12, "bold"), foreground="blue")
        self.connection_port_label.pack(pady=5)
        
        # 转换方向显示框
        direction_frame = ttk.LabelFrame(info_frame, text="转换方向")
        direction_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.connection_direction_var = tk.StringVar(value="TCP→VDA5050")
        self.connection_direction_label = ttk.Label(direction_frame, textvariable=self.connection_direction_var,
                                                   font=("Arial", 12, "bold"), foreground="green")
        self.connection_direction_label.pack(pady=5)
        
        # 上半部分：VDA5050转换结果
        protocol_frame = ttk.LabelFrame(right_frame, text="VDA5050转换结果")
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        self.connection_output = scrolledtext.ScrolledText(protocol_frame, height=12, width=50)
        self.connection_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 下半部分：原始TCP数据包
        packet_frame = ttk.LabelFrame(right_frame, text="原始TCP数据包")
        packet_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        self.connection_packet_output = scrolledtext.ScrolledText(packet_frame, height=12, width=50)
        self.connection_packet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_factsheet_tab(self, notebook):
        """创建Factsheet TCP→VDA5050转换标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Factsheet (TCP→VDA5050)")
        
        # 分割窗口
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：TCP Factsheet输入
        left_frame = ttk.LabelFrame(paned, text="TCP Factsheet数据")
        paned.add(left_frame, weight=1)
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 生成按钮
        ttk.Button(button_frame, text="生成随机TCP Factsheet", 
                  command=lambda: self.generate_random_tcp_factsheet()).pack(side=tk.LEFT, padx=(0, 10))
        
        # 格式化按钮
        ttk.Button(button_frame, text="格式化JSON", 
                  command=lambda: self.format_json_text(self.factsheet_input)).pack(side=tk.LEFT)
        
        # 输入文本框
        self.factsheet_input = scrolledtext.ScrolledText(left_frame, height=25, width=50)
        self.factsheet_input.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 右侧：VDA5050输出
        right_frame = ttk.LabelFrame(paned, text="VDA5050 Factsheet消息")
        paned.add(right_frame, weight=1)
        
        # 转换按钮
        ttk.Button(right_frame, text="转换为VDA5050", 
                  command=lambda: self.convert_tcp_factsheet_to_vda5050()).pack(pady=5)
        
        # TCP源信息框架
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(pady=5, padx=5, fill=tk.X)
        
        # 数据源端口显示框
        port_frame = ttk.LabelFrame(info_frame, text="数据源端口")
        port_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.factsheet_port_var = tk.StringVar(value="19200")
        self.factsheet_port_label = ttk.Label(port_frame, textvariable=self.factsheet_port_var, 
                                             font=("Arial", 12, "bold"), foreground="blue")
        self.factsheet_port_label.pack(pady=5)
        
        # 转换方向显示框
        direction_frame = ttk.LabelFrame(info_frame, text="转换方向")
        direction_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.factsheet_direction_var = tk.StringVar(value="TCP→VDA5050")
        self.factsheet_direction_label = ttk.Label(direction_frame, textvariable=self.factsheet_direction_var,
                                                  font=("Arial", 12, "bold"), foreground="green")
        self.factsheet_direction_label.pack(pady=5)
        
        # 上半部分：VDA5050转换结果
        protocol_frame = ttk.LabelFrame(right_frame, text="VDA5050转换结果")
        protocol_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))
        
        self.factsheet_output = scrolledtext.ScrolledText(protocol_frame, height=12, width=50)
        self.factsheet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 下半部分：原始TCP数据包
        packet_frame = ttk.LabelFrame(right_frame, text="原始TCP数据包")
        packet_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        
        self.factsheet_packet_output = scrolledtext.ScrolledText(packet_frame, height=12, width=50)
        self.factsheet_packet_output.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
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
            
            # 使用TCP协议处理器生成统一的ID
            base_order_id = str(random.randint(168000, 169999))  # 生成168461这样的基础ID
            header_id = int(self.tcp_protocol.generate_task_id().split('_')[-1])  # 提取数字作为header_id
            order_id = self.tcp_protocol.generate_task_id(base_order_id).replace(f"{base_order_id}_", base_order_id)  # 使用基础ID本身作为order_id
            
            # 创建Order消息
            order_msg = OrderMessage(
                header_id=header_id,
                order_id=base_order_id,  # 直接使用基础ID
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
            
            # 显示协议转换结果
            self.order_output.delete(1.0, tk.END)
            self.order_output.insert(tk.END, json.dumps(tcp_result, indent=2, ensure_ascii=False))
            
            # 生成实际TCP数据包
            tcp_packet = self.generate_tcp_packet(tcp_result, 19206, 3066)
            
            # 显示实际TCP数据包
            self.order_packet_output.delete(1.0, tk.END)
            self.order_packet_output.insert(tk.END, tcp_packet)
            
            # 生成二进制TCP数据包
            binary_packet = self.tcp_protocol.create_binary_tcp_packet(3066, tcp_result)
            binary_display = self.format_binary_packet(binary_packet, 3066)
            
            # 显示二进制TCP数据包
            self.order_binary_output.delete(1.0, tk.END)
            self.order_binary_output.insert(tk.END, binary_display)
            
        except Exception as e:
            messagebox.showerror("错误", f"Order转换失败: {str(e)}")
            # 错误时清空显示
            self.order_packet_output.delete(1.0, tk.END)
            self.order_packet_output.insert(tk.END, "转换失败，无法生成数据包")
            self.order_binary_output.delete(1.0, tk.END)
            self.order_binary_output.insert(tk.END, "转换失败，无法生成二进制数据包")
    
    def generate_selected_instant_actions(self):
        """根据选择的动作类型生成InstantActions消息"""
        try:
            # 获取选择的动作类型
            selected_action_type = self.action_type_var.get()
            if not selected_action_type:
                messagebox.showwarning("警告", "请选择动作类型")
                return
            
            # 创建动作
            actions = []
            
            # 只生成一个动作
            if selected_action_type == "translate":
                action = InstantActionBuilder.create_translate(
                    action_id="action_1",
                    dist=round(random.uniform(0.5, 5.0), 2),
                    vx=round(random.uniform(0.1, 1.0), 2)
                )
            elif selected_action_type == "turn":
                action = InstantActionBuilder.create_turn(
                    action_id="action_1",
                    angle=round(random.uniform(0.5, 3.14), 2),
                    vw=round(random.uniform(0.1, 0.5), 2)
                )
            elif selected_action_type == "reloc":
                action = InstantActionBuilder.create_reloc(
                    action_id="action_1",
                    x=round(random.uniform(0, 20), 2),
                    y=round(random.uniform(0, 15), 2),
                    angle=round(random.uniform(0, 6.28), 2)
                )
            else:
                # 使用简单动作 (pick, drop, startPause, stopPause)
                action_params = []
                
                # 为某些动作类型添加随机参数
                if selected_action_type in ["pick", "drop"]:
                    # 添加位置参数
                    action_params.append(ActionParameter(
                        key="loadId",
                        value=f"LOAD_{random.randint(100, 999)}"
                    ))
                    action_params.append(ActionParameter(
                        key="loadType",
                        value=random.choice(["PALLET", "BOX", "CONTAINER"])
                    ))
                
                action = Action(
                    action_id="action_1",
                    action_type=selected_action_type,
                    action_parameters=action_params,
                    blocking_type=random.choice(["HARD", "SOFT", "NONE"]),
                    action_description=f"{selected_action_type}动作 - 随机参数"
                )
            
            actions.append(action)
            
            # 使用TCP协议处理器生成统一的header_id
            base_header_id = str(random.randint(168000, 169999))  # 生成类似168461的基础ID
            
            # 创建InstantActions消息
            instant_actions_msg = InstantActionsMessage(
                header_id=int(base_header_id),  # 直接使用基础ID作为header_id
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
            
            # 使用TCP协议处理器生成统一的header_id
            base_header_id = str(random.randint(168000, 169999))  # 生成类似168461的基础ID
            
            # 创建InstantActions消息
            instant_actions_msg = InstantActionsMessage(
                header_id=int(base_header_id),  # 直接使用基础ID作为header_id
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
            
            # 分析动作配置，获取端口号和报文类型信息
            action_configs = self.instant_actions_converter.analyze_instant_action_configs(instant_actions_data)
            
            # 更新端口号和报文类型显示
            if action_configs:
                if len(action_configs) == 1:
                    # 单个动作，显示具体的端口号和报文类型
                    config = action_configs[0]
                    self.instant_actions_port_var.set(str(config['port']))
                    self.instant_actions_msg_type_var.set(str(config['messageType']))
                else:
                    # 多个动作，显示"多端口"
                    ports = list(set([str(config['port']) for config in action_configs]))
                    msg_types = list(set([str(config['messageType']) for config in action_configs]))
                    self.instant_actions_port_var.set(f"多端口: {', '.join(ports)}")
                    self.instant_actions_msg_type_var.set(f"多类型: {', '.join(msg_types)}")
            else:
                self.instant_actions_port_var.set("无有效动作")
                self.instant_actions_msg_type_var.set("无有效动作")
            
            # 转换为TCP协议
            tcp_result = self.instant_actions_converter.convert_vda5050_instant_actions(instant_actions_data)
            
            # 显示协议转换结果
            self.instant_actions_output.delete(1.0, tk.END)
            self.instant_actions_output.insert(tk.END, json.dumps(tcp_result, indent=2, ensure_ascii=False))
            
            # 生成实际TCP数据包
            try:
                port_str = self.instant_actions_port_var.get()
                msg_type_str = self.instant_actions_msg_type_var.get()
                
                # 提取端口号
                if "多端口" in port_str:
                    port = 19206  # 使用默认端口
                else:
                    port = int(port_str) if port_str.isdigit() else 19206
                
                # 提取报文类型
                if "多类型" in msg_type_str:
                    msg_type = 3066  # 使用默认报文类型
                else:
                    msg_type = int(msg_type_str) if msg_type_str.isdigit() else 3066
                    
            except:
                port = 19206
                msg_type = 3066
                
            tcp_packet = self.generate_tcp_packet(tcp_result, port, msg_type)
            
            # 显示实际TCP数据包
            self.instant_actions_packet_output.delete(1.0, tk.END)
            self.instant_actions_packet_output.insert(tk.END, tcp_packet)
            
            # 生成二进制TCP数据包
            binary_packet = self.tcp_protocol.create_binary_tcp_packet(msg_type, tcp_result)
            binary_display = self.format_binary_packet(binary_packet, msg_type)
            
            # 显示二进制TCP数据包
            self.instant_actions_binary_output.delete(1.0, tk.END)
            self.instant_actions_binary_output.insert(tk.END, binary_display)
            
        except Exception as e:
            messagebox.showerror("错误", f"InstantActions转换失败: {str(e)}")
            # 错误时重置显示
            self.instant_actions_port_var.set("转换失败")
            self.instant_actions_msg_type_var.set("转换失败")
            self.instant_actions_packet_output.delete(1.0, tk.END)
            self.instant_actions_packet_output.insert(tk.END, "转换失败，无法生成数据包")
            self.instant_actions_binary_output.delete(1.0, tk.END)
            self.instant_actions_binary_output.insert(tk.END, "转换失败，无法生成二进制数据包")
    
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
            
            # 显示VDA5050转换结果
            self.state_output.delete(1.0, tk.END)
            self.state_output.insert(tk.END, json.dumps(vda5050_state.get_message_dict(), indent=2, ensure_ascii=False))
            
            # 显示原始TCP数据包格式
            tcp_packet = self.format_tcp_source_packet(tcp_state_data, 19301, 1001)
            self.state_packet_output.delete(1.0, tk.END)
            self.state_packet_output.insert(tk.END, tcp_packet)
            
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
            
            # 显示VDA5050转换结果
            self.visualization_output.delete(1.0, tk.END)
            self.visualization_output.insert(tk.END, json.dumps(visualization_msg.get_message_dict(), indent=2, ensure_ascii=False))
            
            # 显示原始TCP数据包格式
            tcp_packet = self.format_tcp_source_packet(tcp_state_data, 19301, 1001)
            self.visualization_packet_output.delete(1.0, tk.END)
            self.visualization_packet_output.insert(tk.END, tcp_packet)
            
        except Exception as e:
            messagebox.showerror("错误", f"TCP State转Visualization失败: {str(e)}")
    
    def on_action_type_changed(self, event):
        """动作类型下拉栏选择改变时的处理"""
        selected_action = self.action_type_var.get()
        self.update_instant_actions_info(selected_action)
    
    def update_instant_actions_info(self, action_type):
        """根据动作类型更新端口号和报文类型显示"""
        try:
            # 获取动作配置
            config = self.instant_actions_converter.ACTION_CONFIG.get(action_type)
            if config:
                self.instant_actions_port_var.set(str(config.port))
                self.instant_actions_msg_type_var.set(str(config.message_type))
            else:
                self.instant_actions_port_var.set("未知")
                self.instant_actions_msg_type_var.set("未知")
        except Exception as e:
            self.instant_actions_port_var.set("错误")
            self.instant_actions_msg_type_var.set("错误")
    
    def format_json_text(self, text_widget):
        """格式化文本框中的JSON内容"""
        try:
            # 获取文本内容
            content = text_widget.get(1.0, tk.END).strip()
            if not content:
                messagebox.showwarning("警告", "文本框为空，无法格式化")
                return
            
            # 解析并重新格式化JSON
            parsed_json = json.loads(content)
            formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            
            # 更新文本框内容
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, formatted_json)
            
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON格式错误", f"JSON格式不正确：{str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"格式化失败：{str(e)}")
    
    def generate_random_tcp_connection(self):
        """生成随机TCP Connection数据"""
        try:
            tcp_connection = {
                "vehicle_id": f"AGV_{random.randint(1, 999):03d}",
                "create_on": datetime.now(timezone.utc).isoformat(),
                "connection_state": random.choice(["ONLINE", "OFFLINE", "CONNECTING", "DISCONNECTING"]),
                "manufacturer": "Demo_Manufacturer",
                "model": "AGV_Model_" + random.choice(["A", "B", "C"]),
                "version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "serial_number": f"SN{random.randint(100000, 999999)}",
                "network_info": {
                    "ip_address": f"192.168.1.{random.randint(100, 200)}",
                    "port": 19200,
                    "signal_strength": random.randint(-80, -30)  # dBm
                },
                "capabilities": [
                    "navigate",
                    "pick",
                    "drop",
                    random.choice(["load_handling", "obstacle_avoidance", "battery_management"])
                ]
            }
            
            # 显示在输入框
            self.connection_input.delete(1.0, tk.END)
            self.connection_input.insert(tk.END, json.dumps(tcp_connection, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"生成TCP Connection数据失败: {str(e)}")
    
    def convert_tcp_connection_to_vda5050(self):
        """转换TCP Connection为VDA5050协议"""
        try:
            # 获取输入的TCP Connection
            connection_json = self.connection_input.get(1.0, tk.END).strip()
            if not connection_json:
                messagebox.showwarning("警告", "请先生成或输入TCP Connection数据")
                return
            
            tcp_connection_data = json.loads(connection_json)
            
            # 创建VDA5050 Connection消息
            connection_msg = ConnectionMessage(
                header_id=random.randint(168000, 169999),
                timestamp=tcp_connection_data.get("create_on", datetime.now(timezone.utc).isoformat()),
                version="2.0.0",
                manufacturer=tcp_connection_data.get("manufacturer", "Unknown"),
                serial_number=tcp_connection_data.get("serial_number", tcp_connection_data.get("vehicle_id", "")),
                connection_state=tcp_connection_data.get("connection_state", "UNKNOWN")
            )
            
            # 显示VDA5050转换结果
            self.connection_output.delete(1.0, tk.END)
            self.connection_output.insert(tk.END, json.dumps(connection_msg.get_message_dict(), indent=2, ensure_ascii=False))
            
            # 显示原始TCP数据包格式
            tcp_packet = self.format_tcp_source_packet(tcp_connection_data, 19200, 9001)
            self.connection_packet_output.delete(1.0, tk.END)
            self.connection_packet_output.insert(tk.END, tcp_packet)
            
        except Exception as e:
            messagebox.showerror("错误", f"TCP Connection转换失败: {str(e)}")
    
    def generate_random_tcp_factsheet(self):
        """生成随机TCP Factsheet数据"""
        try:
            tcp_factsheet = {
                "vehicle_id": f"AGV_{random.randint(1, 999):03d}",
                "create_on": datetime.now(timezone.utc).isoformat(),
                "manufacturer": "Demo_Manufacturer",
                "model": "AGV_Model_" + random.choice(["A", "B", "C"]),
                "version": f"v{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                "serial_number": f"SN{random.randint(100000, 999999)}",
                "type_specification": {
                    "series_name": "DEMO_AGV_SERIES",
                    "agv_kinematic": random.choice(["DIFF", "OMNI", "BICYCLE"]),
                    "agv_class": random.choice(["CARRIER", "TUGGER", "FORKLIFT"]),
                    "max_load_mass": round(random.uniform(50.0, 200.0), 1),
                    "localization_types": ["NATURAL", "REFLECTOR"],
                    "navigation_types": ["AUTONOMOUS"]
                },
                "physical_parameters": {
                    "speed_min": 0.0,
                    "speed_max": round(random.uniform(1.5, 3.0), 1),
                    "acceleration_max": round(random.uniform(0.8, 2.0), 1),
                    "deceleration_max": round(random.uniform(1.0, 2.5), 1),
                    "height_min": 0.1,
                    "height_max": round(random.uniform(1.8, 2.5), 1),
                    "width": round(random.uniform(0.6, 1.2), 1),
                    "length": round(random.uniform(1.0, 2.0), 1)
                },
                "capabilities": {
                    "supported_actions": ["pick", "drop", "move", "wait", "translate", "turn"],
                    "max_payload": round(random.uniform(50, 200), 1),
                    "battery_capacity": round(random.uniform(50, 100), 1),
                    "charging_types": ["automatic", "manual"],
                    "communication_protocols": ["TCP", "MQTT", "HTTP"]
                },
                "safety_features": {
                    "emergency_stop": True,
                    "collision_avoidance": True,
                    "safety_scanners": random.randint(2, 6),
                    "warning_lights": True,
                    "safety_rated": random.choice(["PLd", "PLe"])
                }
            }
            
            # 显示在输入框
            self.factsheet_input.delete(1.0, tk.END)
            self.factsheet_input.insert(tk.END, json.dumps(tcp_factsheet, indent=2, ensure_ascii=False))
            
        except Exception as e:
            messagebox.showerror("错误", f"生成TCP Factsheet数据失败: {str(e)}")
    
    def convert_tcp_factsheet_to_vda5050(self):
        """转换TCP Factsheet为VDA5050协议"""
        try:
            # 获取输入的TCP Factsheet
            factsheet_json = self.factsheet_input.get(1.0, tk.END).strip()
            if not factsheet_json:
                messagebox.showwarning("警告", "请先生成或输入TCP Factsheet数据")
                return
            
            tcp_factsheet_data = json.loads(factsheet_json)
            
            # 从TCP数据创建VDA5050格式的Factsheet
            from vda5050.factsheet_message import TypeSpecification, ProtocolLimits
            
            type_spec_data = tcp_factsheet_data.get("type_specification", {})
            physical_params_data = tcp_factsheet_data.get("physical_parameters", {})
            
            # 创建类型规格
            type_spec = TypeSpecification(
                series_name=type_spec_data.get("series_name", "UNKNOWN_SERIES"),
                agv_kinematic=type_spec_data.get("agv_kinematic", "DIFF"),
                agv_class=type_spec_data.get("agv_class", "CARRIER"),
                max_load_mass=type_spec_data.get("max_load_mass", 100.0),
                localization_types=type_spec_data.get("localization_types", ["NATURAL"]),
                navigation_types=type_spec_data.get("navigation_types", ["AUTONOMOUS"]),
                series_description=f"转换自TCP的{type_spec_data.get('series_name', 'AGV')}系列"
            )
            
            # 创建物理参数
            physical_params = PhysicalParameters(
                speed_min=physical_params_data.get("speed_min", 0.0),
                speed_max=physical_params_data.get("speed_max", 2.0),
                acceleration_max=physical_params_data.get("acceleration_max", 1.0),
                deceleration_max=physical_params_data.get("deceleration_max", 1.5),
                height_min=physical_params_data.get("height_min", 0.1),
                height_max=physical_params_data.get("height_max", 2.0),
                width=physical_params_data.get("width", 0.8),
                length=physical_params_data.get("length", 1.5)
            )
            
            # 创建协议限制
            protocol_limits = ProtocolLimits(
                max_string_lens={"orderId": 100, "nodeId": 50},
                max_array_lens={"nodes": 100, "edges": 100},
                timing={"maxStatesArrayLength": 1000, "minOrderInterval": 1.0}
            )
            
            # 创建协议特性
            capabilities = tcp_factsheet_data.get("capabilities", {})
            protocol_features = {
                "optionalParameters": ["orderId", "orderUpdateId"],
                "agvActions": capabilities.get("supported_actions", ["move"]),
                "drivingDirection": "BOTH"
            }
            
            # 创建AGV几何信息
            agv_geometry = {
                "wheelDefinitions": [
                    {"type": "DRIVE", "isActiveDriven": True, "isActiveSteered": False, 
                     "position": {"x": 0.0, "y": 0.0, "theta": 0.0}}
                ],
                "envelopes2d": [
                    {"set": "body", "polygonPoints": [
                        {"x": -physical_params_data.get("width", 0.8)/2, "y": -physical_params_data.get("length", 1.5)/2},
                        {"x": physical_params_data.get("width", 0.8)/2, "y": -physical_params_data.get("length", 1.5)/2},
                        {"x": physical_params_data.get("width", 0.8)/2, "y": physical_params_data.get("length", 1.5)/2},
                        {"x": -physical_params_data.get("width", 0.8)/2, "y": physical_params_data.get("length", 1.5)/2}
                    ]}
                ]
            }
            
            # 创建载荷规格
            load_specification = {
                "loadPositions": ["LOAD_POS_1"],
                "loadSets": [
                    {
                        "setName": "DEFAULT_LOAD",
                        "loadType": "PALLET",
                        "loadPositions": ["LOAD_POS_1"],
                        "maxWeight": capabilities.get("max_payload", 100.0),
                        "minLoadhandlingTime": 5.0,
                        "maxLoadhandlingTime": 30.0
                    }
                ]
            }
            
            factsheet_msg = FactsheetMessage(
                header_id=random.randint(168000, 169999),
                type_specification=type_spec,
                physical_parameters=physical_params,
                protocol_limits=protocol_limits,
                protocol_features=protocol_features,
                agv_geometry=agv_geometry,
                load_specification=load_specification,
                timestamp=tcp_factsheet_data.get("create_on", datetime.now(timezone.utc).isoformat()),
                version="2.0.0",
                manufacturer=tcp_factsheet_data.get("manufacturer", "Unknown"),
                serial_number=tcp_factsheet_data.get("serial_number", tcp_factsheet_data.get("vehicle_id", ""))
            )
            
            # 显示VDA5050转换结果
            self.factsheet_output.delete(1.0, tk.END)
            self.factsheet_output.insert(tk.END, json.dumps(factsheet_msg.get_message_dict(), indent=2, ensure_ascii=False))
            
            # 显示原始TCP数据包格式
            tcp_packet = self.format_tcp_source_packet(tcp_factsheet_data, 19200, 9002)
            self.factsheet_packet_output.delete(1.0, tk.END)
            self.factsheet_packet_output.insert(tk.END, tcp_packet)
            
        except Exception as e:
            messagebox.showerror("错误", f"TCP Factsheet转换失败: {str(e)}")
    
    def generate_tcp_packet(self, tcp_data, port, message_type):
        """生成实际发送给小车的TCP数据包格式"""
        try:
            import struct
            from datetime import datetime
            
            # 创建TCP数据包头
            packet_header = f"""TCP数据包格式:
==========================================
目标地址: AGV_IP_ADDRESS
目标端口: {port}
报文类型: {message_type}
时间戳:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据长度: {len(json.dumps(tcp_data).encode('utf-8'))} 字节

==========================================
数据包内容 (JSON格式):
"""
            
            # 格式化数据内容
            if isinstance(tcp_data, dict):
                data_content = json.dumps(tcp_data, indent=2, ensure_ascii=False)
            elif isinstance(tcp_data, list):
                data_content = json.dumps(tcp_data, indent=2, ensure_ascii=False)
            else:
                data_content = str(tcp_data)
            
            # 添加数据包尾
            packet_footer = f"""

==========================================
数据包尾:
校验和: {abs(hash(data_content)) % 10000:04d}
包序号: {random.randint(1000, 9999)}
结束标志: 0xFF 0xFE
=========================================="""
            
            return packet_header + data_content + packet_footer
            
        except Exception as e:
            return f"数据包生成失败: {str(e)}"
    
    def format_tcp_source_packet(self, tcp_data, port, message_type):
        """格式化从小车接收到的TCP数据包"""
        try:
            from datetime import datetime
            
            # 创建TCP源数据包头
            packet_header = f"""TCP源数据包格式:
==========================================
源地址:   AGV_IP_ADDRESS
源端口:   {port}
报文类型: {message_type}
接收时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
数据长度: {len(json.dumps(tcp_data).encode('utf-8'))} 字节

==========================================
接收到的数据包内容 (JSON格式):
"""
            
            # 格式化数据内容
            if isinstance(tcp_data, dict):
                data_content = json.dumps(tcp_data, indent=2, ensure_ascii=False)
            elif isinstance(tcp_data, list):
                data_content = json.dumps(tcp_data, indent=2, ensure_ascii=False)
            else:
                data_content = str(tcp_data)
            
            # 添加数据包尾
            packet_footer = f"""

==========================================
数据包信息:
信号强度: -65 dBm
传输延迟: {random.randint(5, 25)} ms
包完整性: 检验通过 ✓
解析状态: 成功转换为VDA5050格式
=========================================="""
            
            return packet_header + data_content + packet_footer
            
        except Exception as e:
            return f"数据包格式化失败: {str(e)}"
    
    def format_binary_packet(self, binary_data, message_type):
        """格式化二进制TCP数据包显示"""
        try:
            from datetime import datetime
            
            if not binary_data:
                return "二进制数据包生成失败"
            
            # 解析16字节包头
            if len(binary_data) < 16:
                return "数据包长度不足16字节"
            
            sync_header = binary_data[0]
            version = binary_data[1]
            sequence = int.from_bytes(binary_data[2:4], 'big')
            data_length = int.from_bytes(binary_data[4:8], 'big')
            msg_type = int.from_bytes(binary_data[8:10], 'big')
            reserved = binary_data[10:16]
            payload = binary_data[16:]
            
            # 创建格式化显示
            packet_info = f"""二进制TCP数据包分析:
==========================================
数据包总长度: {len(binary_data)} 字节
生成时间:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

包头信息 (16字节):
------------------------------------------
同步头:       0x{sync_header:02X} ({sync_header})
版本号:       0x{version:02X} ({version})
序列号:       {sequence}
数据长度:     {data_length} 字节
消息类型:     {msg_type}
保留字段:     {reserved.hex().upper()}

数据内容 ({data_length}字节):
------------------------------------------
"""
            
            # 格式化完整数据包的十六进制显示
            hex_data = binary_data.hex().upper()
            formatted_hex = ""
            
            # 包头部分（16字节）
            packet_info += "包头 (16字节):\n"
            header_hex = hex_data[:32]  # 16字节 = 32个十六进制字符
            for i in range(0, len(header_hex), 16):  # 每行8字节
                line = header_hex[i:i+16]
                formatted_line = ' '.join([line[j:j+2] for j in range(0, len(line), 2)])
                packet_info += f"  {formatted_line}\n"
            
            # 数据部分
            if len(hex_data) > 32:
                packet_info += f"\n数据部分 ({data_length}字节):\n"
                payload_hex = hex_data[32:]  # 跳过包头的32个字符
                
                # 每行显示16字节（32个十六进制字符）
                for i in range(0, len(payload_hex), 32):
                    line = payload_hex[i:i+32]
                    formatted_line = ' '.join([line[j:j+2] for j in range(0, len(line), 2)])
                    packet_info += f"  {formatted_line}\n"
            
            # 添加ASCII显示（如果数据是可打印字符）
            if payload:
                ascii_display = ""
                for byte in payload:
                    if 32 <= byte <= 126:  # 可打印ASCII字符
                        ascii_display += chr(byte)
                    else:
                        ascii_display += "."
                
                if ascii_display.strip():
                    packet_info += f"\nASCII预览:\n{ascii_display[:200]}{'...' if len(ascii_display) > 200 else ''}\n"
            
            packet_info += "\n" + "=" * 42
            return packet_info
            
        except Exception as e:
            return f"二进制数据包格式化失败: {str(e)}"


def main():
    """主函数"""
    root = tk.Tk()
    app = VDA5050TCPDemo(root)
    root.mainloop()


if __name__ == "__main__":
    main() 