"""Device management module."""

from .gpu_manager import GpuManager, get_gpu_manager, DeviceType

__all__ = ["GpuManager", "get_gpu_manager", "DeviceType"]
