"""GPU/Device manager with auto-detection and fallback."""

import os
import logging
from typing import Literal

logger = logging.getLogger(__name__)

DeviceType = Literal["cuda", "cpu", "auto"]


class GpuManager:
    """Manages device selection with GPU auto-detection."""
    
    def __init__(self):
        self._device: str = "cpu"
        self._detection_reason: str = ""
    
    def choose_device(self, env: str = "auto") -> str:
        """Choose compute device based on availability.
        
        Priority:
        1. RUNTIME_DEVICE environment variable
        2. env parameter
        3. Auto-detect CUDA
        4. Fallback to CPU
        
        Args:
            env: Device mode - "auto", "cuda", or "cpu"
            
        Returns:
            Selected device: "cuda" or "cpu"
        """
        # Check environment override
        env_override = os.getenv("RUNTIME_DEVICE", "").lower()
        if env_override in ["cuda", "cpu"]:
            self._device = env_override
            self._detection_reason = f"Environment variable RUNTIME_DEVICE={env_override}"
            logger.info(f"✓ Using device: {self._device} ({self._detection_reason})")
            return self._device
        
        # If explicit device requested (not auto), try to honor it
        if env and env.lower() in ["cuda", "cpu"]:
            requested = env.lower()
            if requested == "cuda":
                if self._is_cuda_available():
                    self._device = "cuda"
                    self._detection_reason = "Explicitly requested and available"
                else:
                    self._device = "cpu"
                    self._detection_reason = "CUDA requested but not available, falling back to CPU"
                    logger.warning(f"⚠ {self._detection_reason}")
            else:
                self._device = "cpu"
                self._detection_reason = "Explicitly requested"
            
            logger.info(f"✓ Using device: {self._device} ({self._detection_reason})")
            return self._device
        
        # Auto-detect mode
        if self._is_cuda_available():
            self._device = "cuda"
            self._detection_reason = "CUDA available via PyTorch"
        else:
            self._device = "cpu"
            self._detection_reason = "CUDA not available, using CPU"
        
        logger.info(f"✓ Using device: {self._device} ({self._detection_reason})")
        return self._device
    
    def _is_cuda_available(self) -> bool:
        """Check if CUDA is available.
        
        Returns:
            True if CUDA is available
        """
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
                logger.debug(f"CUDA detected: {device_count} device(s), primary: {device_name}")
                return True
        except ImportError:
            logger.debug("PyTorch not installed, CUDA unavailable")
        except Exception as e:
            logger.debug(f"Error checking CUDA availability: {e}")
        
        return False
    
    @property
    def device(self) -> str:
        """Get selected device."""
        return self._device
    
    @property
    def detection_reason(self) -> str:
        """Get reason for device selection."""
        return self._detection_reason


# Global instance
_gpu_manager_instance = None


def get_gpu_manager() -> GpuManager:
    """Get global GPU manager instance."""
    global _gpu_manager_instance
    if _gpu_manager_instance is None:
        _gpu_manager_instance = GpuManager()
    return _gpu_manager_instance
