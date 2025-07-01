#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议即时动作消息类定义
包含即时动作消息的完整结构和功能，以及预定义的即时动作类型
"""

from typing import Dict, Any, List, Optional
from enum import Enum
import uuid
from .base_message import VDA5050BaseMessage, Action, ActionParameter


class InstantActionType(Enum):
    """即时动作类型枚举"""
    # 订单和任务控制
    CANCEL_ORDER = "cancelOrder"
    START_PAUSE = "startPause"
    STOP_PAUSE = "stopPause"
    
    # 紧急停止和错误处理
    SOFT_EMC = "softEmc"
    CLEAR_ERRORS = "clearErrors"
    
    # 信息请求
    STATE_REQUEST = "stateRequest"
    FACTSHEET_REQUEST = "factsheetRequest"
    
    # 运动控制
    MOTION = "motion"
    TRANSLATE = "translate"
    TURN = "turn"
    ROTATE_AGV = "rotateAgv"
    STOP_AGV = "stopAgy"
    
    # 定位控制
    RELOC = "reloc"
    CANCEL_RELOC = "cancelReloc"
    CONFIRM_LOC = "confirmLoc"
    INIT_POSITION = "initPosition"
    
    # 货物操作
    PICK = "pick"
    DROP = "drop"
    ROTATE_LOAD = "rotatedoad"
    
    # 系统控制
    SWITCH_MAP = "switchMap"
    SWITCH_MODE = "switch_mode"
    START_CHARGING = "startCharging"
    STOP_CHARGING = "stopCharging"
    SAFE_CHECK = "safeCheck"


class InstantActionBuilder:
    """即时动作构建器，用于创建标准的即时动作"""
    
    @staticmethod
    def create_cancel_order(action_id: Optional[str] = None) -> Action:
        """创建取消订单动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.CANCEL_ORDER.value,
            blocking_type="HARD",
            action_description="取消订单"
        )
    
    @staticmethod
    def create_start_pause(action_id: Optional[str] = None) -> Action:
        """创建暂停任务动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.START_PAUSE.value,
            blocking_type="HARD",
            action_description="暂停任务"
        )
    
    @staticmethod
    def create_stop_pause(action_id: Optional[str] = None) -> Action:
        """创建继续任务动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.STOP_PAUSE.value,
            blocking_type="HARD",
            action_description="继续任务"
        )
    
    @staticmethod
    def create_soft_emc(action_id: Optional[str] = None,
                       status: bool = True) -> Action:
        """创建软件急停动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            status: 急停状态，true表示启动急停，false表示取消急停 (必需参数)
        """
        # 构建软急停参数列表
        soft_emc_parameters = [
            ActionParameter("status", status)
        ]
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.SOFT_EMC.value,
            blocking_type="HARD",
            action_description="软件急停动作",
            action_parameters=soft_emc_parameters
        )
    
    @staticmethod
    def create_clear_errors(action_id: Optional[str] = None) -> Action:
        """创建清除错误状态动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.CLEAR_ERRORS.value,
            blocking_type="SOFT",
            action_description="清除错误状态"
        )
    
    @staticmethod
    def create_state_request(action_id: Optional[str] = None) -> Action:
        """创建请求状态信息动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.STATE_REQUEST.value,
            blocking_type="NONE",
            action_description="请求状态信息"
        )
    
    @staticmethod
    def create_factsheet_request(action_id: Optional[str] = None) -> Action:
        """创建请求设备信息动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.FACTSHEET_REQUEST.value,
            blocking_type="NONE",
            action_description="请求设备信息"
        )
    
    @staticmethod
    def create_motion(action_id: Optional[str] = None,
                     vx: Optional[float] = None,
                     vy: Optional[float] = None,
                     w: Optional[float] = None,
                     steer: Optional[float] = None,
                     real_steer: Optional[float] = None,
                     duration: Optional[int] = None,
                     parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建开环运动动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            vx: 机器人在机器人坐标系中的x轴方向速度，单位m/s (可缺省)
            vy: 机器人在机器人坐标系中的y轴方向速度，单位m/s (可缺省)
            w: 机器人在机器人坐标系中的角速度，单位rad/s，顺时针为负，逆时针为正 (可缺省)
            steer: 舵角，单位rad，仅当单舵轮机器人时有效 (可缺省)
            real_steer: 目标舵角值(机器人坐标系)，单位rad，优先级大于steer (可缺省)
            duration: 持续时间，单位ms，0=一直保持当前开环速度运动 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建运动参数列表
        motion_parameters = []
        
        # 添加速度和角速度参数
        if vx is not None:
            motion_parameters.append(ActionParameter("vx", vx))
        if vy is not None:
            motion_parameters.append(ActionParameter("vy", vy))
        if w is not None:
            motion_parameters.append(ActionParameter("w", w))
            
        # 添加舵角参数
        if real_steer is not None:
            motion_parameters.append(ActionParameter("real_steer", real_steer))
        elif steer is not None:
            motion_parameters.append(ActionParameter("steer", steer))
            
        # 添加持续时间参数
        if duration is not None:
            motion_parameters.append(ActionParameter("duration", duration))
            
        # 如果提供了额外参数，合并到运动参数中
        if parameters:
            motion_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.MOTION.value,
            blocking_type="HARD",
            action_description="开环运动动作",
            action_parameters=motion_parameters
        )
    
    @staticmethod
    def create_translate(action_id: Optional[str] = None,
                        dist: float = 0.0,
                        vx: Optional[float] = None,
                        vy: Optional[float] = None,
                        mode: Optional[int] = None,
                        parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建平动动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            dist: 直线运动距离，绝对值，单位：m (必需参数)
            vx: 机器人坐标系下X方向运动的速度，正为向前，负为向后，单位：m/s (可缺省)
            vy: 机器人坐标系下Y方向运动的速度，正为向左，负为向右，单位：m/s (可缺省)
            mode: 0=里程模式(根据里程进行运动)，1=定位模式，若缺省则默认为里程模式 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建平动参数列表
        translate_parameters = []
        
        # 添加距离参数（必需）
        translate_parameters.append(ActionParameter("dist", dist))
        
        # 添加速度参数
        if vx is not None:
            translate_parameters.append(ActionParameter("vx", vx))
        if vy is not None:
            translate_parameters.append(ActionParameter("vy", vy))
            
        # 添加模式参数
        if mode is not None:
            translate_parameters.append(ActionParameter("mode", mode))
            
        # 如果提供了额外参数，合并到平动参数中
        if parameters:
            translate_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.TRANSLATE.value,
            blocking_type="HARD",
            action_description="平动动作",
            action_parameters=translate_parameters
        )
    
    @staticmethod
    def create_turn(action_id: Optional[str] = None,
                   angle: float = 0.0,
                   vw: float = 0.0,
                   mode: Optional[int] = None,
                   parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建转动动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            angle: 转动的角度（机器人坐标系），绝对值，单位rad，可以大于2π (必需参数)
            vw: 转动的角速度（机器人坐标系），正为逆时针转，负为顺时针转，单位rad/s (必需参数)
            mode: 0=里程模式（根据里程进行运动），1=定位模式，若缺省则默认为里程模式 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建转动参数列表
        turn_parameters = []
        
        # 添加角度参数（必需）
        turn_parameters.append(ActionParameter("angle", angle))
        
        # 添加角速度参数（必需）
        turn_parameters.append(ActionParameter("vw", vw))
        
        # 添加模式参数
        if mode is not None:
            turn_parameters.append(ActionParameter("mode", mode))
            
        # 如果提供了额外参数，合并到转动参数中
        if parameters:
            turn_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.TURN.value,
            blocking_type="HARD",
            action_description="转动动作",
            action_parameters=turn_parameters
        )
    
    @staticmethod
    def create_rotate_agv(action_id: Optional[str] = None,
                         angle: Optional[float] = None) -> Action:
        """创建车体旋转动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            angle: 旋转角度 (可缺省)
        """
        # 构建车体旋转参数列表
        rotate_agv_parameters = []
        
        # 添加角度参数
        if angle is not None:
            rotate_agv_parameters.append(ActionParameter("angle", angle))
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.ROTATE_AGV.value,
            blocking_type="HARD",
            action_description="车体旋转动作",
            action_parameters=rotate_agv_parameters
        )
    
    @staticmethod
    def create_stop_agv(action_id: Optional[str] = None) -> Action:
        """创建停止车体运动动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.STOP_AGV.value,
            blocking_type="HARD",
            action_description="停止车体运动"
        )
    
    @staticmethod
    def create_reloc(action_id: Optional[str] = None,
                    is_auto: Optional[bool] = None,
                    x: Optional[float] = None,
                    y: Optional[float] = None,
                    angle: Optional[float] = None,
                    length: Optional[float] = None,
                    home: Optional[bool] = None,
                    parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建重定位动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            is_auto: 是否为自动重定位，当存在该字段且值为true，忽略以下所有字段 (可缺省)
            x: 世界坐标系中的x坐标，单位m (可缺省)
            y: 世界坐标系中的y坐标，单位m (可缺省)
            angle: 世界坐标系中的角度，单位rad (可缺省)
            length: 重定位区域半径，单位m (可缺省)
            home: 在RobotHome重定位(若为true，前三个参数无效，并从Roboshop参数配置中的RobotHome1-5重定位，若RobotHome1-5未配置，则不做任何操作。若缺省则认为是false) (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建重定位参数列表
        reloc_parameters = []
        
        # 添加自动重定位参数
        if is_auto is not None:
            reloc_parameters.append(ActionParameter("isAuto", is_auto))
        
        # 添加位置参数
        if x is not None:
            reloc_parameters.append(ActionParameter("x", x))
        if y is not None:
            reloc_parameters.append(ActionParameter("y", y))
        if angle is not None:
            reloc_parameters.append(ActionParameter("angle", angle))
            
        # 添加重定位区域半径参数
        if length is not None:
            reloc_parameters.append(ActionParameter("length", length))
            
        # 添加Home重定位参数
        if home is not None:
            reloc_parameters.append(ActionParameter("home", home))
            
        # 如果提供了额外参数，合并到重定位参数中
        if parameters:
            reloc_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.RELOC.value,
            blocking_type="HARD",
            action_description="重定位动作",
            action_parameters=reloc_parameters
        )
    
    @staticmethod
    def create_cancel_reloc(action_id: Optional[str] = None) -> Action:
        """创建取消重定位动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.CANCEL_RELOC.value,
            blocking_type="HARD",
            action_description="取消重定位操作"
        )
    
    @staticmethod
    def create_confirm_loc(action_id: Optional[str] = None) -> Action:
        """创建确认定位动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.CONFIRM_LOC.value,
            blocking_type="SOFT",
            action_description="确认当前位置"
        )
    
    @staticmethod
    def create_init_position(action_id: Optional[str] = None,
                            x: Optional[float] = None,
                            y: Optional[float] = None,
                            theta: Optional[float] = None,
                            coordinate: Optional[str] = None,
                            reach_angle: Optional[float] = None,
                            reach_dist: Optional[float] = None,
                            use_odo: Optional[int] = None,
                            max_speed: Optional[float] = None,
                            max_rot: Optional[float] = None,
                            hold_dir: Optional[int] = None,
                            parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建初始化位置动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            x: 位置的x坐标 (可缺省)
            y: 位置的y坐标 (可缺省)
            theta: 角度 (可缺省)
            coordinate: 坐标系类型，robot表示机器人坐标系，world是世界坐标系 (可缺省)
            reach_angle: 到点角度精度 (可缺省)
            reach_dist: 到点距离精度 (可缺省)
            use_odo: 是否使用里程定位 (可缺省)
            max_speed: 最大速度 (可缺省)
            max_rot: 最大旋转速度 (可缺省)
            hold_dir: 全向车专用参数 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建初始化位置参数列表
        init_parameters = []
        
        # 添加位置坐标参数
        if x is not None:
            init_parameters.append(ActionParameter("x", x))
        if y is not None:
            init_parameters.append(ActionParameter("y", y))
        if theta is not None:
            init_parameters.append(ActionParameter("theta", theta))
            
        # 添加坐标系参数
        if coordinate is not None:
            init_parameters.append(ActionParameter("coordinate", coordinate))
            
        # 添加精度参数
        if reach_angle is not None:
            init_parameters.append(ActionParameter("reachAngle", reach_angle))
        if reach_dist is not None:
            init_parameters.append(ActionParameter("reachDist", reach_dist))
            
        # 添加定位模式参数
        if use_odo is not None:
            init_parameters.append(ActionParameter("useOdo", use_odo))
            
        # 添加速度参数
        if max_speed is not None:
            init_parameters.append(ActionParameter("maxSpeed", max_speed))
        if max_rot is not None:
            init_parameters.append(ActionParameter("maxRot", max_rot))
            
        # 添加全向车专用参数
        if hold_dir is not None:
            init_parameters.append(ActionParameter("hold_dir", hold_dir))
            
        # 如果提供了额外参数，合并到初始化位置参数中
        if parameters:
            init_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.INIT_POSITION.value,
            blocking_type="HARD",
            action_description="初始化位置动作",
            action_parameters=init_parameters
        )
    
    @staticmethod
    def create_pick(action_id: Optional[str] = None,
                   start_height: Optional[float] = None,
                   end_height: Optional[float] = None,
                   parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建拾取动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            start_height: 开始高度 (可缺省)
            end_height: 结束高度 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建拾取参数列表
        pick_parameters = []
        
        # 添加高度参数
        if start_height is not None:
            pick_parameters.append(ActionParameter("start_height", start_height))
        if end_height is not None:
            pick_parameters.append(ActionParameter("end_height", end_height))
            
        # 如果提供了额外参数，合并到拾取参数中
        if parameters:
            pick_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.PICK.value,
            blocking_type="HARD",
            action_description="拾取货物动作，支持叉车、差速小车",
            action_parameters=pick_parameters
        )
    
    @staticmethod
    def create_drop(action_id: Optional[str] = None,
                   start_height: Optional[float] = None,
                   end_height: Optional[float] = None,
                   parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建放置动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            start_height: 开始高度 (可缺省)
            end_height: 结束高度 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建放置参数列表
        drop_parameters = []
        
        # 添加高度参数
        if start_height is not None:
            drop_parameters.append(ActionParameter("start_height", start_height))
        if end_height is not None:
            drop_parameters.append(ActionParameter("end_height", end_height))
            
        # 如果提供了额外参数，合并到放置参数中
        if parameters:
            drop_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.DROP.value,
            blocking_type="HARD",
            action_description="放置货物动作，支持叉车、差速小车",
            action_parameters=drop_parameters
        )
    
    @staticmethod
    def create_rotate_load(action_id: Optional[str] = None,
                          angle: Optional[float] = None,
                          parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建旋转货物动作
        
        Args:
            action_id: 动作ID，若不指定则自动生成
            angle: 旋转角度 (可缺省)
            parameters: 额外的动作参数列表 (可缺省)
        """
        # 构建旋转货物参数列表
        rotate_parameters = []
        
        # 添加角度参数
        if angle is not None:
            rotate_parameters.append(ActionParameter("angle", angle))
            
        # 如果提供了额外参数，合并到旋转货物参数中
        if parameters:
            rotate_parameters.extend(parameters)
        
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.ROTATE_LOAD.value,
            blocking_type="HARD",
            action_description="旋转货物（货架）动作",
            action_parameters=rotate_parameters
        )
    
    @staticmethod
    def create_switch_map(action_id: Optional[str] = None,
                         parameters: Optional[List[ActionParameter]] = None) -> Action:
        """创建切换地图动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.SWITCH_MAP.value,
            blocking_type="HARD",
            action_description="切换地图",
            action_parameters=parameters or []
        )
    
    @staticmethod
    def create_switch_mode(action_id: Optional[str] = None) -> Action:
        """创建切换注册模式动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.SWITCH_MODE.value,
            blocking_type="SOFT",
            action_description="非标脚本功能"
        )
    
    @staticmethod
    def create_start_charging(action_id: Optional[str] = None) -> Action:
        """创建开始充电动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.START_CHARGING.value,
            blocking_type="SOFT",
            action_description="通过脚本实现充电"
        )
    
    @staticmethod
    def create_stop_charging(action_id: Optional[str] = None) -> Action:
        """创建停止充电动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.STOP_CHARGING.value,
            blocking_type="SOFT",
            action_description="通过脚本实现结束充电"
        )
    
    @staticmethod
    def create_safe_check(action_id: Optional[str] = None) -> Action:
        """创建安全检查动作"""
        return Action(
            action_id=action_id or str(uuid.uuid4()),
            action_type=InstantActionType.SAFE_CHECK.value,
            blocking_type="SOFT",
            action_description="通过脚本实现，需要脚本中实现检查逻辑"
        )


class InstantActionsMessage(VDA5050BaseMessage):
    """VDA5050即时动作消息类"""
    
    def __init__(self,
                 header_id: int,
                 actions: List[Action],
                 timestamp: Optional[str] = None,
                 version: str = "2.0.0",
                 manufacturer: str = "",
                 serial_number: str = ""):
        super().__init__(header_id, timestamp, version, manufacturer, serial_number)
        self.actions = actions
    
    @property
    def subtopic(self) -> str:
        return "/instantActions"
    
    def get_message_dict(self) -> Dict[str, Any]:
        result = self.get_base_dict()
        result.update({
            "actions": [action.to_dict() for action in self.actions]
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        actions = [Action.from_dict(action_data) for action_data in data["actions"]]
        
        return cls(
            header_id=data["headerId"],
            actions=actions,
            timestamp=data.get("timestamp"),
            version=data.get("version", "2.0.0"),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", "")
        )
    
    def validate(self) -> bool:
        """验证即时动作消息"""
        if not super().validate():
            return False
        
        # 验证所有动作的阻塞类型
        for action in self.actions:
            if action.blocking_type not in ["NONE", "SOFT", "HARD"]:
                return False
        
        return True
    
    def is_valid_action_type(self, action_type: str) -> bool:
        """验证动作类型是否为有效的即时动作类型"""
        valid_types = [action_type.value for action_type in InstantActionType]
        return action_type in valid_types
    
    def add_action(self, action: Action):
        """添加动作"""
        self.actions.append(action)
    
    def remove_action(self, action_id: str) -> bool:
        """根据动作ID移除动作"""
        for i, action in enumerate(self.actions):
            if action.action_id == action_id:
                del self.actions[i]
                return True
        return False
    
    def get_action_by_id(self, action_id: str) -> Optional[Action]:
        """根据动作ID获取动作"""
        for action in self.actions:
            if action.action_id == action_id:
                return action
        return None
    
    def get_actions_by_type(self, action_type: str) -> List[Action]:
        """根据动作类型获取所有匹配的动作"""
        return [action for action in self.actions if action.action_type == action_type]
    
    def has_action_type(self, action_type: str) -> bool:
        """检查是否包含指定类型的动作"""
        return any(action.action_type == action_type for action in self.actions)
    
    def clear_actions(self):
        """清除所有动作"""
        self.actions.clear()
    
    # 便利方法 - 添加预定义动作类型
    def add_cancel_order(self, action_id: Optional[str] = None):
        """添加取消订单动作"""
        self.add_action(InstantActionBuilder.create_cancel_order(action_id))
    
    def add_pause_task(self, action_id: Optional[str] = None):
        """添加暂停任务动作"""
        self.add_action(InstantActionBuilder.create_start_pause(action_id))
    
    def add_continue_task(self, action_id: Optional[str] = None):
        """添加继续任务动作"""
        self.add_action(InstantActionBuilder.create_stop_pause(action_id))
    
    def add_soft_emergency_stop(self, action_id: Optional[str] = None, 
                                status: bool = True):
        """添加软件急停动作"""
        self.add_action(InstantActionBuilder.create_soft_emc(action_id, status))
    
    def add_clear_errors(self, action_id: Optional[str] = None):
        """添加清除错误状态动作"""
        self.add_action(InstantActionBuilder.create_clear_errors(action_id))
    
    def add_state_request(self, action_id: Optional[str] = None):
        """添加请求状态信息动作"""
        self.add_action(InstantActionBuilder.create_state_request(action_id))
    
    def add_factsheet_request(self, action_id: Optional[str] = None):
        """添加请求设备信息动作"""
        self.add_action(InstantActionBuilder.create_factsheet_request(action_id))
    
    def add_stop_agv(self, action_id: Optional[str] = None):
        """添加停止AGV运动动作"""
        self.add_action(InstantActionBuilder.create_stop_agv(action_id))
    
    def add_rotate_agv(self, action_id: Optional[str] = None,
                      angle: Optional[float] = None):
        """添加车体旋转动作"""
        self.add_action(InstantActionBuilder.create_rotate_agv(action_id, angle))
    
    def add_pick_action(self, action_id: Optional[str] = None,
                       start_height: Optional[float] = None,
                       end_height: Optional[float] = None,
                       parameters: Optional[List[ActionParameter]] = None):
        """添加拾取动作"""
        self.add_action(InstantActionBuilder.create_pick(action_id, start_height, end_height, parameters))
    
    def add_drop_action(self, action_id: Optional[str] = None,
                       start_height: Optional[float] = None,
                       end_height: Optional[float] = None,
                       parameters: Optional[List[ActionParameter]] = None):
        """添加放置动作"""
        self.add_action(InstantActionBuilder.create_drop(action_id, start_height, end_height, parameters))
    
    def add_start_charging(self, action_id: Optional[str] = None):
        """添加开始充电动作"""
        self.add_action(InstantActionBuilder.create_start_charging(action_id))
    
    def add_stop_charging(self, action_id: Optional[str] = None):
        """添加停止充电动作"""
        self.add_action(InstantActionBuilder.create_stop_charging(action_id)) 