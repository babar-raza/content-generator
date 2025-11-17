import React, { useState, useEffect, useCallback } from 'react';
import { useWebSocket, LiveFlowMessage } from '@/websocket/liveFlow';
import { AgentStatusIndicator, AgentStatus } from './AgentStatusIndicator';
import { DataFlowContainer } from './DataFlowAnimation';

interface Node {
  id: string;
  position: { x: number; y: number };
  data: {
    label: string;
    status: AgentStatus;
    duration?: number;
  };
}

interface DataFlow {
  id: string;
  fromNode: { position: { x: number; y: number }; id: string } | undefined;
  toNode: { position: { x: number; y: number }; id: string } | undefined;
}

interface LiveWorkflowCanvasProps {
  jobId: string;
  workflowSteps?: string[];
}

export const LiveWorkflowCanvas: React.FC<LiveWorkflowCanvasProps> = ({
  jobId,
  workflowSteps = []
}) => {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [completedAgents, setCompletedAgents] = useState<Set<string>>(new Set());
  const [failedAgents, setFailedAgents] = useState<Set<string>>(new Set());
  const [agentDurations, setAgentDurations] = useState<Map<string, number>>(new Map());
  const [dataFlows, setDataFlows] = useState<DataFlow[]>([]);

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const wsUrl = `${protocol}//${host}/ws/live-flow/${jobId}`;

  const { socket, isConnected, lastMessage } = useWebSocket(wsUrl);

  // Initialize nodes from workflow steps
  useEffect(() => {
    if (workflowSteps.length > 0) {
      const initialNodes: Node[] = workflowSteps.map((step, index) => ({
        id: step,
        position: {
          x: 50,
          y: index * 120
        },
        data: {
          label: step,
          status: 'pending' as AgentStatus
        }
      }));
      setNodes(initialNodes);
    }
  }, [workflowSteps]);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'agent_started':
        if (lastMessage.agent_id) {
          setActiveAgent(lastMessage.agent_id);
          updateNodeStatus(lastMessage.agent_id, 'running');
        }
        break;

      case 'agent_completed':
        if (lastMessage.agent_id) {
          setActiveAgent(null);
          setCompletedAgents(prev => new Set([...prev, lastMessage.agent_id!]));
          updateNodeStatus(lastMessage.agent_id, 'completed', lastMessage.duration);
          
          if (lastMessage.duration) {
            setAgentDurations(prev => new Map(prev).set(lastMessage.agent_id!, lastMessage.duration!));
          }
        }
        break;

      case 'agent_failed':
        if (lastMessage.agent_id) {
          setActiveAgent(null);
          setFailedAgents(prev => new Set([...prev, lastMessage.agent_id!]));
          updateNodeStatus(lastMessage.agent_id, 'failed');
        }
        break;

      case 'data_flow':
        if (lastMessage.from_agent && lastMessage.to_agent) {
          animateDataFlow(lastMessage.from_agent, lastMessage.to_agent);
        }
        break;
    }
  }, [lastMessage]);

  const updateNodeStatus = (
    nodeId: string,
    status: AgentStatus,
    duration?: number
  ) => {
    setNodes(prevNodes =>
      prevNodes.map(node => {
        if (node.id === nodeId) {
          return {
            ...node,
            data: {
              ...node.data,
              status,
              duration
            }
          };
        }
        return node;
      })
    );
  };

  const animateDataFlow = (fromId: string, toId: string) => {
    const fromNode = nodes.find(n => n.id === fromId);
    const toNode = nodes.find(n => n.id === toId);

    if (!fromNode || !toNode) return;

    const flow: DataFlow = {
      id: `${fromId}-${toId}-${Date.now()}`,
      fromNode: { ...fromNode, position: fromNode.position },
      toNode: { ...toNode, position: toNode.position }
    };

    setDataFlows(prev => [...prev, flow]);
  };

  const handleFlowComplete = useCallback((flowId: string) => {
    setDataFlows(prev => prev.filter(f => f.id !== flowId));
  }, []);

  const getConnectionColor = (status: AgentStatus) => {
    switch (status) {
      case 'completed':
        return 'stroke-green-500';
      case 'failed':
        return 'stroke-red-500';
      case 'running':
        return 'stroke-blue-500';
      default:
        return 'stroke-gray-300';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Connection Status */}
      <div className="bg-gray-50 border-b px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <div className="text-sm text-gray-600">
          Job: {jobId}
        </div>
      </div>

      {/* Workflow Canvas */}
      <div className="relative p-6" style={{ minHeight: '600px' }}>
        {/* Nodes */}
        <div className="space-y-4">
          {nodes.map((node, index) => (
            <div key={node.id}>
              {/* Node */}
              <div
                style={{
                  position: 'absolute',
                  left: node.position.x,
                  top: node.position.y
                }}
              >
                <AgentStatusIndicator
                  status={node.data.status}
                  agentId={node.data.label}
                  duration={node.data.duration}
                />
              </div>

              {/* Connection line to next node */}
              {index < nodes.length - 1 && (
                <svg
                  style={{
                    position: 'absolute',
                    left: node.position.x + 100,
                    top: node.position.y + 40,
                    overflow: 'visible',
                    pointerEvents: 'none'
                  }}
                  width="2"
                  height="80"
                >
                  <line
                    x1="1"
                    y1="0"
                    x2="1"
                    y2="80"
                    className={getConnectionColor(node.data.status)}
                    strokeWidth="2"
                  />
                </svg>
              )}
            </div>
          ))}
        </div>

        {/* Data Flow Animations */}
        <DataFlowContainer 
          flows={dataFlows} 
          onFlowComplete={handleFlowComplete}
        />

        {/* Empty state */}
        {nodes.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium">No workflow loaded</p>
              <p className="text-sm mt-1">Waiting for job execution...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
