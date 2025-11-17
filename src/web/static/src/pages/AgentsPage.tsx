import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Activity, AlertCircle, CheckCircle, Clock, RefreshCw, XCircle, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface AgentInfo {
  id: string;
  name: string;
  status: string;
  health?: any;
  failures?: any[];
  logs?: any[];
  jobHistory?: JobUsage[];
}

interface JobUsage {
  job_id: string;
  status: string;
  duration: number;
  timestamp: string;
}

const AgentsPage: React.FC = () => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [healthData, setHealthData] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadAgents();
    loadHealth();
  }, []);

  const loadAgents = async () => {
    try {
      const agentsData = await apiClient.getAgents();
      const agentsList = Object.entries(agentsData).map(([id, agent]: [string, any]) => ({
        id,
        name: agent.name || id,
        status: agent.status || 'available'
      }));
      setAgents(agentsList);
    } catch (error) {
      console.error('Failed to load agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadHealth = async () => {
    try {
      const health = await apiClient.getAgentHealth();
      setHealthData(health);
    } catch (error) {
      console.error('Failed to load health data:', error);
    }
  };

  const loadAgentDetails = async (agent: AgentInfo) => {
    try {
      const [health, failures, logs, jobHistory] = await Promise.all([
        apiClient.getAgentHealthById(agent.id).catch(() => null),
        apiClient.getAgentFailures(agent.id).catch(() => []),
        apiClient.getAgentLogs(agent.id).catch(() => []),
        apiClient.getAgentJobs(agent.id).catch(() => ({ jobs: [] }))
      ]);

      setSelectedAgent({
        ...agent,
        health,
        failures,
        logs,
        jobHistory: jobHistory.jobs || []
      });
    } catch (error) {
      console.error('Failed to load agent details:', error);
      setSelectedAgent(agent);
    }
  };

  const resetHealth = async (agentId: string) => {
    try {
      await apiClient.resetAgentHealth(agentId);
      await loadHealth();
      if (selectedAgent?.id === agentId) {
        await loadAgentDetails(selectedAgent);
      }
    } catch (error) {
      console.error('Failed to reset health:', error);
    }
  };

  const navigateToJob = (jobId: string) => {
    navigate(`/jobs?id=${jobId}`);
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'available':
      case 'healthy':
      case 'completed':
        return 'text-green-600';
      case 'busy':
      case 'running':
        return 'text-yellow-600';
      case 'error':
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'available':
      case 'healthy':
      case 'completed':
        return <CheckCircle className="w-5 h-5" />;
      case 'busy':
      case 'running':
        return <Clock className="w-5 h-5" />;
      case 'error':
      case 'failed':
        return <XCircle className="w-5 h-5" />;
      default:
        return <Activity className="w-5 h-5" />;
    }
  };

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading agents...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Agent Management</h1>
          <p className="text-gray-600">Monitor and configure agents</p>
        </div>
        <button
          onClick={() => { loadAgents(); loadHealth(); }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold">Agents ({agents.length})</h2>
            </div>
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {agents.map(agent => (
                <button
                  key={agent.id}
                  onClick={() => loadAgentDetails(agent)}
                  className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                    selectedAgent?.id === agent.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={getStatusColor(agent.status)}>
                        {getStatusIcon(agent.status)}
                      </div>
                      <div>
                        <div className="font-medium">{agent.name}</div>
                        <div className="text-sm text-gray-500">{agent.id}</div>
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          {selectedAgent ? (
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-2xl font-bold">{selectedAgent.name}</h2>
                    <p className="text-gray-600">{selectedAgent.id}</p>
                  </div>
                  <button
                    onClick={() => resetHealth(selectedAgent.id)}
                    className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                  >
                    Reset Health
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 mb-1">Status</div>
                    <div className={`flex items-center gap-2 text-lg font-semibold ${getStatusColor(selectedAgent.status)}`}>
                      {getStatusIcon(selectedAgent.status)}
                      {selectedAgent.status}
                    </div>
                  </div>
                  {selectedAgent.health && (
                    <>
                      <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-600 mb-1">Health Score</div>
                        <div className="text-lg font-semibold">
                          {selectedAgent.health.score || 'N/A'}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {selectedAgent.jobHistory && selectedAgent.jobHistory.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-blue-500" />
                    Job History ({selectedAgent.jobHistory.length})
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Job ID</th>
                          <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
                          <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Duration</th>
                          <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Time</th>
                          <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {selectedAgent.jobHistory.map((job, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                                {job.job_id.substring(0, 8)}...
                              </code>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center gap-1 ${getStatusColor(job.status)}`}>
                                <span className="w-2 h-2 rounded-full bg-current"></span>
                                {job.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {job.duration.toFixed(2)}s
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-500">
                              {formatRelativeTime(job.timestamp)}
                            </td>
                            <td className="px-4 py-3">
                              <button
                                onClick={() => navigateToJob(job.job_id)}
                                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                              >
                                View Job
                                <ExternalLink className="w-3 h-3" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {selectedAgent.failures && selectedAgent.failures.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    Failure History ({selectedAgent.failures.length})
                  </h3>
                  <div className="space-y-3 max-h-60 overflow-y-auto">
                    {selectedAgent.failures.map((failure: any, idx: number) => (
                      <div key={idx} className="border-l-4 border-red-500 pl-4 py-2">
                        <div className="font-medium text-red-700">{failure.error || 'Unknown error'}</div>
                        <div className="text-sm text-gray-500">
                          {failure.timestamp ? new Date(failure.timestamp).toLocaleString() : 'Unknown time'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedAgent.logs && selectedAgent.logs.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4">Recent Logs</h3>
                  <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm max-h-96 overflow-y-auto">
                    {selectedAgent.logs.map((log: any, idx: number) => (
                      <div key={idx} className="mb-2">
                        <span className="text-gray-500">[{log.timestamp || 'N/A'}]</span>{' '}
                        <span className={log.level === 'error' ? 'text-red-400' : 'text-gray-300'}>
                          {log.message || JSON.stringify(log)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-12">
              <div className="text-center text-gray-500">
                <Activity className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg">Select an agent to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentsPage;
