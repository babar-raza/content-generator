import React, { useState, useEffect } from 'react';

interface MeshAgent {
  agent_id: string;
  agent_type: string;
  capabilities: string[];
  health: string;
  load: number;
  max_capacity: number;
}

interface MeshStats {
  registry_stats: {
    total_agents: number;
    healthy_agents: number;
    degraded_agents: number;
    total_capabilities: number;
    avg_load: number;
  };
  router_stats: {
    current_hop_count: number;
    max_hops: number;
    circuit_breaker_enabled: boolean;
  };
  active_contexts: number;
}

interface ExecutionTrace {
  agent_id: string;
  agent_type: string;
  timestamp: string;
  success: boolean;
  execution_time: number;
}

const MeshPage: React.FC = () => {
  const [agents, setAgents] = useState<MeshAgent[]>([]);
  const [stats, setStats] = useState<MeshStats | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [inputData, setInputData] = useState<string>('{}');
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadAgents();
    loadStats();
  }, []);

  const loadAgents = async () => {
    try {
      const response = await fetch('/api/mesh/agents');
      const data = await response.json();
      setAgents(data.agents || []);
    } catch (err) {
      console.error('Failed to load agents:', err);
      setError('Failed to load mesh agents');
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/mesh/stats');
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const executeWorkflow = async () => {
    if (!selectedAgent) {
      setError('Please select an initial agent');
      return;
    }

    setExecuting(true);
    setError('');
    setExecutionResult(null);

    try {
      let parsedInput = {};
      try {
        parsedInput = JSON.parse(inputData);
      } catch {
        setError('Invalid JSON input');
        setExecuting(false);
        return;
      }

      const response = await fetch('/api/mesh/execute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          initial_agent: selectedAgent,
          input_data: parsedInput,
          workflow_name: 'mesh_workflow'
        })
      });

      const result = await response.json();
      setExecutionResult(result);

      if (!result.success) {
        setError(result.error || 'Workflow execution failed');
      }

      // Refresh agents and stats
      await loadAgents();
      await loadStats();
    } catch (err: any) {
      setError(err.message || 'Failed to execute workflow');
    } finally {
      setExecuting(false);
    }
  };

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      case 'unhealthy': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Mesh Orchestration</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Statistics Section */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white p-4 rounded shadow">
            <h3 className="text-sm font-semibold text-gray-600 mb-2">Agent Registry</h3>
            <p className="text-2xl font-bold">{stats.registry_stats.total_agents}</p>
            <p className="text-sm text-gray-500">
              {stats.registry_stats.healthy_agents} healthy, {stats.registry_stats.degraded_agents} degraded
            </p>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h3 className="text-sm font-semibold text-gray-600 mb-2">Capabilities</h3>
            <p className="text-2xl font-bold">{stats.registry_stats.total_capabilities}</p>
            <p className="text-sm text-gray-500">
              Avg load: {stats.registry_stats.avg_load.toFixed(2)}
            </p>
          </div>

          <div className="bg-white p-4 rounded shadow">
            <h3 className="text-sm font-semibold text-gray-600 mb-2">Router</h3>
            <p className="text-2xl font-bold">{stats.router_stats.max_hops}</p>
            <p className="text-sm text-gray-500">
              Max hops, {stats.router_stats.circuit_breaker_enabled ? 'CB enabled' : 'CB disabled'}
            </p>
          </div>
        </div>
      )}

      {/* Workflow Execution Section */}
      <div className="bg-white p-6 rounded shadow mb-6">
        <h2 className="text-xl font-bold mb-4">Execute Mesh Workflow</h2>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Initial Agent</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="w-full p-2 border rounded"
            disabled={executing}
          >
            <option value="">Select an agent...</option>
            {agents.map((agent) => (
              <option key={agent.agent_id} value={agent.agent_type}>
                {agent.agent_type} ({agent.health})
              </option>
            ))}
          </select>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Input Data (JSON)</label>
          <textarea
            value={inputData}
            onChange={(e) => setInputData(e.target.value)}
            className="w-full p-2 border rounded font-mono text-sm"
            rows={4}
            disabled={executing}
            placeholder='{"content": "sample text", "context": {}}'
          />
        </div>

        <button
          onClick={executeWorkflow}
          disabled={executing || !selectedAgent}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {executing ? 'Executing...' : 'Execute Workflow'}
        </button>
      </div>

      {/* Execution Result */}
      {executionResult && (
        <div className="bg-white p-6 rounded shadow mb-6">
          <h2 className="text-xl font-bold mb-4">Execution Result</h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-semibold ${executionResult.success ? 'text-green-600' : 'text-red-600'}`}>
                {executionResult.success ? 'Success' : 'Failed'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Execution Time</p>
              <p className="font-semibold">{executionResult.execution_time?.toFixed(2)}s</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Hops</p>
              <p className="font-semibold">{executionResult.total_hops}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Agents Executed</p>
              <p className="font-semibold">{executionResult.agents_executed?.length || 0}</p>
            </div>
          </div>

          {executionResult.execution_trace && (
            <div>
              <h3 className="font-semibold mb-2">Execution Trace</h3>
              <div className="space-y-2">
                {executionResult.execution_trace.map((trace: ExecutionTrace, idx: number) => (
                  <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                    <div className="flex justify-between">
                      <span className="font-medium">{trace.agent_type}</span>
                      <span className={trace.success ? 'text-green-600' : 'text-red-600'}>
                        {trace.success ? '✓' : '✗'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">
                      {trace.execution_time?.toFixed(2)}s
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Agents List */}
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-bold mb-4">Registered Agents</h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left py-2">Agent Type</th>
                <th className="text-left py-2">Health</th>
                <th className="text-left py-2">Load</th>
                <th className="text-left py-2">Capabilities</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.agent_id} className="border-b hover:bg-gray-50">
                  <td className="py-2">{agent.agent_type}</td>
                  <td className="py-2">
                    <span className={`font-semibold ${getHealthColor(agent.health)}`}>
                      {agent.health}
                    </span>
                  </td>
                  <td className="py-2">
                    {agent.load} / {agent.max_capacity}
                  </td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities.map((cap, idx) => (
                        <span
                          key={idx}
                          className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                        >
                          {cap}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default MeshPage;
