#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VDA5050协议连接消息类定义
包含AGV连接状态信息
"""

from typing import Dict, Any, Optional
from .base_message import VDA5050BaseMessage


class ConnectionMessage(VDA5050BaseMessage):
    """VDA5050连接消息类"""
    
    def __init__(self,
                 header_id: int,
                 connection_state: str,
                 timestamp: Optional[str] = None,
                 version: str = "2.0.0",
                 manufacturer: str = "",
                 serial_number: str = ""):
        super().__init__(header_id, timestamp, version, manufacturer, serial_number)
        self.connection_state = connection_state  # ONLINE, OFFLINE, CONNECTIONBROKEN
    
    @property
    def subtopic(self) -> str:
        return "/connection"
    
    def get_message_dict(self) -> Dict[str, Any]:
        result = self.get_base_dict()
        result.update({
            "connectionState": self.connection_state
        })
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            header_id=data["headerId"],
            connection_state=data["connectionState"],
            timestamp=data.get("timestamp"),
            version=data.get("version", "2.0.0"),
            manufacturer=data.get("manufacturer", ""),
            serial_number=data.get("serialNumber", "")
        )
    
    def validate(self) -> bool:
        """验证连接消息"""
        if not super().validate():
            return False
        
        # 验证连接状态
        if self.connection_state not in ["ONLINE", "OFFLINE", "CONNECTIONBROKEN"]:
            return False
        
        return True
    
    def is_online(self) -> bool:
        """检查是否在线"""
        return self.connection_state == "ONLINE"
    
    def is_offline(self) -> bool:
        """检查是否离线"""
        return self.connection_state == "OFFLINE"
    
    def is_connection_broken(self) -> bool:
        """检查连接是否中断"""
        return self.connection_state == "CONNECTIONBROKEN" 