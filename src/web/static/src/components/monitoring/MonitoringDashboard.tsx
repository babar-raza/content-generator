import React, { useState } from 'react';
import { useMonitoring } from '@/hooks/useMonitoring';
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket';
import { useWorkflowWebSocket } from '@/hooks/useWorkflowWebSocket';
import SystemHealthCard from './SystemHealthCard';
import AgentStatusGrid from './AgentStatusGrid';
import ActiveJobsList from './ActiveJobsList';
import FlowDiagram from './FlowDiagram';
import SystemMetricsChart from './SystemMetricsChart';
import ConnectionStatus from '../ConnectionStatus';

const MonitoringDashboard: React.FC = () => {
  const [pollInterval, setPollInterval] = useState(10000);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  
  const {
    health,
    metrics,
    flows: polledFlows,
    bottlenecks,
    runningJobs,
    loading,
    error,
    refresh,
  } = useMonitoring({ pollInterval, enabled: true });

  // Use WebSocket for real-time agent updates
  const {
    agents: wsAgents,
    status: wsAgentStatus,
    reconnect: wsAgentReconnect,
  } = useAgentWebSocket({
    enabled: true,
    fallbackPolling: true,
  });

  // Use WebSocket for real-time workflow visualization
  const {
    agentExecutions,
    status: wsWorkflowStatus,
    reconnect: wsWorkflowReconnect,
  } = useWorkflowWebSocket({
    enabled: true,
    fallbackPolling: true,
  });

  // Use WebSocket agents if available, otherwise fall back to polling agents
  const agents = wsAgents.length > 0 ? wsAgents : [];

  // Use WebSocket flows if available, otherwise fall back to polling flows
  const flows = agentExecutions.length > 0 
    ? {
        flows: agentExecutions,
        window_seconds: 60,
        count: agentExecutions.length,
        timestamp: new Date().toISOString(),
      }
    : polledFlows;

  if (loading && !health) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading monitoring data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">M</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                System Monitoring
              </h1>
              <p className="text-sm text-gray-600">
                Real-time system health and performance metrics
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* WebSocket connection statuses */}
            <div className="flex items-center gap-3">
              <ConnectionStatus
                status={wsAgentStatus}
                label="Agents"
                onReconnect={wsAgentReconnect}
              />
              <ConnectionStatus
                status={wsWorkflowStatus}
                label="Flows"
                onReconnect={wsWorkflowReconnect}
              />
            </div>

            {/* Refresh interval selector */}
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Refresh:</label>
              <select
                value={pollInterval}
                onChange={(e) => setPollInterval(Number(e.target.value))}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={5000}>5s</option>
                <option value={10000}>10s</option>
                <option value={30000}>30s</option>
                <option value={60000}>60s</option>
              </select>
            </div>

            {/* Manual refresh button */}
            <button
              onClick={refresh}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors text-sm font-medium"
              aria-label="Refresh monitoring data"
            >
              ↻ Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 px-6 py-3">
          <div className="flex items-center">
            <span className="text-red-700 text-sm">⚠️ {error}</span>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Row 1: Health + Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SystemHealthCard health={health} loading={loading} />
            <SystemMetricsChart metrics={metrics} loading={loading} />
          </div>

          {/* Row 2: Agent Status */}
          <AgentStatusGrid
            agents={agents}
            loading={loading}
            onAgentClick={setSelectedAgentId}
          />

          {/* Row 3: Active Jobs */}
          <ActiveJobsList
            jobs={runningJobs}
            loading={loading}
          />

          {/* Row 4: Flow Diagram */}
          <FlowDiagram
            flows={flows}
            bottlenecks={bottlenecks}
            loading={loading}
          />
        </div>
      </div>

      {/* Agent detail modal */}
      {selectedAgentId && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setSelectedAgentId(null)}
        >
          <div
            className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">
                Agent Details
              </h2>
              <button
                onClick={() => setSelectedAgentId(null)}
                className="text-gray-400 hover:text-gray-600"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3">
              {agents
                .filter((a) => a.agent_id === selectedAgentId)
                .map((agent) => (
                  <div key={agent.agent_id}>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">Agent ID</p>
                        <p className="font-medium">{agent.agent_id}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Status</p>
                        <p className="font-medium">{agent.status}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Total Executions</p>
                        <p className="font-medium">{agent.total_executions || 0}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Avg Latency</p>
                        <p className="font-medium">
                          {agent.avg_latency_ms?.toFixed(2) || 0} ms
                        </p>
                      </div>
                      {agent.last_execution && (
                        <div className="col-span-2">
                          <p className="text-sm text-gray-600">Last Execution</p>
                          <p className="font-medium">
                            {new Date(agent.last_execution).toLocaleString()}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MonitoringDashboard;
