"""Tests for GPU manager."""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
from src.engine.device import GpuManager


class TestGpuManager:
    """Test GPU/device selection."""
    
    def test_explicit_cpu(self):
        """Test explicit CPU selection."""
        manager = GpuManager()
        device = manager.choose_device("cpu")
        assert device == "cpu"
    
    def test_explicit_cuda_available(self):
        """Test explicit CUDA when available."""
        manager = GpuManager()
        
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "Tesla V100"
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            device = manager.choose_device("cuda")
            assert device == "cuda"
    
    def test_explicit_cuda_unavailable(self):
        """Test explicit CUDA when unavailable - should fallback to CPU."""
        manager = GpuManager()
        
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            device = manager.choose_device("cuda")
            assert device == "cpu"
    
    def test_auto_detect_cuda_available(self):
        """Test auto-detection with CUDA available."""
        manager = GpuManager()
        
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.device_count.return_value = 1
        mock_torch.cuda.get_device_name.return_value = "GeForce RTX 3080"
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            device = manager.choose_device("auto")
            assert device == "cuda"
    
    def test_auto_detect_cuda_unavailable(self):
        """Test auto-detection with CUDA unavailable."""
        manager = GpuManager()
        
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        
        with patch.dict('sys.modules', {'torch': mock_torch}):
            device = manager.choose_device("auto")
            assert device == "cpu"
    
    def test_auto_detect_no_torch(self):
        """Test auto-detection when PyTorch not installed."""
        manager = GpuManager()
        
        # Remove torch from sys.modules if it exists
        modules_backup = sys.modules.copy()
        if 'torch' in sys.modules:
            del sys.modules['torch']
        
        try:
            device = manager.choose_device("auto")
            assert device == "cpu"
        finally:
            # Restore modules
            sys.modules.update(modules_backup)
    
    def test_env_override_cuda(self):
        """Test environment variable override to CUDA."""
        manager = GpuManager()
        
        with patch.dict(os.environ, {'RUNTIME_DEVICE': 'cuda'}):
            device = manager.choose_device("cpu")  # Param ignored
            assert device == "cuda"
    
    def test_env_override_cpu(self):
        """Test environment variable override to CPU."""
        manager = GpuManager()
        
        with patch.dict(os.environ, {'RUNTIME_DEVICE': 'cpu'}):
            device = manager.choose_device("cuda")  # Param ignored
            assert device == "cpu"
