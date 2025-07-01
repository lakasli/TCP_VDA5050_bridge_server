#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议状态消息类定义
包含AGV状态消息的完整结构和功能
"""

from typing import Dict, Any, List, Optional
from .base_message import VDA5050BaseMessage, NodePosition


class MapInfo:
    """地图信息类"""
    
    def __init__(self,
                 map_id: str,
                 map_version: str,
                 map_status: str,
                 map_description: Optional[str] = None):
        self.map_id = map_id
        self.map_version = map_version
        self.map_status = map_status  # ENABLED, DISABLED
        self.map_description = map_description
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "mapId": self.map_id,
            "mapVersion": self.map_version,
            "mapStatus": self.map_status
        }
        if self.map_description:
            result["mapDescription"] = self.map_description
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            map_id=data["mapId"],
            map_version=data["mapVersion"],
            map_status=data["mapStatus"],
            map_description=data.get("mapDescription")
        )


class NodeState:
    """节点状态类"""
    
    def __init__(self,
                 node_id: str,
                 sequence_id: int,
                 released: bool,
                 node_description: Optional[str] = None,
                 node_position: Optional[NodePosition] = None):
        self.node_id = node_id
        self.sequence_id = sequence_id
        self.released = released
        self.node_description = node_description
        self.node_position = node_position
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "nodeId": self.node_id,
            "sequenceId": self.sequence_id,
            "released": self.released
        }
        if self.node_description:
            result["nodeDescription"] = self.node_description
        if self.node_position:
            result["nodePosition"] = self.node_position.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        node_position = None
        if "nodePosition" in data:
            node_position = NodePosition.from_dict(data["nodePosition"])
        
        return cls(
            node_id=data["nodeId"],
            sequence_id=data["sequenceId"],
            released=data["released"],
            node_description=data.get("nodeDescription"),
            node_position=node_position
        )


class EdgeState:
    """边状态类"""
    
    def __init__(self,
                 edge_id: str,
                 sequence_id: int,
                 released: bool,
                 edge_description: Optional[str] = None,
                 trajectory: Optional[Dict] = None):
        self.edge_id = edge_id
        self.sequence_id = sequence_id
        self.released = released
        self.edge_description = edge_description
        self.trajectory = trajectory
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "edgeId": self.edge_id,
            "sequenceId": self.sequence_id,
            "released": self.released
        }
        if self.edge_description:
            result["edgeDescription"] = self.edge_description
        if self.trajectory:
            result["trajectory"] = self.trajectory
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            edge_id=data["edgeId"],
            sequence_id=data["sequenceId"],
            released=data["released"],
            edge_description=data.get("edgeDescription"),
            trajectory=data.get("trajectory")
        )


class ActionState:
    """动作状态类"""
    
    def __init__(self,
                 action_id: str,
                 action_type: str,
                 action_status: str,
                 action_description: Optional[str] = None,
                 result_description: Optional[str] = None):
        self.action_id = action_id
        self.action_type = action_type
        self.action_status = action_status  # WAITING, INITIALIZING, RUNNING, FINISHED, FAILED
        self.action_description = action_description
        self.result_description = result_description
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "actionId": self.action_id,
            "actionType": self.action_type,
            "actionStatus": self.action_status
        }
        if self.action_description:
            result["actionDescription"] = self.action_description
        if self.result_description:
            result["resultDescription"] = self.result_description
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            action_id=data["actionId"],
            action_type=data["actionType"],
            action_status=data["actionStatus"],
            action_description=data.get("actionDescription"),
            result_description=data.get("resultDescription")
        )


class BatteryState:
    """电池状态类"""
    
    def __init__(self,
                 battery_charge: float,
                 battery_voltage: Optional[float] = None,
                 battery_health: Optional[int] = None,
                 charging: Optional[bool] = None,
                 reach: Optional[int] = None):
        self.battery_charge = battery_charge  # 0.0 to 100.0
        self.battery_voltage = battery_voltage
        self.battery_health = battery_health  # 0 to 100
        self.charging = charging
        self.reach = reach  # 剩余可达距离（米）
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "batteryCharge": self.battery_charge
        }
        if self.battery_voltage is not None:
            result["batteryVoltage"] = self.battery_voltage
        if self.battery_health is not None:
            result["batteryHealth"] = self.battery_health
        if self.charging is not None:
            result["charging"] = self.charging
        if self.reach is not None:
            result["reach"] = self.reach
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            battery_charge=data["batteryCharge"],
            battery_voltage=data.get("batteryVoltage"),
            battery_health=data.get("batteryHealth"),
            charging=data.get("charging"),
            reach=data.get("reach")
        )


class Error:
    """错误类"""
    
    def __init__(self,
                 error_type: str,
                 error_level: str,
                 error_references: Optional[List[Dict]] = None,
                 error_description: Optional[str] = None):
        self.error_type = error_type
        self.error_level = error_level  # WARNING, FATAL
        self.error_references = error_references or []
        self.error_description = error_description
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "errorType": self.error_type,
            "errorLevel": self.error_level
        }
        if self.error_references:
            result["errorReferences"] = self.error_references
        if self.error_description:
            result["errorDescription"] = self.error_description
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            error_type=data["errorType"],
            error_level=data["errorLevel"],
            error_references=data.get("errorReferences", []),
            error_description=data.get("errorDescription")
        )


class SafetyState:
    """安全状态类"""
    
    def __init__(self,
                 e_stop: str,
                 field_violation: bool,
                 protective_field: Optional[str] = None):
        self.e_stop = e_stop  # AUTOACK, MANUAL, REMOTE, NONE
        self.field_violation = field_violation
        self.protective_field = protective_field
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "eStop": self.e_stop,
            "fieldViolation": self.field_violation
        }
        if self.protective_field:
            result["protectiveField"] = self.protective_field
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            e_stop=data["eStop"],
            field_violation=data["fieldViolation"],
            protective_field=data.get("protectiveField")
        )


class StateMessage(VDA5050BaseMessage):
    """VDA5050状态消息类"""
    
    def __init__(self,
                 header_id: int,
                 order_id: str,
                 order_update_id: int,
                 last_node_id: str,
                 last_node_sequence_id: int,
                 node_states: List[NodeState],
                 edge_states: List[EdgeState],
                 driving: bool,
                 action_states: List[ActionState],
                 battery_state: BatteryState,
                 operating_mode: str,
                 errors: List[Error],
                 safety_state: SafetyState,
                 timestamp: Optional[str] = None,
                 version: str = "2.0.0",
                 manufacturer: str = "",
                 serial_number: str = "",
                 maps: Optional[List[MapInfo]] = None,
                 zone_set_id: Optional[str] = None,
                 paused: Optional[bool] = None,
                 new_base_request: Optional[bool] = None,
                 distance_since_last_node: Optional[float] = None,
                 agv_position: Optional[NodePosition] = None,
                 velocity: Optional[Dict] = None,
                 loads: Optional[List[Dict]] = None,
                 information: Optional[List[Dict]] = None):
        super().__init__(header_id, timestamp, version, manufacturer, serial_number)
        self.order_id = order_id
        self.order_update_id = order_update_id
        self.last_node_id = last_node_id
        self.last_node_sequence_id = last_node_sequence_id
        self.node_states = node_states
        self.edge_states = edge_states
        self.driving = driving
        self.action_states = action_states
        self.battery_state = battery_state
        self.operating_mode = operating_mode  # AUTOMATIC, SEMIAUTOMATIC, MANUAL, SERVICE, TEACHIN
        self.errors = errors
        self.safety_state = safety_state
        self.maps = maps or []
        self.zone_set_id = zone_set_id
        self.paused = paused
        self.new_base_request = new_base_request
        self.distance_since_last_node = distance_since_last_node
        self.agv_position = agv_position
        self.velocity = velocity
        self.loads = loads or []
        self.information = information or []
    
    @property
    def subtopic(self) -> str:
        return "/state"
    
    def get_message_dict(self) -> Dict[str, Any]:
        result = self.get_base_dict()
        result.update({
            "orderId": self.order_id,
            "orderUpdateId": self.order_update_id,
            "lastNodeId": self.last_node_id,
            "lastNodeSequenceId": self.last_node_sequence_id,
            "nodeStates": [node_state.to_dict() for node_state in self.node_states],
            "edgeStates": [edge_state.to_dict() for edge_state in self.edge_states],
            "driving": self.driving,
            "actionStates": [action_state.to_dict() for action_state in self.action_states],
            "batteryState": self.battery_state.to_dict(),
            "operatingMode": self.operating_mode,
            "errors": [error.to_dict() for error in self.errors],
            "safetyState": self.safety_state.to_dict()
        })
        
        # 添加可选字段
        if self.maps:
            result["maps"] = [map_info.to_dict() for map_info in self.maps]
        if self.zone_set_id:
            result["zoneSetId"] = self.zone_set_id
        if self.paused is not None:
            result["paused"] = self.paused
        if self.new_base_request is not None:
            result["newBaseRequest"] = self.new_base_request
        if self.distance_since_last_node is not None:
            result["distanceSinceLastNode"] = self.distance_since_last_node
        if self.agv_position:
            result["agvPosition"] = self.agv_position.to_dict()
        if self.velocity:
            result["velocity"] = self.velocity
        if self.loads:
            result["loads"] = self.loads
        if self.information:
            result["information"] = self.information
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        node_states = [NodeState.from_dict(ns) for ns in data["nodeStates"]]
        edge_states = [EdgeState.from_dict(es) for es in data["edgeStates"]]
        action_states = [ActionState.from_dict(as_data) for as_data in data["actionStates"]]
        battery_state = BatteryState.from_dict(data["batteryState"])
        errors = [Error.from_dict(err) for err in data["errors"]]
        safety_state = SafetyState.from_dict(data["safetyState"])
        
        maps = []
        if "maps" in data:
            maps = [MapInfo.from_dict(map_data) for map_data in data["maps"]]
        
        agv_position = None
        if "agvPosition" in data:
            agv_position = NodePosition.from_dict(data["agvPosition"])
        
        return cls(
            header_id=data["headerId"],
            order_id=data["orderId"],
            order_update_id=data["orderUpdateId"],
            last_node_id=data["lastNodeId"],
            last_node_sequence_id=data["lastNodeSequenceId"],
            node_states=node_states,
            edge_states=edge_states,
            driving=data["driving"],
            action_states=action_states,
            battery_state=battery_state,
            operating_mode=data["operatingMode"],
            errors=errors,
            safety_state=safety_state,
            timestamp=data.get("timestamp"),
            version=data.get("version", "2.0.0"),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", ""),
            maps=maps,
            zone_set_id=data.get("zoneSetId"),
            paused=data.get("paused"),
            new_base_request=data.get("newBaseRequest"),
            distance_since_last_node=data.get("distanceSinceLastNode"),
            agv_position=agv_position,
            velocity=data.get("velocity"),
            loads=data.get("loads", []),
            information=data.get("information", [])
        )
    
    def validate(self) -> bool:
        """验证状态消息"""
        if not super().validate():
            return False
        
        # 检查必需字段
        if self.order_update_id < 0:
            return False
        if self.last_node_sequence_id < 0:
            return False
        if self.operating_mode not in ["AUTOMATIC", "SEMIAUTOMATIC", "MANUAL", "SERVICE", "TEACHIN"]:
            return False
        
        return True 