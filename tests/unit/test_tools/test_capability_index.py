"""
Unit tests for capability_index.py

Tests capability enumeration, tier classification, and capability matrix building.
"""

import pytest
from pathlib import Path


class TestCapabilityIndex:
    """Test capability index generation."""

    def test_capability_index_imports(self):
        """Test that capability_index module can be imported."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'tools'))
        import capability_index
        assert hasattr(capability_index, 'build_capability_matrix')
        assert hasattr(capability_index, 'extract_agent_capabilities')

    def test_classify_agent_tier_function_exists(self):
        """Test that classify_agent_tier function exists."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'tools'))
        import capability_index
        assert hasattr(capability_index, 'classify_agent_tier')
