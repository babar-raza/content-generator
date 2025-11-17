"""
Agent Negotiation System - Phase 6: Peer-to-Peer Coordination
"""

import threading
import time
import uuid
import logging
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

from src.core import AgentEvent, EventBus
from src.core.contracts import (
    CapabilityRequest, NegotiationBid, CapabilityClaim, DependencySpec,
    NegotiationStatus
)


logger = logging.getLogger(__name__)


class NegotiationEvent(AgentEvent):
    """Extended event for negotiation protocols"""
    
    def __init__(self, event_type: str, agent_id: str, correlation_id: str,
                 negotiation_data: Dict[str, Any], target_agent: Optional[str] = None,
                 request_id: Optional[str] = None, timestamp: datetime = None):
        super().__init__(event_type, agent_id, correlation_id, negotiation_data, timestamp)
        self.target_agent = target_agent  # For direct agent communication
        self.request_id = request_id  # Links to original request


class DependencyTracker:
    """Tracks agent dependencies and completion status"""
    
    def __init__(self):
        self.dependencies: Dict[str, List[DependencySpec]] = defaultdict(list)  # agent_id -> dependencies
        self.completed_outputs: Dict[str, Set[str]] = defaultdict(set)  # correlation_id -> completed outputs
        self.waiting_agents: Dict[str, List[str]] = defaultdict(list)  # output_key -> waiting agent_ids
        self.dependency_timeouts: Dict[str, datetime] = {}  # dependency_id -> timeout
        self.lock = threading.RLock()
        
    def add_dependency(self, agent_id: str, dependency: DependencySpec) -> None:
        """Add a dependency for an agent"""
        with self.lock:
            self.dependencies[agent_id].append(dependency)
            output_key = f"{dependency.correlation_id}:{dependency.required_output}"
            self.waiting_agents[output_key].append(agent_id)
            self.dependency_timeouts[dependency.dependency_id] = (
                datetime.now() + timedelta(seconds=dependency.timeout)
            )
            
            logger.info(f"Added dependency {dependency.dependency_id} for agent {agent_id}")
    
    def mark_output_completed(self, correlation_id: str, output: str, providing_agent: str) -> List[str]:
        """Mark an output as completed and return waiting agents"""
        with self.lock:
            output_key = f"{correlation_id}:{output}"
            self.completed_outputs[correlation_id].add(output)
            
            # Get agents that were waiting for this output
            waiting_agents = self.waiting_agents.get(output_key, [])
            
            # Remove them from waiting list
            if output_key in self.waiting_agents:
                del self.waiting_agents[output_key]
            
            logger.info(f"Output {output} completed by {providing_agent}, notifying {len(waiting_agents)} waiting agents")
            return waiting_agents
    
    def check_dependencies_ready(self, agent_id: str, correlation_id: str) -> bool:
        """Check if all dependencies for an agent are satisfied"""
        with self.lock:
            agent_deps = self.dependencies.get(agent_id, [])
            correlation_deps = [dep for dep in agent_deps if dep.correlation_id == correlation_id]
            
            for dep in correlation_deps:
                if dep.required_output not in self.completed_outputs.get(correlation_id, set()):
                    # Check if dependency has timed out
                    if dep.dependency_id in self.dependency_timeouts:
                        if datetime.now() > self.dependency_timeouts[dep.dependency_id]:
                            if dep.is_critical:
                                logger.warning(f"Critical dependency {dep.dependency_id} timed out")
                                return False
                            else:
                                logger.info(f"Non-critical dependency {dep.dependency_id} timed out, proceeding")
                                continue
                    else:
                        return False
            
            return True
    
    def get_missing_dependencies(self, agent_id: str, correlation_id: str) -> List[DependencySpec]:
        """Get list of missing dependencies for an agent"""
        with self.lock:
            agent_deps = self.dependencies.get(agent_id, [])
            correlation_deps = [dep for dep in agent_deps if dep.correlation_id == correlation_id]
            
            missing = []
            for dep in correlation_deps:
                if dep.required_output not in self.completed_outputs.get(correlation_id, set()):
                    missing.append(dep)
            
            return missing


class NegotiationManager:
    """Manages agent-to-agent negotiations and coordination"""
    
    def __init__(self, event_bus: EventBus, timeout: float = 30.0):
        self.event_bus = event_bus
        self.timeout = timeout
        
        # Active negotiations
        self.active_requests: Dict[str, CapabilityRequest] = {}  # request_id -> request
        self.request_bids: Dict[str, List[NegotiationBid]] = defaultdict(list)  # request_id -> bids
        self.active_claims: Dict[str, CapabilityClaim] = {}  # claim_id -> claim
        self.negotiation_status: Dict[str, NegotiationStatus] = {}  # request_id -> status
        
        # Dependency tracking
        self.dependency_tracker = DependencyTracker()
        
        # Statistics
        self.negotiation_stats = {
            "requests_made": 0,
            "bids_received": 0,
            "claims_made": 0,
            "successful_negotiations": 0,
            "failed_negotiations": 0,
            "timeout_negotiations": 0
        }
        
        # ===== PHASE 7: FAULT TOLERANCE ENHANCEMENTS =====
        
        # Failure tracking during negotiation
        self.failed_negotiations: Dict[str, List[str]] = defaultdict(list)  # correlation_id -> failed_agent_ids
        self.negotiation_timeouts: Dict[str, datetime] = {}  # request_id -> timeout
        self.max_negotiation_retries = 3
        
        # Recovery tracking
        self.recovering_negotiations: Set[str] = set()  # correlation_ids in recovery
        self.agent_failure_counts: Dict[str, int] = defaultdict(int)  # agent_id -> failure_count
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        
        # Subscribe to negotiation events
        self._subscribe_to_events()
        
        logger.info("NegotiationManager initialized")
    
    def _subscribe_to_events(self) -> None:
        """Subscribe to negotiation-related events"""
        self.event_bus.subscribe("capability_request", self._handle_capability_request)
        self.event_bus.subscribe("capability_bid", self._handle_capability_bid)
        self.event_bus.subscribe("capability_claim", self._handle_capability_claim)
        self.event_bus.subscribe("capability_complete", self._handle_capability_complete)
        self.event_bus.subscribe("capability_failed", self._handle_capability_failed)
        self.event_bus.subscribe("dependency_check", self._handle_dependency_check)
    
    def request_capability(self, requester_id: str, capability: str, correlation_id: str,
                          input_data: Dict[str, Any], **kwargs) -> str:
        """
        Request a capability from peer agents
        
        Returns:
            request_id for tracking the request
        """
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        request = CapabilityRequest(
            request_id=request_id,
            requester_id=requester_id,
            capability=capability,
            correlation_id=correlation_id,
            input_data=input_data,
            **kwargs
        )
        
        with self.lock:
            self.active_requests[request_id] = request
            self.negotiation_status[request_id] = NegotiationStatus.REQUESTED
            self.negotiation_stats["requests_made"] += 1
        
        # Publish the request
        event = NegotiationEvent(
            event_type="capability_request",
            agent_id=requester_id,
            correlation_id=correlation_id,
            negotiation_data=request.to_dict(),
            request_id=request_id
        )
        
        self.event_bus.publish(event)
        
        logger.info(f"Capability request {request_id} for {capability} published by {requester_id}")
        return request_id
    
    def submit_bid(self, request_id: str, agent_id: str, **bid_kwargs) -> str:
        """Submit a bid for a capability request"""
        if request_id not in self.active_requests:
            logger.warning(f"Bid submitted for unknown request {request_id}")
            return None
        
        request = self.active_requests[request_id]
        bid_id = f"bid_{uuid.uuid4().hex[:8]}"
        
        bid = NegotiationBid(
            request_id=request_id,
            bid_id=bid_id,
            agent_id=agent_id,
            capability=request.capability,
            correlation_id=request.correlation_id,
            **bid_kwargs
        )
        
        with self.lock:
            self.request_bids[request_id].append(bid)
            self.negotiation_status[request_id] = NegotiationStatus.BIDDING
            self.negotiation_stats["bids_received"] += 1
        
        # Publish the bid
        event = NegotiationEvent(
            event_type="capability_bid",
            agent_id=agent_id,
            correlation_id=request.correlation_id,
            negotiation_data=bid.to_dict(),
            target_agent=request.requester_id,
            request_id=request_id
        )
        
        self.event_bus.publish(event)
        
        logger.info(f"Bid {bid_id} submitted by {agent_id} for request {request_id}")
        return bid_id
    
    def claim_capability(self, request_id: str, bid_id: str, agent_id: str) -> str:
        """Claim a capability after winning the bid"""
        if request_id not in self.active_requests:
            logger.warning(f"Claim submitted for unknown request {request_id}")
            return None
        
        request = self.active_requests[request_id]
        claim_id = f"claim_{uuid.uuid4().hex[:8]}"
        
        # Find the winning bid
        winning_bid = None
        for bid in self.request_bids.get(request_id, []):
            if bid.bid_id == bid_id:
                winning_bid = bid
                break
        
        if not winning_bid:
            logger.warning(f"Claim submitted for unknown bid {bid_id}")
            return None
        
        claim = CapabilityClaim(
            request_id=request_id,
            claim_id=claim_id,
            agent_id=agent_id,
            capability=request.capability,
            correlation_id=request.correlation_id,
            estimated_completion=datetime.now() + timedelta(seconds=winning_bid.estimated_time)
        )
        
        with self.lock:
            self.active_claims[claim_id] = claim
            self.negotiation_status[request_id] = NegotiationStatus.CLAIMED
            self.negotiation_stats["claims_made"] += 1
        
        # Publish the claim
        event = NegotiationEvent(
            event_type="capability_claim",
            agent_id=agent_id,
            correlation_id=request.correlation_id,
            negotiation_data=claim.to_dict(),
            target_agent=request.requester_id,
            request_id=request_id
        )
        
        self.event_bus.publish(event)
        
        logger.info(f"Capability {request.capability} claimed by {agent_id} (claim {claim_id})")
        return claim_id
    
    def complete_capability(self, claim_id: str, output_data: Dict[str, Any]) -> None:
        """Mark a capability as completed"""
        if claim_id not in self.active_claims:
            logger.warning(f"Completion reported for unknown claim {claim_id}")
            return
        
        claim = self.active_claims[claim_id]
        
        with self.lock:
            self.negotiation_status[claim.request_id] = NegotiationStatus.COMPLETED
            self.negotiation_stats["successful_negotiations"] += 1
        
        # Notify dependency tracker of completed outputs
        for output_key in output_data.keys():
            waiting_agents = self.dependency_tracker.mark_output_completed(
                claim.correlation_id, output_key, claim.agent_id
            )
            
            # Notify waiting agents
            for waiting_agent in waiting_agents:
                self.event_bus.publish(NegotiationEvent(
                    event_type="dependency_ready",
                    agent_id=claim.agent_id,
                    correlation_id=claim.correlation_id,
                    negotiation_data={
                        "output": output_key,
                        "data": output_data[output_key],
                        "waiting_agent": waiting_agent
                    },
                    target_agent=waiting_agent
                ))
        
        # Publish completion
        event = NegotiationEvent(
            event_type="capability_complete",
            agent_id=claim.agent_id,
            correlation_id=claim.correlation_id,
            negotiation_data={
                "claim_id": claim_id,
                "capability": claim.capability,
                "output_data": output_data
            },
            request_id=claim.request_id
        )
        
        self.event_bus.publish(event)
        
        logger.info(f"Capability {claim.capability} completed by {claim.agent_id}")
    
    def add_dependency(self, agent_id: str, dependency: DependencySpec) -> None:
        """Add a dependency for an agent"""
        self.dependency_tracker.add_dependency(agent_id, dependency)
    
    def check_dependencies_ready(self, agent_id: str, correlation_id: str) -> bool:
        """Check if agent's dependencies are ready"""
        return self.dependency_tracker.check_dependencies_ready(agent_id, correlation_id)
    
    def get_missing_dependencies(self, agent_id: str, correlation_id: str) -> List[DependencySpec]:
        """Get missing dependencies for an agent"""
        return self.dependency_tracker.get_missing_dependencies(agent_id, correlation_id)
    
    def _handle_capability_request(self, event: AgentEvent) -> None:
        """Handle incoming capability request"""
        logger.debug(f"Handling capability request: {event.event_type}")
    
    def _handle_capability_bid(self, event: AgentEvent) -> None:
        """Handle incoming capability bid"""
        logger.debug(f"Handling capability bid: {event.event_type}")
    
    def _handle_capability_claim(self, event: AgentEvent) -> None:
        """Handle capability claim"""
        logger.debug(f"Handling capability claim: {event.event_type}")
    
    def _handle_capability_complete(self, event: AgentEvent) -> None:
        """Handle capability completion"""
        logger.debug(f"Handling capability completion: {event.event_type}")
    
    def _handle_capability_failed(self, event: AgentEvent) -> None:
        """Handle capability failure"""
        request_id = getattr(event, 'request_id', None)
        if request_id:
            with self.lock:
                self.negotiation_status[request_id] = NegotiationStatus.FAILED
                self.negotiation_stats["failed_negotiations"] += 1
        
        logger.warning(f"Capability failed: {event.data}")
    
    def _handle_dependency_check(self, event: AgentEvent) -> None:
        """Handle dependency readiness check"""
        logger.debug(f"Handling dependency check: {event.event_type}")
    
    def _cleanup_expired(self) -> None:
        """Background thread to clean up expired negotiations"""
        while True:
            try:
                time.sleep(5)  # Check every 5 seconds
                
                current_time = datetime.now()
                expired_requests = []
                
                with self.lock:
                    for request_id, request in self.active_requests.items():
                        if (current_time - request.timestamp).total_seconds() > request.max_wait_time:
                            if self.negotiation_status.get(request_id) in [NegotiationStatus.REQUESTED, NegotiationStatus.BIDDING]:
                                expired_requests.append(request_id)
                
                # Mark expired requests as timed out
                for request_id in expired_requests:
                    with self.lock:
                        self.negotiation_status[request_id] = NegotiationStatus.CANCELLED
                        self.negotiation_stats["timeout_negotiations"] += 1
                    
                    logger.info(f"Request {request_id} timed out")
                    
            except Exception as e:
                logger.error(f"Error in negotiation cleanup: {e}")
    
    # ===== PHASE 7: FAULT TOLERANCE METHODS =====
    
    def handle_agent_failure(self, failed_agent_id: str) -> None:
        """Handle failure of an agent during negotiations"""
        with self.lock:
            logger.warning(f"Handling failure of agent {failed_agent_id} in negotiations")
            
            # Track agent failure
            self.agent_failure_counts[failed_agent_id] += 1
            
            # Find affected negotiations
            affected_requests = []
            affected_claims = []
            
            # Check active requests where this agent was involved
            for request_id, request in self.active_requests.items():
                if request.requester_id == failed_agent_id:
                    affected_requests.append(request_id)
            
            # Check active claims by this agent
            for claim_id, claim in self.active_claims.items():
                if claim.agent_id == failed_agent_id:
                    affected_claims.append(claim_id)
            
            # Cancel affected requests and attempt recovery
            for request_id in affected_requests:
                self._cancel_and_retry_request(request_id, failed_agent_id)
            
            # Cancel affected claims and reassign work
            for claim_id in affected_claims:
                self._cancel_and_reassign_claim(claim_id, failed_agent_id)
    
    def _cancel_and_retry_request(self, request_id: str, failed_agent_id: str) -> None:
        """Cancel a request from failed agent and retry if possible"""
        logger.info(f"Canceling request {request_id} from failed agent {failed_agent_id}")
        
        request = self.active_requests.get(request_id)
        if not request:
            return
        
        # Mark correlation as having failure
        correlation_id = request.correlation_id
        self.failed_negotiations[correlation_id].append(failed_agent_id)
        
        # Cancel the request
        self.negotiation_status[request_id] = NegotiationStatus.CANCELLED
        self.negotiation_stats["failed_negotiations"] += 1
        
        # Remove from active tracking
        self.active_requests.pop(request_id, None)
        self.request_bids.pop(request_id, None)
        
        # Check if we should retry
        failure_count = len(self.failed_negotiations[correlation_id])
        if failure_count < self.max_negotiation_retries:
            logger.info(f"Retrying negotiation for {correlation_id} (attempt {failure_count + 1})")
            self.recovering_negotiations.add(correlation_id)
            
            # Could trigger retry logic here
            # For now, just log that retry is needed
            logger.info(f"Negotiation recovery needed for {correlation_id}")
        else:
            logger.error(f"Maximum retries exceeded for {correlation_id}, negotiation failed")
    
    def _cancel_and_reassign_claim(self, claim_id: str, failed_agent_id: str) -> None:
        """Cancel a claim from failed agent and attempt reassignment"""
        logger.info(f"Canceling claim {claim_id} from failed agent {failed_agent_id}")
        
        claim = self.active_claims.get(claim_id)
        if not claim:
            return
        
        # Remove the claim
        self.active_claims.pop(claim_id, None)
        
        # Mark correlation as having failure
        correlation_id = claim.correlation_id
        self.failed_negotiations[correlation_id].append(failed_agent_id)
        
        # Attempt to reassign the work
        # This would typically trigger a new capability request
        logger.info(f"Work reassignment needed for claim {claim_id}")
        
        # Publish failure event for other systems to handle
        self.event_bus.publish(AgentEvent(
            event_type="capability_failed",
            agent_id=failed_agent_id,
            correlation_id=correlation_id,
            data={
                "claim_id": claim_id,
                "capability": claim.capability,
                "reason": "agent_failure"
            }
        ))
    
    def mark_agent_recovered(self, agent_id: str) -> None:
        """Mark an agent as recovered from failure"""
        with self.lock:
            if agent_id in self.agent_failure_counts:
                logger.info(f"Agent {agent_id} recovered, resetting failure count")
                self.agent_failure_counts[agent_id] = 0
    
    def is_agent_problematic(self, agent_id: str, threshold: int = 3) -> bool:
        """Check if an agent has too many recent failures"""
        with self.lock:
            return self.agent_failure_counts.get(agent_id, 0) >= threshold
    
    def get_fault_tolerance_status(self) -> Dict[str, Any]:
        """Get fault tolerance status of negotiation system"""
        with self.lock:
            return {
                "failed_negotiations": dict(self.failed_negotiations),
                "recovering_negotiations": list(self.recovering_negotiations),
                "agent_failure_counts": dict(self.agent_failure_counts),
                "max_retries": self.max_negotiation_retries,
                "active_timeouts": len(self.negotiation_timeouts)
            }
    
    def force_recovery_reset(self, correlation_id: str) -> bool:
        """Force reset recovery state for a correlation (admin function)"""
        with self.lock:
            if correlation_id in self.recovering_negotiations:
                self.recovering_negotiations.remove(correlation_id)
                self.failed_negotiations.pop(correlation_id, None)
                logger.info(f"Force-reset recovery for {correlation_id}")
                return True
            return False
    
    def get_negotiation_stats(self) -> Dict[str, Any]:
        """Get negotiation statistics including fault tolerance info"""
        with self.lock:
            stats = self.negotiation_stats.copy()
            stats["active_requests"] = len(self.active_requests)
            stats["active_claims"] = len(self.active_claims)
            stats["fault_tolerance"] = self.get_fault_tolerance_status()
            return stats


# Global negotiation manager instance
_negotiation_manager = None


def get_negotiation_manager() -> NegotiationManager:
    """Get global negotiation manager instance"""
    global _negotiation_manager
    if _negotiation_manager is None:
        from src.core import EventBus
        # This will need to be initialized with the actual event bus
        logger.warning("NegotiationManager not initialized, creating temporary instance")
        _negotiation_manager = NegotiationManager(EventBus())
    return _negotiation_manager


def set_negotiation_manager(manager: NegotiationManager) -> None:
    """Set global negotiation manager instance"""
    global _negotiation_manager
    _negotiation_manager = manager
