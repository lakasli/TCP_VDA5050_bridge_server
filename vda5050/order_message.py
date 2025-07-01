#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议订单消息类定义
包含订单消息的完整结构和功能
"""

from typing import Dict, Any, List, Optional
from .base_message import VDA5050BaseMessage, Action, NodePosition


class Node:
    """节点类"""
    
    def __init__(self,
                 node_id: str,
                 sequence_id: int,
                 released: bool,
                 actions: List[Action],
                 node_description: Optional[str] = None,
                 node_position: Optional[NodePosition] = None):
        self.node_id = node_id
        self.sequence_id = sequence_id
        self.released = released
        self.actions = actions
        self.node_description = node_description
        self.node_position = node_position
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "nodeId": self.node_id,
            "sequenceId": self.sequence_id,
            "released": self.released,
            "actions": [action.to_dict() for action in self.actions]
        }
        if self.node_description:
            result["nodeDescription"] = self.node_description
        if self.node_position:
            result["nodePosition"] = self.node_position.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        actions = [Action.from_dict(action_data) for action_data in data["actions"]]
        node_position = None
        if "nodePosition" in data:
            node_position = NodePosition.from_dict(data["nodePosition"])
        
        return cls(
            node_id=data["nodeId"],
            sequence_id=data["sequenceId"],
            released=data["released"],
            actions=actions,
            node_description=data.get("nodeDescription"),
            node_position=node_position
        )


class Edge:
    """边类"""
    
    def __init__(self,
                 edge_id: str,
                 sequence_id: int,
                 released: bool,
                 start_node_id: str,
                 end_node_id: str,
                 actions: List[Action],
                 edge_description: Optional[str] = None,
                 max_speed: Optional[float] = None,
                 max_height: Optional[float] = None,
                 min_height: Optional[float] = None,
                 orientation: Optional[float] = None,
                 orientation_type: Optional[str] = None,
                 direction: Optional[str] = None,
                 rotation_allowed: Optional[bool] = None,
                 max_rotation_speed: Optional[float] = None,
                 length: Optional[float] = None,
                 trajectory: Optional[Dict] = None):
        self.edge_id = edge_id
        self.sequence_id = sequence_id
        self.released = released
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.actions = actions
        self.edge_description = edge_description
        self.max_speed = max_speed
        self.max_height = max_height
        self.min_height = min_height
        self.orientation = orientation
        self.orientation_type = orientation_type
        self.direction = direction
        self.rotation_allowed = rotation_allowed
        self.max_rotation_speed = max_rotation_speed
        self.length = length
        self.trajectory = trajectory
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "edgeId": self.edge_id,
            "sequenceId": self.sequence_id,
            "released": self.released,
            "startNodeId": self.start_node_id,
            "endNodeId": self.end_node_id,
            "actions": [action.to_dict() for action in self.actions]
        }
        
        # 添加可选字段
        optional_fields = {
            "edgeDescription": self.edge_description,
            "maxSpeed": self.max_speed,
            "maxHeight": self.max_height,
            "minHeight": self.min_height,
            "orientation": self.orientation,
            "orientationType": self.orientation_type,
            "direction": self.direction,
            "rotationAllowed": self.rotation_allowed,
            "maxRotationSpeed": self.max_rotation_speed,
            "length": self.length,
            "trajectory": self.trajectory
        }
        
        for key, value in optional_fields.items():
            if value is not None:
                result[key] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        actions = [Action.from_dict(action_data) for action_data in data["actions"]]
        
        return cls(
            edge_id=data["edgeId"],
            sequence_id=data["sequenceId"],
            released=data["released"],
            start_node_id=data["startNodeId"],
            end_node_id=data["endNodeId"],
            actions=actions,
            edge_description=data.get("edgeDescription"),
            max_speed=data.get("maxSpeed"),
            max_height=data.get("maxHeight"),
            min_height=data.get("minHeight"),
            orientation=data.get("orientation"),
            orientation_type=data.get("orientationType"),
            direction=data.get("direction"),
            rotation_allowed=data.get("rotationAllowed"),
            max_rotation_speed=data.get("maxRotationSpeed"),
            length=data.get("length"),
            trajectory=data.get("trajectory")
        )


class OrderMessage(VDA5050BaseMessage):
    """VDA5050订单消息类"""
    
    def __init__(self,
                 header_id: int,
                 order_id: str,
                 order_update_id: int,
                 nodes: List[Node],
                 edges: List[Edge],
                 timestamp: Optional[str] = None,
                 version: str = "2.0.0",
                 manufacturer: str = "",
                 serial_number: str = "",
                 zone_set_id: Optional[str] = None):
        super().__init__(header_id, timestamp, version, manufacturer, serial_number)
        self.order_id = order_id
        self.order_update_id = order_update_id
        self.nodes = nodes
        self.edges = edges
        self.zone_set_id = zone_set_id
    
    @property
    def subtopic(self) -> str:
        return "/order"
    
    def get_message_dict(self) -> Dict[str, Any]:
        result = self.get_base_dict()
        result.update({
            "orderId": self.order_id,
            "orderUpdateId": self.order_update_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges]
        })
        
        if self.zone_set_id:
            result["zoneSetId"] = self.zone_set_id
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        nodes = [Node.from_dict(node_data) for node_data in data["nodes"]]
        edges = [Edge.from_dict(edge_data) for edge_data in data["edges"]]
        
        return cls(
            header_id=data["headerId"],
            order_id=data["orderId"],
            order_update_id=data["orderUpdateId"],
            nodes=nodes,
            edges=edges,
            timestamp=data.get("timestamp"),
            version=data.get("version", "2.0.0"),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", ""),
            zone_set_id=data.get("zoneSetId")
        )
    
    def validate(self) -> bool:
        """验证订单消息"""
        if not super().validate():
            return False
        
        # 检查必需字段
        if not self.order_id:
            return False
        if self.order_update_id < 0:
            return False
        
        # 验证节点和边的sequence_id连续性
        all_sequence_ids = []
        for node in self.nodes:
            all_sequence_ids.append(node.sequence_id)
        for edge in self.edges:
            all_sequence_ids.append(edge.sequence_id)
        
        if all_sequence_ids:
            all_sequence_ids.sort()
            for i, seq_id in enumerate(all_sequence_ids):
                if seq_id != i:
                    return False
        
        return True 