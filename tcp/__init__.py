"""
TCP协议处理模块
支持不同厂商的TCP协议实现
"""

from .manufacturer_a import ManufacturerATCPProtocol

__all__ = ["ManufacturerATCPProtocol"] 