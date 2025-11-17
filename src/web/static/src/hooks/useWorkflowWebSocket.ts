import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket, ConnectionStatus } from './useWebSocket';
import { FlowEvent } from '@/types/monitoring';

interface WorkflowWebSocketData {
  type: string;
  data: any;
  timestamp: string;
}

interface WorkflowState {
  workflow_id?: string;
  status?: string;
  nodes?: Record<string, any>;
  edges?: any[];
}

interface WorkflowGraphUpdate {
  nodes: any[];
  edges: any[];
  active_nodes?: string[];
}

interface UseWorkflowWebSocketOptions {
  onWorkflowUpdate?: (update: WorkflowWebSocketData) => void;
  enabled?: boolean;
  fallbackPolling?: boolean;
  pollingInterval?: number;
}

interface UseWorkflowWebSocketReturn {
  workflowState: WorkflowState | null;
  graphData: WorkflowGraphUpdate | null;
  agentExecutions: FlowEvent[];
  status: ConnectionStatus;
  error: string | null;
  send: (data: any) => void;
  reconnect: () => void;
}

export function useWorkflowWebSocket(
  options: UseWorkflowWebSocketOptions = {}
): UseWorkflowWebSocketReturn {
  const {
    onWorkflowUpdate,
    enabled = true,
    fallbackPolling = true,
    pollingInterval = 5000,
  } = options;

  const [workflowState, setWorkflowState] = useState<WorkflowState | null>(null);
  const [graphData, setGraphData] = useState<WorkflowGraphUpdate | null>(null);
  const [agentExecutions, setAgentExecutions] = useState<FlowEvent[]>([]);
  const [shouldPoll, setShouldPoll] = useState(false);
  const pollingTimerRef = useRef<number | null>(null);

  const handleMessage = useCallback((data: WorkflowWebSocketData) => {
    console.log('Workflow WebSocket message:', data);

    switch (data.type) {
      case 'workflow.state':
        setWorkflowState(data.data);
        break;

      case 'workflow.graph':
        setGraphData(data.data);
        break;

      case 'agent.execution':
        // Track agent execution for visualization
        const flowEvent: FlowEvent = {
          flow_id: data.data.flow_id || `${data.data.source_agent}-${data.data.target_agent}`,
          source_agent: data.data.source_agent,
          target_agent: data.data.target_agent,
          event_type: data.data.event_type || 'execution',
          timestamp: data.timestamp,
          correlation_id: data.data.correlation_id || '',
          status: data.data.status || 'unknown',
          latency_ms: data.data.latency_ms,
          data_size_bytes: data.data.data_size_bytes,
          metadata: data.data.metadata,
        };
        
        setAgentExecutions((prev) => [flowEvent, ...prev].slice(0, 100)); // Keep last 100

        // Update active nodes in graph
        if (data.data.status === 'running' || data.data.status === 'started') {
          setGraphData((prev) => {
            if (!prev) return prev;
            const activeNodes = new Set(prev.active_nodes || []);
            activeNodes.add(data.data.source_agent);
            return {
              ...prev,
              active_nodes: Array.from(activeNodes),
            };
          });
        } else if (data.data.status === 'completed' || data.data.status === 'failed') {
          setGraphData((prev) => {
            if (!prev) return prev;
            const activeNodes = new Set(prev.active_nodes || []);
            activeNodes.delete(data.data.source_agent);
            return {
              ...prev,
              active_nodes: Array.from(activeNodes),
            };
          });
        }
        break;

      case 'workflow.node.start':
        setGraphData((prev) => {
          if (!prev) return prev;
          const activeNodes = new Set(prev.active_nodes || []);
          activeNodes.add(data.data.node_id);
          return {
            ...prev,
            active_nodes: Array.from(activeNodes),
          };
        });
        break;

      case 'workflow.node.complete':
      case 'workflow.node.fail':
        setGraphData((prev) => {
          if (!prev) return prev;
          const activeNodes = new Set(prev.active_nodes || []);
          activeNodes.delete(data.data.node_id);
          return {
            ...prev,
            active_nodes: Array.from(activeNodes),
          };
        });
        break;
    }

    onWorkflowUpdate?.(data);
  }, [onWorkflowUpdate]);

  const {
    data,
    status,
    error,
    send,
    reconnect,
  } = useWebSocket<WorkflowWebSocketData>({
    url: '/ws/visual',
    onMessage: handleMessage,
    enabled,
    reconnectAttempts: 5,
    reconnectDelay: 1000,
  });

  // Fallback polling when WebSocket fails
  useEffect(() => {
    if (!fallbackPolling) return;

    if (status === 'error' && error?.includes('Max reconnection')) {
      setShouldPoll(true);
    } else if (status === 'connected') {
      setShouldPoll(false);
    }
  }, [status, error, fallbackPolling]);

  // Polling implementation
  useEffect(() => {
    if (!shouldPoll) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    const pollWorkflowData = async () => {
      try {
        const response = await fetch('/api/monitoring/flows/realtime?window_seconds=60');
        if (response.ok) {
          const data = await response.json();
          if (data.flows) {
            setAgentExecutions(data.flows);
          }
        }
      } catch (err) {
        console.error('Workflow polling failed:', err);
      }
    };

    // Initial poll
    pollWorkflowData();

    // Set up interval
    pollingTimerRef.current = window.setInterval(pollWorkflowData, pollingInterval);

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [shouldPoll, pollingInterval]);

  // Request initial workflows when connected
  useEffect(() => {
    if (status === 'connected') {
      send({ type: 'get_workflows' });
    }
  }, [status, send]);

  return {
    workflowState,
    graphData,
    agentExecutions,
    status: shouldPoll ? 'disconnected' : status,
    error,
    send,
    reconnect,
  };
}

export default useWorkflowWebSocket;
