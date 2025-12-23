"""Tests for MeshDebugAdapter - MESH-009 implementation.

Tests cover:
- Bid visualization
- Timeline event tracking
- Workflow state updates
- Integration with DebugController
- Thread safety
"""

import pytest
import uuid
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

from src.core.contracts import Bid
from src.debug.controller import DebugController
from src.debug.mesh_adapter import (
    BidVisualization,
    MeshDebugAdapter,
    MeshTimelineEvent,
    get_global_mesh_adapter,
    reset_global_mesh_adapter,
)
from src.debug.models import ExecutionStateStatus


@pytest.fixture
def debug_controller():
    """Create debug controller for testing."""
    return DebugController()


@pytest.fixture
def mesh_adapter(debug_controller):
    """Create mesh debug adapter for testing."""
    return MeshDebugAdapter(debug_controller)


@pytest.fixture
def workflow_id():
    """Generate workflow ID for testing."""
    return f"test-workflow-{uuid.uuid4()}"


@pytest.fixture
def sample_bid():
    """Create sample bid for testing."""
    return Bid(
        agent_id="agent-123",
        capability="keyword_extraction",
        correlation_id="corr-456",
        estimated_time=1.5,
        confidence=0.85,
        priority=5,
        current_load=2,
        max_capacity=10,
        health_score=0.95,
        success_rate=0.92,
        additional_info={
            "score_components": {
                "capability_match": 1.0,
                "success_rate": 0.92,
                "latency": 0.8,
                "health": 0.95,
                "load": 0.8,
            }
        },
    )


class TestMeshDebugAdapter:
    """Test suite for MeshDebugAdapter."""

    def test_initialization(self, debug_controller):
        """Test adapter initialization."""
        adapter = MeshDebugAdapter(debug_controller)

        assert adapter.debug_controller == debug_controller
        assert isinstance(adapter._workflow_bids, dict)
        assert isinstance(adapter._timeline_events, dict)

    def test_on_capability_request(self, mesh_adapter, workflow_id):
        """Test capability request event handling."""
        input_data = {"topic": "Python async patterns"}
        context = {"mode": "test"}

        mesh_adapter.on_capability_request(
            workflow_id,
            "keyword_extraction",
            input_data,
            context,
        )

        # Verify timeline event created
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "capability_request"
        assert timeline[0].capability == "keyword_extraction"
        assert timeline[0].workflow_id == workflow_id

        # Verify bids cleared
        bids = mesh_adapter.get_bids(workflow_id)
        assert len(bids) == 0

    def test_on_bid_received(self, mesh_adapter, workflow_id, sample_bid):
        """Test bid received event handling."""
        mesh_adapter.on_bid_received(workflow_id, sample_bid)

        # Verify bid stored
        bids = mesh_adapter.get_bids(workflow_id)
        assert len(bids) == 1
        assert bids[0].agent_id == "agent-123"
        assert bids[0].capability == "keyword_extraction"
        assert bids[0].confidence == 0.85

        # Verify timeline event created
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "bid_received"
        assert timeline[0].agent_id == "agent-123"

    def test_multiple_bids(self, mesh_adapter, workflow_id):
        """Test handling multiple bids for same capability."""
        # Create multiple bids
        for i in range(3):
            bid = Bid(
                agent_id=f"agent-{i}",
                capability="keyword_extraction",
                correlation_id="corr-123",
                estimated_time=1.0 + i * 0.1,
                confidence=0.8 + i * 0.05,
                priority=5,
                current_load=i,
                max_capacity=10,
                health_score=0.9,
                success_rate=0.85,
                additional_info={"score_components": {}},
            )
            mesh_adapter.on_bid_received(workflow_id, bid)

        # Verify all bids stored
        bids = mesh_adapter.get_bids(workflow_id)
        assert len(bids) == 3

        # Verify can filter by capability
        kb_bids = mesh_adapter.get_bids(workflow_id, "keyword_extraction")
        assert len(kb_bids) == 3

    def test_on_agent_selected(self, mesh_adapter, workflow_id, sample_bid):
        """Test agent selected event handling."""
        # First receive bid
        mesh_adapter.on_bid_received(workflow_id, sample_bid)

        # Then select agent
        mesh_adapter.on_agent_selected(
            workflow_id,
            "agent-123",
            "keyword_extraction",
            sample_bid,
        )

        # Verify timeline event
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert any(e.event_type == "agent_selected" for e in timeline)

        selected_event = next(e for e in timeline if e.event_type == "agent_selected")
        assert selected_event.agent_id == "agent-123"
        assert selected_event.capability == "keyword_extraction"
        assert "all_bids" in selected_event.data
        assert selected_event.data["bids_received"] == 1

    def test_on_agent_execution_start(self, mesh_adapter, workflow_id):
        """Test agent execution start event handling."""
        inputs = {"topic": "Python async", "keywords": ["async", "await"]}

        mesh_adapter.on_agent_execution_start(
            workflow_id,
            "agent-123",
            "keyword_extraction",
            inputs,
        )

        # Verify timeline event
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "agent_execution_start"
        assert timeline[0].agent_id == "agent-123"
        assert "snapshot_id" in timeline[0].data

    def test_on_agent_execution_complete_success(self, mesh_adapter, workflow_id):
        """Test successful agent execution complete."""
        outputs = {"keywords": ["async", "await", "asyncio"]}

        mesh_adapter.on_agent_execution_complete(
            workflow_id,
            "agent-123",
            "keyword_extraction",
            outputs,
            duration_ms=245.5,
            success=True,
        )

        # Verify timeline event
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "agent_execution_complete"
        assert timeline[0].data["success"] is True
        assert timeline[0].data["duration_ms"] == 245.5

    def test_on_agent_execution_complete_failure(self, mesh_adapter, workflow_id):
        """Test failed agent execution complete."""
        mesh_adapter.on_agent_execution_complete(
            workflow_id,
            "agent-123",
            "keyword_extraction",
            {},
            duration_ms=100.0,
            success=False,
            error="Agent execution timeout",
        )

        # Verify timeline event
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "agent_execution_complete"
        assert timeline[0].data["success"] is False
        assert timeline[0].data["error"] == "Agent execution timeout"

    def test_on_workflow_paused(self, mesh_adapter, workflow_id):
        """Test workflow paused event handling."""
        mesh_adapter.on_workflow_paused(workflow_id, "Waiting for approval")

        # Verify timeline event
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "workflow_paused"
        assert timeline[0].data["reason"] == "Waiting for approval"

    def test_on_workflow_resumed(self, mesh_adapter, workflow_id):
        """Test workflow resumed event handling."""
        mesh_adapter.on_workflow_resumed(workflow_id)

        # Verify timeline event
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 1
        assert timeline[0].event_type == "workflow_resumed"

    def test_complete_workflow_flow(self, mesh_adapter, workflow_id, sample_bid):
        """Test complete workflow flow with all events."""
        # 1. Capability request
        mesh_adapter.on_capability_request(
            workflow_id,
            "keyword_extraction",
            {"topic": "Python async"},
        )

        # 2. Multiple bids
        for i in range(3):
            bid = Bid(
                agent_id=f"agent-{i}",
                capability="keyword_extraction",
                correlation_id="corr-123",
                estimated_time=1.0,
                confidence=0.7 + i * 0.1,
                priority=5,
                current_load=0,
                max_capacity=10,
                health_score=0.9,
                success_rate=0.85,
                additional_info={"score_components": {}},
            )
            mesh_adapter.on_bid_received(workflow_id, bid)

        # 3. Agent selected
        mesh_adapter.on_agent_selected(workflow_id, "agent-2", "keyword_extraction")

        # 4. Agent execution
        mesh_adapter.on_agent_execution_start(
            workflow_id,
            "agent-2",
            "keyword_extraction",
            {"topic": "Python async"},
        )

        mesh_adapter.on_agent_execution_complete(
            workflow_id,
            "agent-2",
            "keyword_extraction",
            {"keywords": ["async", "await"]},
            duration_ms=200.0,
            success=True,
        )

        # Verify timeline
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 7  # request + 3 bids + selection + start + complete (7 events)

        event_types = [e.event_type for e in timeline]
        assert "capability_request" in event_types
        assert event_types.count("bid_received") == 3
        assert "agent_selected" in event_types
        assert "agent_execution_start" in event_types
        assert "agent_execution_complete" in event_types

        # Verify bids
        bids = mesh_adapter.get_bids(workflow_id)
        assert len(bids) == 3

    def test_clear_workflow_data(self, mesh_adapter, workflow_id, sample_bid):
        """Test clearing workflow data."""
        # Add some data
        mesh_adapter.on_capability_request(workflow_id, "test", {})
        mesh_adapter.on_bid_received(workflow_id, sample_bid)

        # Verify data exists
        assert len(mesh_adapter.get_timeline_events(workflow_id)) > 0
        assert len(mesh_adapter.get_bids(workflow_id)) > 0

        # Clear data
        mesh_adapter.clear_workflow_data(workflow_id)

        # Verify data cleared
        assert len(mesh_adapter.get_timeline_events(workflow_id)) == 0
        assert len(mesh_adapter.get_bids(workflow_id)) == 0

    def test_thread_safety(self, mesh_adapter, workflow_id):
        """Test thread safety of adapter operations."""
        import threading

        def add_events():
            for i in range(10):
                mesh_adapter.on_capability_request(
                    workflow_id,
                    f"capability-{i}",
                    {},
                )

        # Run multiple threads
        threads = [threading.Thread(target=add_events) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify all events recorded (5 threads * 10 events each)
        timeline = mesh_adapter.get_timeline_events(workflow_id)
        assert len(timeline) == 50

    def test_bid_visualization_to_dict(self, sample_bid):
        """Test BidVisualization serialization."""
        bid_viz = BidVisualization(
            bid_id="bid-123",
            agent_id=sample_bid.agent_id,
            capability=sample_bid.capability,
            score=0.88,
            confidence=sample_bid.confidence,
            estimated_time=sample_bid.estimated_time,
            current_load=sample_bid.current_load,
            health_score=sample_bid.health_score,
            components={"test": 0.5},
        )

        data = bid_viz.to_dict()
        assert data["bid_id"] == "bid-123"
        assert data["agent_id"] == sample_bid.agent_id
        assert data["score"] == 0.88
        assert "timestamp" in data

    def test_timeline_event_to_dict(self, workflow_id):
        """Test MeshTimelineEvent serialization."""
        event = MeshTimelineEvent(
            event_id="event-123",
            event_type="capability_request",
            workflow_id=workflow_id,
            capability="test_capability",
            data={"key": "value"},
        )

        data = event.to_dict()
        assert data["event_id"] == "event-123"
        assert data["event_type"] == "capability_request"
        assert data["workflow_id"] == workflow_id
        assert data["capability"] == "test_capability"
        assert "timestamp" in data


class TestGlobalMeshAdapter:
    """Test global mesh adapter singleton."""

    def test_get_global_adapter(self):
        """Test getting global adapter instance."""
        adapter1 = get_global_mesh_adapter()
        adapter2 = get_global_mesh_adapter()

        assert adapter1 is adapter2

    def test_reset_global_adapter(self):
        """Test resetting global adapter."""
        adapter1 = get_global_mesh_adapter()
        reset_global_mesh_adapter()
        adapter2 = get_global_mesh_adapter()

        assert adapter1 is not adapter2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
