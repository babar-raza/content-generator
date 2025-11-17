"""
Capability Registry - Phase 9B: Enhanced with Predictive Scheduling & Cross-Agent Optimization
"""

import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from src.core.contracts import (
    AgentContract, CapabilitySpec, Bid, WorkSpec, 
    BidResult, CapabilityStatus, FlowControlStatus,
    CapacityLevel, CapacityInfo, FlowControlEvent
)

try:
    from src.core.config import Config
    PHASE_9B_AVAILABLE = True
except ImportError:
    PHASE_9B_AVAILABLE = False


logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """Registry for capability discovery and bidding coordination"""
    
    def __init__(self, bid_timeout: float = 2.0, selection_strategy: str = "highest_score"):
        """
        Initialize capability registry
        
        Args:
            bid_timeout: Time to wait for bids in seconds
            selection_strategy: How to select winning bid (highest_score, fastest, most_confident)
        """
        self.agents: Dict[str, 'Agent'] = {}
        self.contracts: Dict[str, AgentContract] = {}
        self.capabilities: Dict[str, Set[str]] = defaultdict(set)  # capability -> set of agent_ids
        self.bid_timeout = bid_timeout
        self.selection_strategy = selection_strategy
        
        # Tracking
        self.active_bids: Dict[str, List[Bid]] = {}  # correlation_id -> bids
        self.bid_history: List[BidResult] = []
        self.execution_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Health tracking
        self.agent_health: Dict[str, float] = {}
        self.last_heartbeat: Dict[str, datetime] = {}
        self.heartbeat_timeout = 10.0  # seconds
        
        # ===== PHASE 7: FAULT TOLERANCE & RECOVERY =====
        
        # Work execution tracking
        self.claimed_work: Dict[str, Dict[str, Any]] = {}  # work_id -> {agent_id, claim_time, timeout, work_spec}
        self.work_timeouts: Dict[str, datetime] = {}  # work_id -> timeout
        self.execution_timeout = 30.0  # seconds
        
        # Failure tracking
        self.failed_agents: Set[str] = set()
        self.agent_failures: Dict[str, List[datetime]] = defaultdict(list)  # agent_id -> failure times
        self.failure_window = 300.0  # 5 minutes
        self.max_failures_per_window = 3
        
        # Recovery tracking
        self.recovering_agents: Dict[str, datetime] = {}  # agent_id -> recovery_start_time
        self.recovery_grace_period = 60.0  # seconds
        
        # Fault tolerance monitoring
        self.fault_stats = {
            "agent_failures": 0,
            "work_timeouts": 0,
            "successful_reassignments": 0,
            "failed_reassignments": 0,
            "recovered_agents": 0
        }
        
        # ===== PHASE 8: BACK-PRESSURE & FLOW CONTROL =====
        
        # Capacity tracking
        self.agent_capacity: Dict[str, CapacityInfo] = {}
        self.flow_control_enabled = True
        self.system_load_threshold = 0.8  # System considered overloaded at 80%
        
        # Flow control statistics
        self.flow_stats = {
            "overload_events": 0,
            "throttle_events": 0,
            "capacity_adjustments": 0,
            "work_rejections": 0,
            "flow_control_saves": 0  # Times flow control prevented overload
        }
        
        # Back-pressure management
        self.overloaded_agents: Set[str] = set()
        self.throttled_agents: Set[str] = set()
        self.system_overload_mode = False
        
        # Start fault tolerance monitoring thread
        self._start_fault_monitor()
        
        # ===== PHASE 9B: PREDICTIVE SCHEDULING & CROSS-AGENT OPTIMIZATION =====
        
        if PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B:
            # Predictive scheduling
            self.predictive_enabled = Config.PREFETCH_ENABLED
            self.capability_sequences: Dict[str, List[str]] = {}  # correlation_id -> capability sequence
            self.transition_patterns: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))  # from_cap -> {to_cap: probability}
            self.prefetch_requests: Dict[str, Dict[str, Any]] = {}  # correlation_id -> {capability: prefetch_data}
            
            # Load performance hints
            try:
                self.perf_hints = Config.load_perf_hints()
                self.hot_paths = self.perf_hints.get("hot_paths", {})
                self.prefetch_rules = self.perf_hints.get("prefetch_rules", {})
                logger.info(f"Loaded performance hints: {len(self.hot_paths)} hot paths, {len(self.prefetch_rules)} prefetch rules")
            except Exception as e:
                logger.warning(f"Failed to load performance hints: {e}")
                self.perf_hints = {}
                self.hot_paths = {}
                self.prefetch_rules = {}
            
            # Cross-agent optimization tracking
            self.cross_agent_stats = {
                "prefetch_hits": 0,
                "prefetch_misses": 0,
                "soft_bids_generated": 0,
                "pipeline_triggers": 0,
                "batch_aggregations": 0
            }
            
            # Soft bidding for predictive scheduling
            self.soft_bids: Dict[str, List[Dict[str, Any]]] = {}  # correlation_id -> [soft_bid_data]
            self.soft_bid_threshold = Config.SOFT_BID_THRESHOLD
            
            logger.info("CapabilityRegistry: Phase 9B predictive scheduling enabled")
        else:
            self.predictive_enabled = False
            logger.info("CapabilityRegistry: Phase 9B features disabled")
        
        logger.info(f"CapabilityRegistry initialized with strategy: {selection_strategy}")
    
    def register_agent(self, agent: 'Agent', contract: AgentContract) -> None:
        """Register an agent with its capabilities"""
        with self.lock:
            self.agents[agent.agent_id] = agent
            self.contracts[agent.agent_id] = contract
            
            # Index capabilities for fast lookup
            for capability in contract.capabilities:
                self.capabilities[capability].add(agent.agent_id)
            
            # Initialize health
            self.agent_health[agent.agent_id] = 1.0
            self.last_heartbeat[agent.agent_id] = datetime.now()
            
            logger.info(f"Registered agent {agent.agent_id} with {len(contract.capabilities)} capabilities")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Remove agent from registry"""
        with self.lock:
            if agent_id in self.contracts:
                contract = self.contracts[agent_id]
                for capability in contract.capabilities:
                    self.capabilities[capability].discard(agent_id)
                
                del self.agents[agent_id]
                del self.contracts[agent_id]
                self.agent_health.pop(agent_id, None)
                self.last_heartbeat.pop(agent_id, None)
                
                logger.info(f"Unregistered agent {agent_id}")
    
    def find_capable_agents(self, capability: str, constraints: Dict[str, Any] = None) -> List['Agent']:
        """
        Find agents capable of performing a capability
        
        Args:
            capability: The capability needed
            constraints: Optional constraints to filter agents
            
        Returns:
            List of capable agents
        """
        with self.lock:
            agent_ids = self.capabilities.get(capability, set())
            capable_agents = []
            
            for agent_id in agent_ids:
                if agent_id not in self.agents:
                    continue
                    
                agent = self.agents[agent_id]
                contract = self.contracts[agent_id]
                
                # Check if agent is healthy
                if not self._is_agent_healthy(agent_id):
                    continue
                
                # Apply constraints if provided
                if constraints:
                    if not self._check_constraints(agent, contract, constraints):
                        continue
                
                capable_agents.append(agent)
            
            return capable_agents
    
    def request_bids(self, work_spec: WorkSpec) -> BidResult:
        """
        Request bids from capable agents with flow control considerations
        
        Args:
            work_spec: Specification of work to be done
            
        Returns:
            BidResult with winning bid and all bids
        """
        capability = work_spec.capability
        correlation_id = work_spec.correlation_id
        
        # ===== PHASE 8: FLOW CONTROL CHECKS =====
        
        # Check system-wide capacity before proceeding
        if self.flow_control_enabled and self._is_system_overloaded():
            logger.warning(f"System overloaded, rejecting bid request for {capability}")
            self.flow_stats["work_rejections"] += 1
            return BidResult(
                winning_bid=None,
                all_bids=[],
                selection_reason="System overloaded - back-pressure active"
            )
        
        # Find capable agents with flow control filtering
        capable_agents = self._find_available_agents(capability, work_spec.constraints)
        
        if not capable_agents:
            logger.warning(f"No available agents found for {capability}")
            return BidResult(
                winning_bid=None,
                all_bids=[],
                selection_reason="No capable/available agents found"
            )
        
        # Collect bids
        bids = []
        bid_threads = []
        
        def collect_bid(agent):
            try:
                # Double-check agent availability before requesting bid
                if self._can_agent_accept_work(agent):
                    bid = agent.bid(work_spec)
                    if bid:
                        with self.lock:
                            bids.append(bid)
                else:
                    logger.debug(f"Agent {agent.agent_id} cannot accept work due to flow control")
            except Exception as e:
                logger.error(f"Error collecting bid from {agent.agent_id}: {e}")
        
        # Start bid collection threads
        for agent in capable_agents:
            thread = threading.Thread(target=collect_bid, args=(agent,))
            thread.start()
            bid_threads.append(thread)
        
        # Wait for bids with timeout
        for thread in bid_threads:
            thread.join(timeout=self.bid_timeout)
        
        if not bids:
            logger.warning(f"No bids received for {capability}")
            # Check if this was due to flow control
            if len(capable_agents) > 0:
                self.flow_stats["work_rejections"] += 1
            return BidResult(
                winning_bid=None,
                all_bids=[],
                selection_reason="No bids received (possible flow control)"
            )
        
        # Select winner with flow control considerations
        winning_bid = self._select_winner_with_flow_control(bids)
        
        # Record result
        result = BidResult(
            winning_bid=winning_bid,
            all_bids=bids,
            selection_reason=f"Selected by {self.selection_strategy} strategy with flow control"
        )
        
        with self.lock:
            self.bid_history.append(result)
            self.active_bids[correlation_id] = bids
        
        # Notify winner
        if winning_bid:
            winning_agent = self.agents.get(winning_bid.agent_id)
            if winning_agent:
                # Update capacity tracking before assigning work
                self._update_agent_capacity(winning_bid.agent_id)
                winning_agent.on_bid_won(work_spec)
        
        logger.info(f"Bid winner for {capability}: {winning_bid.agent_id if winning_bid else 'None'}")
        
        return result
    
    def _select_winner(self, bids: List[Bid]) -> Optional[Bid]:
        """Select winning bid based on strategy"""
        if not bids:
            return None
        
        if self.selection_strategy == "highest_score":
            return max(bids, key=lambda b: b.score)
        elif self.selection_strategy == "fastest":
            return min(bids, key=lambda b: b.estimated_time)
        elif self.selection_strategy == "most_confident":
            return max(bids, key=lambda b: b.confidence)
        elif self.selection_strategy == "least_loaded":
            return min(bids, key=lambda b: b.current_load / max(b.max_capacity, 1))
        else:
            # Default to highest score
            return max(bids, key=lambda b: b.score)
    
    def _is_agent_healthy(self, agent_id: str) -> bool:
        """Check if agent is healthy based on heartbeats"""
        if agent_id not in self.last_heartbeat:
            return False
        
        time_since_heartbeat = (datetime.now() - self.last_heartbeat[agent_id]).total_seconds()
        if time_since_heartbeat > self.heartbeat_timeout:
            self.agent_health[agent_id] = 0.0
            return False
        
        return self.agent_health.get(agent_id, 0) > 0.5
    
    def _check_constraints(self, agent: 'Agent', contract: AgentContract, 
                          constraints: Dict[str, Any]) -> bool:
        """Check if agent meets specified constraints"""
        # Example constraints: min_confidence, max_load, required_version
        if "min_confidence" in constraints:
            # Would need to get this from agent
            pass
        
        if "max_load" in constraints:
            # Would need to check agent's current load
            pass
        
        if "required_version" in constraints:
            if contract.version < constraints["required_version"]:
                return False
        
        return True
    
    def heartbeat(self, agent_id: str, health: float = 1.0) -> None:
        """Update agent heartbeat and health"""
        with self.lock:
            self.last_heartbeat[agent_id] = datetime.now()
            self.agent_health[agent_id] = health
    
    def get_capability_stats(self, capability: str) -> Dict[str, Any]:
        """Get statistics for a capability"""
        with self.lock:
            agent_ids = self.capabilities.get(capability, set())
            
            # Calculate stats from bid history
            capability_bids = [
                result for result in self.bid_history
                if any(bid.capability == capability for bid in result.all_bids)
            ]
            
            if not capability_bids:
                return {
                    "capability": capability,
                    "available_agents": len(agent_ids),
                    "total_bids": 0,
                    "success_rate": 0.0,
                    "avg_bid_time": 0.0
                }
            
            total_bids = sum(len(result.all_bids) for result in capability_bids)
            successful_bids = sum(1 for result in capability_bids if result.winning_bid)
            
            # Calculate average bid times
            bid_times = []
            for result in capability_bids:
                for bid in result.all_bids:
                    bid_times.append(bid.estimated_time)
            
            avg_bid_time = sum(bid_times) / len(bid_times) if bid_times else 0.0
            
            return {
                "capability": capability,
                "available_agents": len(agent_ids),
                "total_bids": total_bids,
                "success_rate": successful_bids / len(capability_bids) if capability_bids else 0.0,
                "avg_bid_time": avg_bid_time,
                "bid_history_count": len(capability_bids)
            }
    
    def reassign_work(self, failed_agent_id: str, work_spec: WorkSpec) -> BidResult:
        """
        Reassign work from a failed agent
        
        Args:
            failed_agent_id: ID of the failed agent
            work_spec: Original work specification
            
        Returns:
            New bid result
        """
        logger.info(f"Reassigning work from failed agent {failed_agent_id}")
        
        # Exclude failed agent from bidding
        with self.lock:
            # Temporarily remove failed agent
            failed_agent = self.agents.pop(failed_agent_id, None)
        
        try:
            # Request new bids
            result = self.request_bids(work_spec)
        finally:
            # Restore failed agent (might recover)
            if failed_agent:
                with self.lock:
                    self.agents[failed_agent_id] = failed_agent
        
        return result
    
    # ===== PHASE 7: FAULT TOLERANCE & RECOVERY METHODS =====
    
    def _start_fault_monitor(self) -> None:
        """Start fault tolerance monitoring thread"""
        def monitor_loop():
            while True:
                try:
                    self._check_for_failures()
                    self._check_work_timeouts()
                    self._check_agent_recovery()
                    time.sleep(2)  # Check every 2 seconds
                except Exception as e:
                    logger.error(f"Fault monitor error: {e}")
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info("Fault tolerance monitor started")
    
    def _check_for_failures(self) -> None:
        """Check for failed agents based on heartbeats"""
        with self.lock:
            current_time = datetime.now()
            newly_failed = []
            
            for agent_id in list(self.agents.keys()):
                if agent_id in self.failed_agents:
                    continue  # Already marked as failed
                
                if not self._is_agent_healthy(agent_id):
                    # Agent is unhealthy, mark as failed
                    self._mark_agent_failed(agent_id, current_time)
                    newly_failed.append(agent_id)
            
            # Log newly failed agents
            for agent_id in newly_failed:
                logger.warning(f"Agent {agent_id} marked as failed due to missed heartbeats")
    
    def _mark_agent_failed(self, agent_id: str, failure_time: datetime) -> None:
        """Mark an agent as failed and track failure history"""
        with self.lock:
            self.failed_agents.add(agent_id)
            self.agent_failures[agent_id].append(failure_time)
            self.fault_stats["agent_failures"] += 1
            
            # Clean old failure records outside the window
            cutoff_time = failure_time - timedelta(seconds=self.failure_window)
            self.agent_failures[agent_id] = [
                t for t in self.agent_failures[agent_id] 
                if t > cutoff_time
            ]
            
            # Reassign all work claimed by this agent
            self._reassign_agent_work(agent_id)
    
    def _reassign_agent_work(self, failed_agent_id: str) -> None:
        """Reassign all work claimed by a failed agent"""
        with self.lock:
            work_to_reassign = []
            
            # Find work claimed by failed agent
            for work_id, work_info in self.claimed_work.items():
                if work_info["agent_id"] == failed_agent_id:
                    work_to_reassign.append((work_id, work_info))
            
            # Reassign each piece of work
            for work_id, work_info in work_to_reassign:
                logger.info(f"Reassigning work {work_id} from failed agent {failed_agent_id}")
                
                # Remove from claimed work
                self.claimed_work.pop(work_id, None)
                self.work_timeouts.pop(work_id, None)
                
                # Attempt reassignment
                try:
                    result = self.reassign_work(failed_agent_id, work_info["work_spec"])
                    if result.winning_bid:
                        self.fault_stats["successful_reassignments"] += 1
                        logger.info(f"Successfully reassigned work {work_id} to {result.winning_bid.agent_id}")
                    else:
                        self.fault_stats["failed_reassignments"] += 1
                        logger.error(f"Failed to reassign work {work_id} - no available agents")
                except Exception as e:
                    self.fault_stats["failed_reassignments"] += 1
                    logger.error(f"Error reassigning work {work_id}: {e}")
    
    def _check_work_timeouts(self) -> None:
        """Check for work that has timed out"""
        with self.lock:
            current_time = datetime.now()
            timed_out_work = []
            
            for work_id, timeout_time in self.work_timeouts.items():
                if current_time > timeout_time:
                    timed_out_work.append(work_id)
            
            # Handle timed out work
            for work_id in timed_out_work:
                work_info = self.claimed_work.get(work_id)
                if work_info:
                    agent_id = work_info["agent_id"]
                    logger.warning(f"Work {work_id} timed out for agent {agent_id}")
                    
                    self.fault_stats["work_timeouts"] += 1
                    
                    # Remove from tracking
                    self.claimed_work.pop(work_id, None)
                    self.work_timeouts.pop(work_id, None)
                    
                    # Attempt reassignment
                    try:
                        result = self.reassign_work(agent_id, work_info["work_spec"])
                        if result.winning_bid:
                            self.fault_stats["successful_reassignments"] += 1
                            logger.info(f"Successfully reassigned timed-out work {work_id} to {result.winning_bid.agent_id}")
                        else:
                            self.fault_stats["failed_reassignments"] += 1
                            logger.error(f"Failed to reassign timed-out work {work_id}")
                    except Exception as e:
                        self.fault_stats["failed_reassignments"] += 1
                        logger.error(f"Error reassigning timed-out work {work_id}: {e}")
    
    def _check_agent_recovery(self) -> None:
        """Check for agents that have recovered from failure"""
        with self.lock:
            current_time = datetime.now()
            recovered_agents = []
            
            for agent_id in list(self.failed_agents):
                # Check if agent is now healthy
                if self._is_agent_healthy(agent_id):
                    # Start recovery grace period if not already started
                    if agent_id not in self.recovering_agents:
                        self.recovering_agents[agent_id] = current_time
                        logger.info(f"Agent {agent_id} started recovery grace period")
                    else:
                        # Check if grace period has passed
                        recovery_start = self.recovering_agents[agent_id]
                        if (current_time - recovery_start).total_seconds() >= self.recovery_grace_period:
                            recovered_agents.append(agent_id)
                else:
                    # Agent is still unhealthy, cancel recovery
                    if agent_id in self.recovering_agents:
                        del self.recovering_agents[agent_id]
                        logger.info(f"Agent {agent_id} recovery cancelled - still unhealthy")
            
            # Mark agents as recovered
            for agent_id in recovered_agents:
                self._mark_agent_recovered(agent_id)
    
    def _mark_agent_recovered(self, agent_id: str) -> None:
        """Mark an agent as recovered"""
        with self.lock:
            self.failed_agents.discard(agent_id)
            self.recovering_agents.pop(agent_id, None)
            self.fault_stats["recovered_agents"] += 1
            logger.info(f"Agent {agent_id} has fully recovered")
    
    def claim_work(self, work_id: str, agent_id: str, work_spec: WorkSpec) -> None:
        """Claim work for an agent with timeout tracking"""
        with self.lock:
            claim_time = datetime.now()
            timeout_time = claim_time + timedelta(seconds=self.execution_timeout)
            
            self.claimed_work[work_id] = {
                "agent_id": agent_id,
                "claim_time": claim_time,
                "timeout": timeout_time,
                "work_spec": work_spec
            }
            self.work_timeouts[work_id] = timeout_time
            
            logger.debug(f"Work {work_id} claimed by {agent_id}, timeout at {timeout_time}")
    
    def complete_work(self, work_id: str, agent_id: str) -> bool:
        """Mark work as completed"""
        with self.lock:
            work_info = self.claimed_work.get(work_id)
            if not work_info:
                logger.warning(f"Work {work_id} not found in claimed work")
                return False
            
            if work_info["agent_id"] != agent_id:
                logger.warning(f"Work {work_id} claimed by {work_info['agent_id']}, not {agent_id}")
                return False
            
            # Remove from tracking
            self.claimed_work.pop(work_id, None)
            self.work_timeouts.pop(work_id, None)
            
            logger.debug(f"Work {work_id} completed by {agent_id}")
            return True
    
    def is_agent_failed(self, agent_id: str) -> bool:
        """Check if an agent is currently marked as failed"""
        with self.lock:
            return agent_id in self.failed_agents
    
    def is_agent_recovering(self, agent_id: str) -> bool:
        """Check if an agent is in recovery grace period"""
        with self.lock:
            return agent_id in self.recovering_agents
    
    def get_agent_failure_count(self, agent_id: str) -> int:
        """Get the number of recent failures for an agent"""
        with self.lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(seconds=self.failure_window)
            
            recent_failures = [
                t for t in self.agent_failures.get(agent_id, [])
                if t > cutoff_time
            ]
            return len(recent_failures)
    
    def set_execution_timeout(self, timeout: float) -> None:
        """Set the execution timeout for claimed work"""
        with self.lock:
            self.execution_timeout = timeout
            logger.info(f"Execution timeout set to {timeout} seconds")
    
    def force_agent_recovery(self, agent_id: str) -> bool:
        """Force an agent to be marked as recovered (admin function)"""
        with self.lock:
            if agent_id in self.failed_agents:
                self._mark_agent_recovered(agent_id)
                logger.info(f"Agent {agent_id} force-recovered by admin")
                return True
            return False
    
    def get_fault_tolerance_status(self) -> Dict[str, Any]:
        """Get comprehensive fault tolerance status"""
        with self.lock:
            return {
                "fault_stats": self.fault_stats.copy(),
                "failed_agents": list(self.failed_agents),
                "recovering_agents": {
                    agent_id: recovery_time.isoformat()
                    for agent_id, recovery_time in self.recovering_agents.items()
                },
                "claimed_work_count": len(self.claimed_work),
                "pending_timeouts": len(self.work_timeouts),
                "configuration": {
                    "heartbeat_timeout": self.heartbeat_timeout,
                    "execution_timeout": self.execution_timeout,
                    "failure_window": self.failure_window,
                    "max_failures_per_window": self.max_failures_per_window,
                    "recovery_grace_period": self.recovery_grace_period
                }
            }
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get current registry status including fault tolerance and flow control info"""
        with self.lock:
            healthy_agents = sum(1 for agent_id in self.agents 
                               if self._is_agent_healthy(agent_id))
            
            return {
                "total_agents": len(self.agents),
                "healthy_agents": healthy_agents,
                "failed_agents": len(self.failed_agents),
                "recovering_agents": len(self.recovering_agents),
                "total_capabilities": len(self.capabilities),
                "active_bids": len(self.active_bids),
                "claimed_work": len(self.claimed_work),
                "bid_history_size": len(self.bid_history),
                "selection_strategy": self.selection_strategy,
                "fault_tolerance": self.get_fault_tolerance_status(),
                "flow_control": self.get_flow_control_status(),
                "capabilities": {
                    cap: len(agents) for cap, agents in self.capabilities.items()
                }
            }
    
    def get_all_agent_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed state information for all agents (Phase 10: Observability)
        
        Returns:
            Dict mapping agent_id to agent state information
        """
        with self.lock:
            agent_states = {}
            
            for agent_id, agent in self.agents.items():
                # Get basic agent info
                state = {
                    "agent_id": agent_id,
                    "current_load": getattr(agent, 'current_load', 0),
                    "max_capacity": getattr(agent, 'max_capacity', 1),
                    "health_score": self.agent_health.get(agent_id, 1.0),
                    "last_heartbeat": self.last_heartbeat.get(agent_id),
                    "last_activity": datetime.now(),  # Updated by registry
                }
                
                # Get flow control status
                if hasattr(agent, 'flow_status'):
                    state["flow_status"] = agent.flow_status.value if hasattr(agent.flow_status, 'value') else str(agent.flow_status)
                else:
                    state["flow_status"] = "available"
                
                # Get current work if any
                current_work = None
                for work_id, work_info in self.claimed_work.items():
                    if work_info.get("agent_id") == agent_id:
                        current_work = {
                            "work_id": work_id,
                            "capability": work_info.get("work_spec", {}).get("capability"),
                            "correlation_id": work_info.get("work_spec", {}).get("correlation_id"),
                            "start_time": work_info.get("claim_time"),
                            "estimated_duration": 30.0  # Default estimate
                        }
                        break
                
                if current_work:
                    state["current_work"] = current_work
                
                # Get agent-specific attributes
                if hasattr(agent, 'execution_history'):
                    recent_executions = list(agent.execution_history)[-5:]  # Last 5 executions
                    state["recent_executions"] = recent_executions
                
                if hasattr(agent, 'success_count'):
                    state["success_count"] = agent.success_count
                    state["failure_count"] = getattr(agent, 'failure_count', 0)
                    total_executions = state["success_count"] + state["failure_count"]
                    if total_executions > 0:
                        state["success_rate"] = state["success_count"] / total_executions
                
                # Agent contract info
                if agent_id in self.contracts:
                    contract = self.contracts[agent_id]
                    state["capabilities"] = list(contract.capabilities.keys())
                    state["agent_type"] = contract.agent_type
                
                # Failure and recovery info
                state["is_failed"] = agent_id in self.failed_agents
                state["is_recovering"] = agent_id in self.recovering_agents
                state["recent_failures"] = len(self.agent_failures.get(agent_id, []))
                
                # Capacity info
                if agent_id in self.agent_capacity:
                    capacity_info = self.agent_capacity[agent_id]
                    state["capacity_level"] = capacity_info.capacity_level.value if hasattr(capacity_info.capacity_level, 'value') else str(capacity_info.capacity_level)
                    state["available_slots"] = capacity_info.available_slots
                    state["throttle_factor"] = getattr(capacity_info, 'throttle_factor', 1.0)
                
                agent_states[agent_id] = state
            
            return agent_states
    
    # ===== PHASE 8: BACK-PRESSURE & FLOW CONTROL METHODS =====
    
    def _find_available_agents(self, capability: str, constraints: Dict[str, Any] = None) -> List['Agent']:
        """Find agents that are both capable and available (considering flow control)"""
        capable_agents = self.find_capable_agents(capability, constraints)
        
        if not self.flow_control_enabled:
            return capable_agents
        
        available_agents = []
        for agent in capable_agents:
            if self._can_agent_accept_work(agent):
                available_agents.append(agent)
            else:
                logger.debug(f"Agent {agent.agent_id} filtered out by flow control")
        
        return available_agents
    
    def _can_agent_accept_work(self, agent: 'Agent') -> bool:
        """Check if agent can accept work based on flow control status"""
        if not self.flow_control_enabled:
            return True
        
        # Check if agent is in overloaded or unavailable state
        if agent.agent_id in self.overloaded_agents:
            return False
        
        # Check agent's own flow control status
        if hasattr(agent, '_can_accept_work'):
            return agent._can_accept_work()
        
        # Fallback to basic capacity check
        return agent.current_load < agent.max_capacity
    
    def _is_system_overloaded(self) -> bool:
        """Check if the entire system is overloaded"""
        if not self.agents:
            return False
        
        total_capacity = 0
        total_load = 0
        
        for agent in self.agents.values():
            if self._is_agent_healthy(agent.agent_id):
                total_capacity += agent.max_capacity
                total_load += agent.current_load
        
        if total_capacity == 0:
            return True
        
        system_utilization = total_load / total_capacity
        return system_utilization >= self.system_load_threshold
    
    def _select_winner_with_flow_control(self, bids: List[Bid]) -> Optional[Bid]:
        """Select winning bid considering flow control factors"""
        if not bids:
            return None
        
        # Filter out bids from overloaded agents
        available_bids = []
        for bid in bids:
            if bid.agent_id not in self.overloaded_agents:
                # Check additional flow control info in bid
                additional_info = bid.additional_info or {}
                flow_status = additional_info.get("flow_status", "available")
                if flow_status != "overloaded":
                    available_bids.append(bid)
        
        if not available_bids:
            logger.warning("All bidding agents are overloaded, falling back to original bids")
            available_bids = bids
        
        # Apply original selection strategy to available bids
        return self._select_winner(available_bids)
    
    def _update_agent_capacity(self, agent_id: str) -> None:
        """Update capacity tracking for an agent"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        
        # Get current capacity info from agent
        if hasattr(agent, 'get_capacity_info'):
            capacity_info = agent.get_capacity_info()
            self.agent_capacity[agent_id] = capacity_info
            
            # Update flow control tracking
            if capacity_info.flow_status == FlowControlStatus.OVERLOADED:
                self.overloaded_agents.add(agent_id)
                self.throttled_agents.discard(agent_id)
                self.flow_stats["overload_events"] += 1
            elif capacity_info.flow_status == FlowControlStatus.THROTTLED:
                self.throttled_agents.add(agent_id)
                self.overloaded_agents.discard(agent_id)
                self.flow_stats["throttle_events"] += 1
            else:
                self.overloaded_agents.discard(agent_id)
                self.throttled_agents.discard(agent_id)
        
        # Update system overload status
        was_overloaded = self.system_overload_mode
        self.system_overload_mode = self._is_system_overloaded()
        
        if was_overloaded and not self.system_overload_mode:
            logger.info("System no longer overloaded - resuming normal operations")
        elif not was_overloaded and self.system_overload_mode:
            logger.warning("System is now overloaded - activating back-pressure")
    
    def handle_flow_control_event(self, event_type: str, agent_id: str, event_data: Dict[str, Any]) -> None:
        """Handle flow control events from agents"""
        logger.info(f"Handling flow control event: {event_type} from {agent_id}")
        
        if event_type == "agent_overloaded":
            self.overloaded_agents.add(agent_id)
            self.throttled_agents.discard(agent_id)
            self.flow_stats["overload_events"] += 1
            
            # Optionally redistribute work from this agent
            self._consider_work_redistribution(agent_id)
            
        elif event_type == "agent_available":
            self.overloaded_agents.discard(agent_id)
            self.throttled_agents.discard(agent_id)
            
            # Agent is now available for work
            logger.info(f"Agent {agent_id} is now available for work")
            
        elif event_type == "capacity_changed":
            self.flow_stats["capacity_adjustments"] += 1
            self._update_agent_capacity(agent_id)
            
        elif event_type == "capacity_critical":
            # Agent is approaching overload
            if agent_id not in self.overloaded_agents:
                self.throttled_agents.add(agent_id)
    
    def _consider_work_redistribution(self, overloaded_agent_id: str) -> None:
        """Consider redistributing work from an overloaded agent"""
        # This is a placeholder for work redistribution logic
        # In a full implementation, this would:
        # 1. Find work currently assigned to the overloaded agent
        # 2. Find alternative agents with capacity
        # 3. Reassign non-critical work to other agents
        logger.debug(f"Considering work redistribution from overloaded agent {overloaded_agent_id}")
    
    def get_flow_control_status(self) -> Dict[str, Any]:
        """Get current flow control status"""
        with self.lock:
            return {
                "flow_control_enabled": self.flow_control_enabled,
                "system_overload_mode": self.system_overload_mode,
                "system_load_threshold": self.system_load_threshold,
                "overloaded_agents": list(self.overloaded_agents),
                "throttled_agents": list(self.throttled_agents),
                "agent_capacity_info": {
                    agent_id: info.to_dict() 
                    for agent_id, info in self.agent_capacity.items()
                },
                "flow_stats": self.flow_stats.copy()
            }
    
    def enable_flow_control(self, enabled: bool = True) -> None:
        """Enable or disable flow control globally"""
        with self.lock:
            self.flow_control_enabled = enabled
            if enabled:
                logger.info("Flow control enabled globally")
            else:
                logger.info("Flow control disabled globally")
                # Clear flow control state
                self.overloaded_agents.clear()
                self.throttled_agents.clear()
                self.system_overload_mode = False
    
    def set_system_load_threshold(self, threshold: float) -> None:
        """Set the system-wide load threshold for overload detection"""
        with self.lock:
            self.system_load_threshold = max(0.1, min(1.0, threshold))
            logger.info(f"System load threshold set to {self.system_load_threshold:.1%}")
    
    def get_system_capacity_summary(self) -> Dict[str, Any]:
        """Get a summary of system-wide capacity"""
        with self.lock:
            total_capacity = 0
            total_load = 0
            available_agents = 0
            overloaded_agents = 0
            
            for agent in self.agents.values():
                if self._is_agent_healthy(agent.agent_id):
                    total_capacity += agent.max_capacity
                    total_load += agent.current_load
                    
                    if agent.agent_id in self.overloaded_agents:
                        overloaded_agents += 1
                    else:
                        available_agents += 1
            
            utilization = (total_load / total_capacity) if total_capacity > 0 else 0.0
            
            return {
                "total_capacity": total_capacity,
                "total_load": total_load,
                "utilization": utilization,
                "available_capacity": total_capacity - total_load,
                "healthy_agents": len(self.agents) - len(self.failed_agents),
                "available_agents": available_agents,
                "overloaded_agents": overloaded_agents,
                "system_overloaded": self.system_overload_mode,
                "flow_control_active": self.flow_control_enabled
            }
    
    # ===== PHASE 9B: PREDICTIVE SCHEDULING METHODS =====
    
    def track_capability_sequence(self, correlation_id: str, capability: str) -> None:
        """Track capability execution sequence for pattern learning"""
        if not (PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B and self.predictive_enabled):
            return
        
        with self.lock:
            if correlation_id not in self.capability_sequences:
                self.capability_sequences[correlation_id] = []
            
            sequence = self.capability_sequences[correlation_id]
            
            # Add to sequence
            sequence.append(capability)
            
            # Update transition patterns if we have a previous capability
            if len(sequence) >= 2:
                prev_capability = sequence[-2]
                self.transition_patterns[prev_capability][capability] += 1.0
                
                # Normalize probabilities periodically
                if sum(self.transition_patterns[prev_capability].values()) > 100:
                    self._normalize_transition_patterns(prev_capability)
            
            # Limit sequence length to manage memory
            if len(sequence) > 20:
                sequence[:] = sequence[-15:]  # Keep last 15
            
            logger.debug(f"Tracked capability sequence for {correlation_id}: {capability}")
    
    def _normalize_transition_patterns(self, from_capability: str) -> None:
        """Normalize transition patterns to maintain probability distribution"""
        patterns = self.transition_patterns[from_capability]
        total = sum(patterns.values())
        
        if total > 0:
            # Normalize to probabilities and apply decay
            for to_capability in patterns:
                patterns[to_capability] = (patterns[to_capability] / total) * 0.9  # Decay factor
    
    def predict_next_capabilities(self, correlation_id: str, current_capability: str) -> List[Tuple[str, float]]:
        """
        Predict next likely capabilities with confidence scores
        
        Returns:
            List of (capability, confidence) tuples sorted by confidence
        """
        if not (PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B and self.predictive_enabled):
            return []
        
        predictions = []
        
        with self.lock:
            # Use hot paths from performance hints
            hot_path = self.hot_paths.get(current_capability, [])
            for next_cap in hot_path:
                predictions.append((next_cap, 0.8))  # High confidence for configured hot paths
            
            # Use learned transition patterns
            patterns = self.transition_patterns.get(current_capability, {})
            for next_cap, probability in patterns.items():
                # Don't duplicate hot path predictions
                if next_cap not in [pred[0] for pred in predictions]:
                    predictions.append((next_cap, min(probability, 0.7)))  # Cap at 0.7 for learned patterns
            
            # Use prefetch rules
            for trigger, next_capabilities in self.prefetch_rules.items():
                if trigger == current_capability:
                    for next_cap in next_capabilities:
                        if next_cap not in [pred[0] for pred in predictions]:
                            predictions.append((next_cap, 0.6))  # Medium confidence for prefetch rules
        
        # Sort by confidence and return top predictions
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:5]  # Top 5 predictions
    
    def generate_soft_bids(self, correlation_id: str, predicted_capabilities: List[Tuple[str, float]]) -> None:
        """Generate soft bids for predicted capabilities"""
        if not (PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B and self.predictive_enabled):
            return
        
        soft_bids = []
        
        for capability, confidence in predicted_capabilities:
            if confidence >= self.soft_bid_threshold:
                # Find capable agents for this capability
                capable_agents = self.find_capable_agents(capability)
                
                for agent in capable_agents:
                    if self._is_agent_healthy(agent.agent_id) and agent.current_load < agent.max_capacity:
                        # Generate soft bid
                        soft_bid = {
                            "agent_id": agent.agent_id,
                            "capability": capability,
                            "confidence": confidence * 0.5,  # Reduce confidence for soft bids
                            "estimated_time": getattr(agent.contract.capabilities.get(capability), 'cost_estimate', 30.0),
                            "soft_bid": True,
                            "timestamp": time.time()
                        }
                        soft_bids.append(soft_bid)
        
        if soft_bids:
            with self.lock:
                if correlation_id not in self.soft_bids:
                    self.soft_bids[correlation_id] = []
                self.soft_bids[correlation_id].extend(soft_bids)
                self.cross_agent_stats["soft_bids_generated"] += len(soft_bids)
            
            logger.debug(f"Generated {len(soft_bids)} soft bids for {correlation_id}")
    
    def get_soft_bids(self, correlation_id: str, capability: str) -> List[Dict[str, Any]]:
        """Get existing soft bids for a capability"""
        if not (PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B and self.predictive_enabled):
            return []
        
        with self.lock:
            soft_bids = self.soft_bids.get(correlation_id, [])
            return [bid for bid in soft_bids if bid["capability"] == capability]
    
    def trigger_prefetch(self, correlation_id: str, capability: str) -> None:
        """Trigger prefetching for a capability"""
        if not (PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B and self.predictive_enabled):
            return
        
        # Check if prefetch is beneficial based on cache hit prediction
        if self._should_prefetch(capability):
            with self.lock:
                if correlation_id not in self.prefetch_requests:
                    self.prefetch_requests[correlation_id] = {}
                
                self.prefetch_requests[correlation_id][capability] = {
                    "timestamp": time.time(),
                    "status": "requested"
                }
            
            logger.debug(f"Triggered prefetch for {capability} in {correlation_id}")
    
    def _should_prefetch(self, capability: str) -> bool:
        """Determine if prefetching is beneficial for a capability"""
        # Simple heuristic: prefetch if capability is in hot paths or frequently used
        return (capability in self.hot_paths or 
                sum(patterns.get(capability, 0) for patterns in self.transition_patterns.values()) > 5)
    
    def get_phase9b_stats(self) -> Dict[str, Any]:
        """Get Phase 9B specific statistics"""
        if not (PHASE_9B_AVAILABLE and Config.ENABLE_OPT_PHASE9B):
            return {"enabled": False}
        
        with self.lock:
            return {
                "enabled": True,
                "predictive_enabled": self.predictive_enabled,
                "learned_transitions": len(self.transition_patterns),
                "hot_paths_loaded": len(self.hot_paths),
                "prefetch_rules_loaded": len(self.prefetch_rules),
                "active_soft_bids": sum(len(bids) for bids in self.soft_bids.values()),
                "prefetch_requests": sum(len(reqs) for reqs in self.prefetch_requests.values()),
                "cross_agent_stats": self.cross_agent_stats.copy()
            }


