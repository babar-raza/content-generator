import React from 'react';
import { CheckCircle, Circle, AlertCircle, Loader } from 'lucide-react';

export type AgentStatus = 'pending' | 'running' | 'completed' | 'failed';

interface AgentStatusIndicatorProps {
  status: AgentStatus;
  agentId: string;
  duration?: number;
}

export const AgentStatusIndicator: React.FC<AgentStatusIndicatorProps> = ({
  status,
  agentId,
  duration
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return <Circle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'bg-blue-50 border-blue-300';
      case 'completed':
        return 'bg-green-50 border-green-300';
      case 'failed':
        return 'bg-red-50 border-red-300';
      default:
        return 'bg-gray-50 border-gray-300';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'running':
        return 'Running...';
      case 'completed':
        return duration ? `Completed (${duration.toFixed(2)}s)` : 'Completed';
      case 'failed':
        return 'Failed';
      default:
        return 'Pending';
    }
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border-2 ${getStatusColor()}`}>
      {getStatusIcon()}
      <div className="flex flex-col">
        <span className="text-sm font-medium">{agentId}</span>
        <span className="text-xs text-gray-600">{getStatusText()}</span>
      </div>
    </div>
  );
};
