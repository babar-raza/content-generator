"""Tests for agent discovery, registration, and contracts.

Tests the AgentScanner, EnhancedAgentRegistry, and DependencyResolver
to ensure all agents are properly discovered and registered.

NOTE: These tests were written for a different API than the current implementation.
Many tests have been commented out and need to be rewritten to match the actual
AgentScanner, EnhancedAgentRegistry, and DependencyResolver APIs.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.agent_scanner import AgentScanner, AgentMetadata
from src.orchestration.enhanced_registry import EnhancedAgentRegistry, get_registry
from src.orchestration.dependency_resolver import DependencyResolver


class TestAgentScanner:
    """Test agent discovery and scanning functionality."""
    
    def test_scanner_initialization(self):
        """Test scanner initializes with default path."""
        # AgentScanner requires 3 files for initialization
        agents_file = Path("src/agents/agents.py")
        contracts_file = Path("src/core/contracts.py")
        config_file = Path("config/agents.yaml")

        scanner = AgentScanner(agents_file, contracts_file, config_file)
        assert scanner.agents_file == agents_file
        assert scanner.contracts_file == contracts_file
        assert scanner.config_file == config_file
    
    def test_scanner_custom_path(self):
        """Test scanner with custom path."""
        custom_path = Path("custom/agents")
        scanner = AgentScanner(custom_path)
        assert scanner.base_path == custom_path
    
    def test_discover_agents(self):
        """Test discovering all agents in src/agents directory."""
        scanner = AgentScanner()
        agents = scanner.discover()
        
        # Should discover many agents (at least 30+)
        assert len(agents) >= 30
        print(f"\nDiscovered {len(agents)} agents")
        
        # Verify we have agent classes or None values
        assert all(agent is None or hasattr(agent, '__name__') for agent in agents)
    
    def test_discover_caching(self):
        """Test that discovery caching works."""
        scanner = AgentScanner()
        
        # First discovery
        agents1 = scanner.discover()
        assert scanner._cache_valid == True
        
        # Second discovery should use cache
        agents2 = scanner.discover()
        assert agents1 == agents2
        
        # Force rescan
        agents3 = scanner.discover(force_rescan=True)
        assert len(agents3) == len(agents1)
    
    def test_get_metadata(self):
        """Test getting metadata for specific agents."""
        scanner = AgentScanner()
        scanner.discover()
        
        # Test known agents
        outline_meta = scanner.get_metadata("OutlineCreationAgent")
        assert outline_meta is not None
        assert outline_meta.name == "OutlineCreationAgent"
        assert outline_meta.category == "content"
        
        # Test non-existent agent
        fake_meta = scanner.get_metadata("NonExistentAgent")
        assert fake_meta is None
    
    def test_get_all_metadata(self):
        """Test getting all agent metadata."""
        scanner = AgentScanner()
        scanner.discover()
        
        all_metadata = scanner.get_all_metadata()
        assert isinstance(all_metadata, dict)
        assert len(all_metadata) >= 30
        
        # Verify metadata structure
        for name, metadata in all_metadata.items():
            assert isinstance(metadata, AgentMetadata)
            assert metadata.name == name
            assert isinstance(metadata.category, str)
            assert isinstance(metadata.capabilities, list)
    
    def test_get_agents_by_category(self):
        """Test getting agents by category."""
        scanner = AgentScanner()
        scanner.discover()
        
        # Test content category
        content_agents = scanner.get_agents_by_category("content")
        assert len(content_agents) >= 4  # At least a few content agents
        assert all(agent.category == "content" for agent in content_agents)
        
        # Test code category
        code_agents = scanner.get_agents_by_category("code")
        assert len(code_agents) >= 4
        assert all(agent.category == "code" for agent in code_agents)
        
        # Test non-existent category
        empty_agents = scanner.get_agents_by_category("nonexistent")
        assert empty_agents == []
    
    def test_category_extraction(self):
        """Test category extraction from file path."""
        scanner = AgentScanner()
        scanner.discover()
        
        metadata = scanner.get_all_metadata()
        
        # Verify categories
        categories = set(m.category for m in metadata.values())
        expected_categories = {"content", "code", "seo", "ingestion", "publishing", "research"}
        assert expected_categories.issubset(categories)
    
    def test_capabilities_extraction(self):
        """Test capabilities extraction from agents."""
        scanner = AgentScanner()
        scanner.discover()
        
        # Get OutlineCreationAgent
        outline_meta = scanner.get_metadata("OutlineCreationAgent")
        if outline_meta:
            assert "create_outline" in outline_meta.capabilities
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        scanner = AgentScanner()
        scanner.discover()
        assert scanner._cache_valid == True
        
        scanner.invalidate_cache()
        assert scanner._cache_valid == False
    
    def test_trigger_reload(self):
        """Test triggering agent reload."""
        scanner = AgentScanner()
        initial_agents = scanner.discover()
        
        reloaded_agents = scanner.trigger_reload()
        assert len(reloaded_agents) == len(initial_agents)


class TestEnhancedAgentRegistry:
    """Test enhanced agent registry functionality."""
    
    def test_registry_initialization(self):
        """Test registry initializes correctly."""
        registry = EnhancedAgentRegistry()
        
        assert registry.agents_dir == Path("src/agents")
        assert isinstance(registry.scanner, AgentScanner)
        assert isinstance(registry.dependency_resolver, DependencyResolver)
        
        # Should auto-discover agents on init
        assert len(registry._agent_classes) >= 30
    
    def test_discover_agents(self):
        """Test agent discovery through registry."""
        registry = EnhancedAgentRegistry()
        count = registry.discover_agents()
        
        assert count >= 30
        assert len(registry._agent_classes) == count
        assert len(registry._agent_metadata) == count
    
    def test_get_agent_without_instantiation(self):
        """Test getting agent without config/event_bus returns None."""
        registry = EnhancedAgentRegistry()
        
        # Without config/event_bus, should return None
        agent = registry.get_agent("OutlineCreationAgent")
        assert agent is None
    
    def test_get_agent_with_config(self):
        """Test getting agent with config and event_bus."""
        registry = EnhancedAgentRegistry()
        
        # Create mock config and event_bus
        mock_config = MagicMock()
        mock_event_bus = MagicMock()
        
        # Patch the agent class to avoid actual instantiation issues
        with patch.object(registry, '_agent_classes') as mock_classes:
            mock_agent_class = MagicMock()
            mock_agent_instance = MagicMock()
            mock_agent_class.return_value = mock_agent_instance
            mock_classes.get.return_value = mock_agent_class
            
            with patch.object(registry, '_agent_metadata') as mock_metadata:
                mock_meta = MagicMock()
                mock_meta.dependencies = []
                mock_metadata.get.return_value = mock_meta
                
                agent = registry.get_agent("TestAgent", config=mock_config, event_bus=mock_event_bus)
                assert agent == mock_agent_instance
    
    def test_get_dependencies(self):
        """Test getting agent dependencies."""
        registry = EnhancedAgentRegistry()
        
        # Get dependencies for a known agent
        deps = registry.get_dependencies("OutlineCreationAgent")
        assert isinstance(deps, list)
        
        # Non-existent agent
        deps = registry.get_dependencies("NonExistentAgent")
        assert deps == []
    
    def test_agents_by_category(self):
        """Test getting agents by category."""
        registry = EnhancedAgentRegistry()
        
        # Get content agents
        content_agents = registry.agents_by_category("content")
        assert len(content_agents) >= 4
        assert all(hasattr(agent, 'category') and agent.category == "content" for agent in content_agents)
        
        # Get code agents
        code_agents = registry.agents_by_category("code")
        assert len(code_agents) >= 4
        
        # Non-existent category
        empty = registry.agents_by_category("nonexistent")
        assert empty == []
    
    def test_get_all_agents(self):
        """Test getting all registered agents."""
        registry = EnhancedAgentRegistry()
        
        all_agents = registry.get_all_agents()
        assert isinstance(all_agents, dict)
        assert len(all_agents) >= 30
    
    def test_get_agent_metadata(self):
        """Test getting metadata for specific agent."""
        registry = EnhancedAgentRegistry()
        
        metadata = registry.get_agent_metadata("OutlineCreationAgent")
        assert metadata is not None
        assert metadata.name == "OutlineCreationAgent"
        assert metadata.category == "content"
    
    def test_get_all_categories(self):
        """Test getting all categories."""
        registry = EnhancedAgentRegistry()
        
        categories = registry.get_all_categories()
        assert isinstance(categories, list)
        assert "content" in categories
        assert "code" in categories
        assert "seo" in categories
    
    def test_validate_dependencies(self):
        """Test dependency validation."""
        registry = EnhancedAgentRegistry()
        
        issues = registry.validate_dependencies()
        # Should return dict of issues (possibly empty)
        assert isinstance(issues, dict)
    
    def test_detect_cycles(self):
        """Test cycle detection."""
        registry = EnhancedAgentRegistry()
        
        cycles = registry.detect_cycles()
        # Should be None if no cycles
        assert cycles is None or isinstance(cycles, list)
    
    def test_get_registry_stats(self):
        """Test getting registry statistics."""
        registry = EnhancedAgentRegistry()
        
        stats = registry.get_registry_stats()
        assert "total_agents" in stats
        assert "categories" in stats
        assert "instantiated_agents" in stats
        assert "agents_by_category" in stats
        
        assert stats["total_agents"] >= 30
        assert stats["categories"] >= 5
    
    def test_clear_instances(self):
        """Test clearing agent instances."""
        registry = EnhancedAgentRegistry()
        registry.clear_instances()
        
        assert len(registry._agent_instances) == 0
    
    def test_rescan(self):
        """Test forcing a rescan."""
        registry = EnhancedAgentRegistry()
        initial_count = len(registry._agent_classes)
        
        count = registry.rescan()
        assert count == initial_count


class TestGetRegistry:
    """Test singleton registry access."""
    
    def test_get_registry_singleton(self):
        """Test that get_registry returns singleton."""
        registry1 = get_registry()
        registry2 = get_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, EnhancedAgentRegistry)
    
    def test_get_registry_initializes_once(self):
        """Test that registry is only initialized once."""
        # Reset the global instance
        import src.orchestration.enhanced_registry as reg_module
        original_instance = reg_module._registry_instance
        reg_module._registry_instance = None
        
        try:
            registry1 = get_registry()
            count1 = len(registry1._agent_classes)
            
            registry2 = get_registry()
            count2 = len(registry2._agent_classes)
            
            assert count1 == count2
            assert registry1 is registry2
        finally:
            # Restore original instance
            reg_module._registry_instance = original_instance


class TestDependencyResolver:
    """Test dependency resolution functionality."""
    
    def test_resolver_initialization(self):
        """Test resolver initializes correctly."""
        resolver = DependencyResolver()
        
        assert resolver._dependency_graph == {}
        assert resolver._reverse_graph == {}
    
    def test_add_dependency(self):
        """Test adding a single dependency."""
        resolver = DependencyResolver()
        resolver.add_dependency("AgentA", "AgentB")
        
        deps = resolver.get_dependencies("AgentA")
        assert "AgentB" in deps
    
    def test_add_agent_with_dependencies(self):
        """Test adding agent with multiple dependencies."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB", "AgentC"])
        
        deps = resolver.get_dependencies("AgentA")
        assert "AgentB" in deps
        assert "AgentC" in deps
    
    def test_get_all_dependencies(self):
        """Test getting all transitive dependencies."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB"])
        resolver.add_agent("AgentB", ["AgentC"])
        resolver.add_agent("AgentC", [])
        
        all_deps = resolver.get_all_dependencies("AgentA")
        assert "AgentB" in all_deps
        assert "AgentC" in all_deps
        assert "AgentA" not in all_deps
    
    def test_get_dependents(self):
        """Test getting agents that depend on given agent."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB"])
        resolver.add_agent("AgentC", ["AgentB"])
        
        dependents = resolver.get_dependents("AgentB")
        assert "AgentA" in dependents
        assert "AgentC" in dependents
    
    def test_resolve_order_simple(self):
        """Test resolving execution order."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", [])
        resolver.add_agent("AgentB", ["AgentA"])
        resolver.add_agent("AgentC", ["AgentB"])
        
        order = resolver.resolve_order(["AgentA", "AgentB", "AgentC"])
        
        # AgentA should come before AgentB, AgentB before AgentC
        assert order.index("AgentA") < order.index("AgentB")
        assert order.index("AgentB") < order.index("AgentC")
    
    def test_resolve_order_complex(self):
        """Test resolving complex dependency order."""
        resolver = DependencyResolver()
        resolver.add_agent("A", [])
        resolver.add_agent("B", ["A"])
        resolver.add_agent("C", ["A"])
        resolver.add_agent("D", ["B", "C"])
        
        order = resolver.resolve_order(["A", "B", "C", "D"])
        
        # A must come first
        assert order.index("A") == 0
        # B and C must come before D
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")
    
    def test_detect_cycles_no_cycle(self):
        """Test cycle detection with no cycles."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", [])
        resolver.add_agent("AgentB", ["AgentA"])
        
        cycle = resolver.detect_cycles()
        assert cycle is None
    
    def test_detect_cycles_with_cycle(self):
        """Test cycle detection with actual cycle."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB"])
        resolver.add_agent("AgentB", ["AgentA"])
        
        cycle = resolver.detect_cycles()
        assert cycle is not None
        assert len(cycle) > 0
    
    def test_validate_dependencies_all_satisfied(self):
        """Test validation when all dependencies satisfied."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB"])
        resolver.add_agent("AgentB", [])
        
        available = {"AgentA", "AgentB"}
        issues = resolver.validate_dependencies(available)
        
        assert len(issues) == 0
    
    def test_validate_dependencies_missing(self):
        """Test validation with missing dependencies."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB", "AgentC"])
        
        available = {"AgentA"}
        issues = resolver.validate_dependencies(available)
        
        assert "AgentA" in issues
        assert "AgentB" in issues["AgentA"]
        assert "AgentC" in issues["AgentA"]
    
    def test_clear(self):
        """Test clearing all dependencies."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB"])
        
        resolver.clear()
        
        assert len(resolver._dependency_graph) == 0
        assert len(resolver._reverse_graph) == 0
    
    def test_to_dict(self):
        """Test exporting dependency graph."""
        resolver = DependencyResolver()
        resolver.add_agent("AgentA", ["AgentB"])
        resolver.add_agent("AgentB", [])
        
        graph_dict = resolver.to_dict()
        
        assert isinstance(graph_dict, dict)
        assert "AgentA" in graph_dict
        assert "AgentB" in graph_dict["AgentA"]


class TestIntegration:
    """Integration tests for the complete discovery and registration flow."""
    
    def test_full_discovery_and_registration_flow(self):
        """Test the complete flow from discovery to registration."""
        # Create scanner and discover agents
        scanner = AgentScanner()
        agents = scanner.discover()
        
        assert len(agents) >= 30
        
        # Get metadata
        all_metadata = scanner.get_all_metadata()
        assert len(all_metadata) >= 30
        
        # Create registry and verify it has the same agents
        registry = EnhancedAgentRegistry()
        assert len(registry._agent_classes) == len(agents)
        
        # Test category grouping
        categories = registry.get_all_categories()
        assert len(categories) >= 5
        
        for category in categories:
            agents_in_cat = registry.agents_by_category(category)
            assert len(agents_in_cat) > 0
    
    def test_specific_known_agents(self):
        """Test that known agents are discovered correctly."""
        registry = EnhancedAgentRegistry()
        
        known_agents = [
            "OutlineCreationAgent",
            "CodeGenerationAgent",
            "SEOMetadataAgent",
            "FileWriterAgent",
            "TopicIdentificationAgent"
        ]
        
        for agent_name in known_agents:
            metadata = registry.get_agent_metadata(agent_name)
            assert metadata is not None, f"{agent_name} not found"
            assert metadata.name == agent_name
    
    def test_category_counts(self):
        """Test that each category has expected number of agents."""
        registry = EnhancedAgentRegistry()
        
        # Expected minimums for each category
        expected_minimums = {
            "content": 4,
            "code": 4,
            "seo": 3,
            "ingestion": 4,
            "publishing": 4
        }
        
        for category, min_count in expected_minimums.items():
            agents = registry.agents_by_category(category)
            assert len(agents) >= min_count, f"Category {category} should have at least {min_count} agents"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
