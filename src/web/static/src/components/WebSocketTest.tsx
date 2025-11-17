import React, { useState } from 'react';
import { useJobWebSocket } from '@/hooks/useJobWebSocket';
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket';
import { useWorkflowWebSocket } from '@/hooks/useWorkflowWebSocket';
import ConnectionStatus from './ConnectionStatus';

/**
 * WebSocketTest component for testing WebSocket connections
 * 
 * Usage:
 * 1. Start the backend server
 * 2. Create a job via API
 * 3. Use this component to monitor WebSocket connections
 */
const WebSocketTest: React.FC = () => {
  const [jobId, setJobId] = useState('');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Job WebSocket
  const {
    jobStatus,
    events: jobEvents,
    status: jobStatus_,
    error: jobError,
    reconnect: jobReconnect,
  } = useJobWebSocket({
    jobId: activeJobId,
    fallbackPolling: true,
  });

  // Agent WebSocket
  const {
    agents,
    executions,
    status: agentStatus,
    error: agentError,
    reconnect: agentReconnect,
  } = useAgentWebSocket({
    enabled: true,
    fallbackPolling: true,
  });

  // Workflow WebSocket
  const {
    workflowState,
    graphData,
    agentExecutions,
    status: workflowStatus,
    error: workflowError,
    reconnect: workflowReconnect,
  } = useWorkflowWebSocket({
    enabled: true,
    fallbackPolling: true,
  });

  const handleConnectToJob = () => {
    if (jobId.trim()) {
      setActiveJobId(jobId.trim());
    }
  };

  const handleDisconnectFromJob = () => {
    setActiveJobId(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg shadow p-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            WebSocket Integration Test
          </h1>
          <p className="text-gray-600">
            Test real-time WebSocket connections for jobs, agents, and workflows
          </p>
        </div>

        {/* Connection Status */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Connection Status
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-700">Job WebSocket</span>
                <ConnectionStatus
                  status={jobStatus_}
                  showLabel={false}
                  onReconnect={jobReconnect}
                />
              </div>
              {jobError && (
                <p className="text-xs text-red-600 mt-2">{jobError}</p>
              )}
              {activeJobId && (
                <p className="text-xs text-gray-600 mt-2">
                  Connected to: {activeJobId}
                </p>
              )}
            </div>

            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-700">Agent WebSocket</span>
                <ConnectionStatus
                  status={agentStatus}
                  showLabel={false}
                  onReconnect={agentReconnect}
                />
              </div>
              {agentError && (
                <p className="text-xs text-red-600 mt-2">{agentError}</p>
              )}
              <p className="text-xs text-gray-600 mt-2">
                Tracking {agents.length} agents
              </p>
            </div>

            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-700">Workflow WebSocket</span>
                <ConnectionStatus
                  status={workflowStatus}
                  showLabel={false}
                  onReconnect={workflowReconnect}
                />
              </div>
              {workflowError && (
                <p className="text-xs text-red-600 mt-2">{workflowError}</p>
              )}
              <p className="text-xs text-gray-600 mt-2">
                {agentExecutions.length} flow events
              </p>
            </div>
          </div>
        </div>

        {/* Job Connection Control */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Job WebSocket Control
          </h2>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Job ID
              </label>
              <input
                type="text"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                placeholder="Enter job ID"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button
              onClick={handleConnectToJob}
              disabled={!jobId.trim() || !!activeJobId}
              className="px-6 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Connect
            </button>
            <button
              onClick={handleDisconnectFromJob}
              disabled={!activeJobId}
              className="px-6 py-2 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Disconnect
            </button>
          </div>
        </div>

        {/* Job Events */}
        {activeJobId && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Job Events ({jobEvents.length})
            </h2>
            {jobStatus && (
              <div className="mb-4 p-4 bg-blue-50 rounded">
                <p className="text-sm">
                  <strong>Status:</strong> {jobStatus.status}
                </p>
                <p className="text-sm">
                  <strong>Progress:</strong> {jobStatus.progress}%
                </p>
                {jobStatus.current_node && (
                  <p className="text-sm">
                    <strong>Current Node:</strong> {jobStatus.current_node}
                  </p>
                )}
              </div>
            )}
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {jobEvents.slice().reverse().map((event, idx) => (
                <div key={idx} className="p-3 bg-gray-50 rounded text-sm">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-blue-600">{event.type}</span>
                    <span className="text-gray-500 text-xs">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <pre className="text-xs text-gray-700 overflow-x-auto">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                </div>
              ))}
              {jobEvents.length === 0 && (
                <p className="text-center text-gray-500 py-8">
                  No events received yet
                </p>
              )}
            </div>
          </div>
        )}

        {/* Agent Executions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Agent Executions ({executions.length})
          </h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {executions.slice(0, 20).map((execution, idx) => (
              <div key={idx} className="p-3 bg-gray-50 rounded text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{execution.agent_id}</span>
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-1 rounded text-xs ${
                        execution.status === 'running'
                          ? 'bg-blue-100 text-blue-800'
                          : execution.status === 'completed'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {execution.status}
                    </span>
                    <span className="text-gray-500 text-xs">
                      {new Date(execution.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
                {execution.duration_ms && (
                  <p className="text-xs text-gray-600 mt-1">
                    Duration: {execution.duration_ms}ms
                  </p>
                )}
              </div>
            ))}
            {executions.length === 0 && (
              <p className="text-center text-gray-500 py-8">
                No executions received yet
              </p>
            )}
          </div>
        </div>

        {/* Workflow Events */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Workflow Flow Events ({agentExecutions.length})
          </h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {agentExecutions.slice(0, 20).map((flow, idx) => (
              <div key={idx} className="p-3 bg-gray-50 rounded text-sm">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-blue-600">
                      {flow.source_agent}
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="font-medium text-blue-600">
                      {flow.target_agent}
                    </span>
                  </div>
                  <span className="text-gray-500 text-xs">
                    {new Date(flow.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-600">
                  <span>Status: {flow.status}</span>
                  {flow.latency_ms && <span>Latency: {flow.latency_ms}ms</span>}
                </div>
              </div>
            ))}
            {agentExecutions.length === 0 && (
              <p className="text-center text-gray-500 py-8">
                No flow events received yet
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebSocketTest;
