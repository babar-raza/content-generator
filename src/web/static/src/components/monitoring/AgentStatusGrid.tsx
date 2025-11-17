import React, { useEffect, useState } from 'react';
import { AgentStatus } from '@/types/monitoring';
import { apiClient } from '@/api/client';
import { useNavigate } from 'react-router-dom';

interface AgentStatusGridProps {
  compact?: boolean;
}

const AgentStatusGrid: React.FC<AgentStatusGridProps> = ({ compact = false }) => {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadAgents();
    const interval = setInterval(loadAgents, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadAgents = async () => {
    try {
      const data = await apiClient.getAgentStatuses();
      setAgents(data);
    } catch (error) {
      console.error('Failed to load agents:', error);
    } finally {
      setLoading(false);
    }
  };

  const onAgentClick = (agentId: string) => {
    navigate('/agents');
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'available':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'busy':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'error':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'offline':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'available':
        return '✓';
      case 'busy':
        return '⟳';
      case 'error':
        return '✗';
      case 'offline':
        return '○';
      default:
        return '?';
    }
  };

  if (loading && agents.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4"></div>
          <div className={`grid ${compact ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'} gap-4`}>
            {[1, 2, 3, 4, 5, 6].slice(0, compact ? 3 : 6).map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const displayAgents = compact ? agents.slice(0, 6) : agents;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Agent Status</h2>
        <span className="text-sm text-gray-600">
          {agents.length} {agents.length === 1 ? 'agent' : 'agents'}
        </span>
      </div>

      {displayAgents.length > 0 ? (
        <>
          <div className={`grid ${compact ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'} gap-4`}>
            {displayAgents.map((agent) => (
              <div
                key={agent.agent_id}
                onClick={() => onAgentClick(agent.agent_id)}
                className={`border-2 rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow ${getStatusColor(
                  agent.status
                )}`}
                role="button"
                tabIndex={0}
                aria-label={`View details for ${agent.name}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onAgentClick(agent.agent_id);
                  }
                }}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-sm truncate" title={agent.name}>
                      {agent.name}
                    </h3>
                    {!compact && (
                      <p className="text-xs opacity-75 truncate" title={agent.agent_id}>
                        {agent.agent_id}
                      </p>
                    )}
                  </div>
                  <span className="text-lg ml-2">{getStatusIcon(agent.status)}</span>
                </div>

                {!compact && (
                  <>
                    <div className="grid grid-cols-2 gap-2 text-xs mt-3">
                      <div>
                        <p className="opacity-75">Executions</p>
                        <p className="font-semibold">{agent.total_executions || 0}</p>
                      </div>
                      <div>
                        <p className="opacity-75">Avg Latency</p>
                        <p className="font-semibold">
                          {agent.avg_latency_ms?.toFixed(0) || 0}ms
                        </p>
                      </div>
                    </div>

                    {agent.last_execution && (
                      <div className="text-xs opacity-75 mt-2 pt-2 border-t border-current">
                        Last: {new Date(agent.last_execution).toLocaleTimeString()}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
          {compact && agents.length > 6 && (
            <button
              onClick={() => navigate('/agents')}
              className="mt-4 w-full text-center text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View all {agents.length} agents →
            </button>
          )}
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">No agents available</div>
      )}
    </div>
  );
};

export default AgentStatusGrid;
