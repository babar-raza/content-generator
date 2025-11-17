import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket, ConnectionStatus } from './useWebSocket';
import { AgentStatus } from '@/types/monitoring';

interface AgentWebSocketData {
  type: string;
  data: any;
  timestamp: string;
}

interface AgentExecution {
  agent_id: string;
  status: string;
  timestamp: string;
  duration_ms?: number;
  error?: string;
}

interface UseAgentWebSocketOptions {
  onAgentUpdate?: (update: AgentWebSocketData) => void;
  enabled?: boolean;
  fallbackPolling?: boolean;
  pollingInterval?: number;
}

interface UseAgentWebSocketReturn {
  agents: AgentStatus[];
  executions: AgentExecution[];
  status: ConnectionStatus;
  error: string | null;
  send: (data: any) => void;
  reconnect: () => void;
}

export function useAgentWebSocket(
  options: UseAgentWebSocketOptions = {}
): UseAgentWebSocketReturn {
  const {
    onAgentUpdate,
    enabled = true,
    fallbackPolling = true,
    pollingInterval = 10000,
  } = options;

  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [shouldPoll, setShouldPoll] = useState(false);
  const pollingTimerRef = useRef<number | null>(null);

  const handleMessage = useCallback((data: AgentWebSocketData) => {
    console.log('Agent WebSocket message:', data);

    if (data.type === 'agent.status' && Array.isArray(data.data)) {
      setAgents(data.data);
    } else if (data.type === 'agent.started') {
      // Track execution start
      const execution: AgentExecution = {
        agent_id: data.data.agent_id,
        status: 'running',
        timestamp: data.timestamp,
      };
      setExecutions((prev) => [execution, ...prev].slice(0, 100)); // Keep last 100

      // Update agent status
      setAgents((prev) =>
        prev.map((agent) =>
          agent.agent_id === data.data.agent_id
            ? { ...agent, status: 'busy' as const }
            : agent
        )
      );
    } else if (data.type === 'agent.completed') {
      // Track execution completion
      setExecutions((prev) =>
        prev.map((exec) =>
          exec.agent_id === data.data.agent_id &&
          exec.status === 'running'
            ? {
                ...exec,
                status: 'completed',
                duration_ms: data.data.duration_ms,
              }
            : exec
        )
      );

      // Update agent status and metrics
      setAgents((prev) =>
        prev.map((agent) =>
          agent.agent_id === data.data.agent_id
            ? {
                ...agent,
                status: 'available' as const,
                last_execution: data.timestamp,
                total_executions: (agent.total_executions || 0) + 1,
                avg_latency_ms: data.data.duration_ms || agent.avg_latency_ms,
              }
            : agent
        )
      );
    } else if (data.type === 'agent.failed') {
      // Track execution failure
      setExecutions((prev) =>
        prev.map((exec) =>
          exec.agent_id === data.data.agent_id &&
          exec.status === 'running'
            ? {
                ...exec,
                status: 'failed',
                error: data.data.error,
                duration_ms: data.data.duration_ms,
              }
            : exec
        )
      );

      // Update agent status
      setAgents((prev) =>
        prev.map((agent) =>
          agent.agent_id === data.data.agent_id
            ? {
                ...agent,
                status: 'error' as const,
                last_execution: data.timestamp,
              }
            : agent
        )
      );
    }

    onAgentUpdate?.(data);
  }, [onAgentUpdate]);

  const {
    data,
    status,
    error,
    send,
    reconnect,
  } = useWebSocket<AgentWebSocketData>({
    url: '/ws/agents',
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

    const pollAgentStatuses = async () => {
      try {
        const response = await fetch('/api/monitoring/agents');
        if (response.ok) {
          const data = await response.json();
          setAgents(data);
        }
      } catch (err) {
        console.error('Agent polling failed:', err);
      }
    };

    // Initial poll
    pollAgentStatuses();

    // Set up interval
    pollingTimerRef.current = window.setInterval(pollAgentStatuses, pollingInterval);

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [shouldPoll, pollingInterval]);

  // Request initial agent list when connected
  useEffect(() => {
    if (status === 'connected') {
      send({ type: 'get_agents' });
    }
  }, [status, send]);

  return {
    agents,
    executions,
    status: shouldPoll ? 'disconnected' : status,
    error,
    send,
    reconnect,
  };
}

export default useAgentWebSocket;
