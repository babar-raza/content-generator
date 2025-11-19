"""Flow Analysis API routes.

Provides endpoints for monitoring agent data flows and detecting bottlenecks.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..models import (
    FlowEvent,
    BottleneckReport,
    ActiveFlow,
    FlowRealtimeResponse,
    FlowHistoryResponse,
    BottleneckResponse,
    ActiveFlowsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flows", tags=["flows"])


# This will be injected by the app
_flow_monitor = None


def set_flow_monitor(monitor):
    """Set the flow monitor for dependency injection."""
    global _flow_monitor
    _flow_monitor = monitor


def get_flow_monitor():
    """Dependency to get flow monitor."""
    if _flow_monitor is None:
        # Try to import and get the global instance
        try:
            from src.visualization.agent_flow_monitor import get_flow_monitor
            return get_flow_monitor()
        except Exception as e:
            logger.error(f"Failed to get flow monitor: {e}")
            raise HTTPException(status_code=503, detail="Flow monitor not initialized")
    return _flow_monitor


@router.get("/realtime", response_model=FlowRealtimeResponse)
async def get_realtime_flows(
    window: int = Query(default=60, ge=1, le=3600, description="Time window in seconds")
):
    """Get active flows in the last N seconds.
    
    Args:
        window: Time window in seconds (default 60, max 3600)
        
    Returns:
        FlowRealtimeResponse with flows from the last N seconds
    """
    try:
        monitor = get_flow_monitor()
        
        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=window)
        
        # Get all active flows
        all_flows = monitor.get_active_flows()
        
        # Filter flows within time window
        recent_flows = []
        for flow in all_flows:
            flow_dict = flow.to_dict() if hasattr(flow, 'to_dict') else flow
            
            # Parse timestamp
            timestamp_str = flow_dict.get('timestamp')
            if timestamp_str:
                try:
                    flow_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    if flow_time >= cutoff_time:
                        recent_flows.append(FlowEvent(
                            flow_id=flow_dict.get('flow_id', ''),
                            source_agent=flow_dict.get('source_agent', ''),
                            target_agent=flow_dict.get('target_agent', ''),
                            event_type=flow_dict.get('event_type', ''),
                            timestamp=timestamp_str,
                            correlation_id=flow_dict.get('correlation_id', ''),
                            status=flow_dict.get('status', 'active'),
                            latency_ms=flow_dict.get('latency_ms'),
                            data_size_bytes=flow_dict.get('data_size_bytes'),
                            metadata=flow_dict.get('metadata', {})
                        ))
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse flow timestamp: {e}")
                    continue
        
        return FlowRealtimeResponse(
            flows=recent_flows,
            window_seconds=window,
            count=len(recent_flows),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting realtime flows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get realtime flows: {str(e)}")


@router.get("/history/{correlation_id}", response_model=FlowHistoryResponse)
async def get_flow_history(correlation_id: str):
    """Get historical flow data for a specific job/correlation ID.
    
    Args:
        correlation_id: Job ID or workflow execution ID
        
    Returns:
        FlowHistoryResponse with historical flow data
    """
    try:
        monitor = get_flow_monitor()
        
        # Get flow history for correlation ID
        flows = monitor.get_flows_by_correlation(correlation_id)
        
        if not flows:
            return FlowHistoryResponse(
                correlation_id=correlation_id,
                flows=[],
                total_flows=0,
                start_time=None,
                end_time=None,
                total_duration_ms=None
            )
        
        # Convert to FlowEvent objects
        flow_events = []
        timestamps = []
        
        for flow in flows:
            flow_dict = flow.to_dict() if hasattr(flow, 'to_dict') else flow
            timestamp_str = flow_dict.get('timestamp')
            
            if timestamp_str:
                timestamps.append(timestamp_str)
                
            flow_events.append(FlowEvent(
                flow_id=flow_dict.get('flow_id', ''),
                source_agent=flow_dict.get('source_agent', ''),
                target_agent=flow_dict.get('target_agent', ''),
                event_type=flow_dict.get('event_type', ''),
                timestamp=timestamp_str,
                correlation_id=flow_dict.get('correlation_id', ''),
                status=flow_dict.get('status', 'active'),
                latency_ms=flow_dict.get('latency_ms'),
                data_size_bytes=flow_dict.get('data_size_bytes'),
                metadata=flow_dict.get('metadata', {})
            ))
        
        # Calculate total duration
        total_duration_ms = None
        start_time = None
        end_time = None
        
        if timestamps:
            start_time = min(timestamps)
            end_time = max(timestamps)
            
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                total_duration_ms = (end_dt - start_dt).total_seconds() * 1000
            except (ValueError, AttributeError):
                pass
        
        return FlowHistoryResponse(
            correlation_id=correlation_id,
            flows=flow_events,
            total_flows=len(flow_events),
            start_time=start_time,
            end_time=end_time,
            total_duration_ms=total_duration_ms
        )
        
    except Exception as e:
        logger.error(f"Error getting flow history for {correlation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get flow history: {str(e)}")


@router.get("/bottlenecks", response_model=BottleneckResponse)
async def get_bottlenecks(
    threshold_ms: float = Query(default=1000, ge=0, description="Latency threshold in milliseconds")
):
    """Detect slow agents and stages (bottlenecks).
    
    Args:
        threshold_ms: Latency threshold in milliseconds (default 1000)
        
    Returns:
        BottleneckResponse with detected bottlenecks
    """
    try:
        monitor = get_flow_monitor()
        
        # Detect bottlenecks
        bottlenecks = monitor.detect_bottlenecks(threshold_ms=threshold_ms)
        
        # Convert to BottleneckReport objects
        bottleneck_reports = []
        
        for bottleneck in bottlenecks:
            bottleneck_dict = bottleneck.to_dict() if hasattr(bottleneck, 'to_dict') else bottleneck
            
            bottleneck_reports.append(BottleneckReport(
                agent_id=bottleneck_dict.get('agent_id', ''),
                avg_latency_ms=bottleneck_dict.get('avg_latency_ms', 0),
                max_latency_ms=bottleneck_dict.get('max_latency_ms', 0),
                flow_count=bottleneck_dict.get('flow_count', 0),
                severity=bottleneck_dict.get('severity', 'low'),
                timestamp=bottleneck_dict.get('timestamp', datetime.now(timezone.utc).isoformat())
            ))
        
        return BottleneckResponse(
            bottlenecks=bottleneck_reports,
            threshold_ms=threshold_ms,
            count=len(bottleneck_reports),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error detecting bottlenecks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to detect bottlenecks: {str(e)}")


@router.get("/active", response_model=ActiveFlowsResponse)
async def get_active_flows():
    """Get currently executing flows.
    
    Returns:
        ActiveFlowsResponse with currently active flows
    """
    try:
        monitor = get_flow_monitor()
        
        # Get active flows
        flows = monitor.get_active_flows()
        
        # Convert to ActiveFlow objects
        active_flows = []
        
        for flow in flows:
            flow_dict = flow.to_dict() if hasattr(flow, 'to_dict') else flow
            
            # Only include flows with active status
            if flow_dict.get('status') == 'active':
                active_flows.append(ActiveFlow(
                    flow_id=flow_dict.get('flow_id', ''),
                    correlation_id=flow_dict.get('correlation_id', ''),
                    source_agent=flow_dict.get('source_agent', ''),
                    target_agent=flow_dict.get('target_agent', ''),
                    event_type=flow_dict.get('event_type', ''),
                    started_at=flow_dict.get('timestamp'),
                    current_duration_ms=flow_dict.get('latency_ms')
                ))
        
        return ActiveFlowsResponse(
            active_flows=active_flows,
            count=len(active_flows),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting active flows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active flows: {str(e)}")
