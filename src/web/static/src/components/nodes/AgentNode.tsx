import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { NodeData } from '@/types';

const AgentNode: React.FC<NodeProps<NodeData>> = ({ data, selected }) => {
  const getStatusColor = () => {
    switch (data.status) {
      case 'running':
        return 'border-blue-500 bg-blue-50';
      case 'completed':
        return 'border-green-500 bg-green-50';
      case 'error':
        return 'border-red-500 bg-red-50';
      default:
        return 'border-gray-300 bg-white';
    }
  };

  const getStatusIcon = () => {
    switch (data.status) {
      case 'running':
        return '⚡';
      case 'completed':
        return '✓';
      case 'error':
        return '✕';
      default:
        return '○';
    }
  };

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 shadow-sm min-w-[180px] transition-all ${getStatusColor()} ${
        selected ? 'ring-2 ring-primary-500' : ''
      }`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !border-2 !bg-white"
      />
      
      <div className="flex items-start justify-between gap-2 mb-1">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 truncate">
            {data.agentId || 'Node'}
          </div>
        </div>
        <span className="text-lg flex-shrink-0">{getStatusIcon()}</span>
      </div>
      
      <div className="text-xs text-gray-600 line-clamp-2">
        {data.label}
      </div>
      
      {data.agent && (
        <div className="mt-2 flex flex-wrap gap-1">
          {data.agent.capabilities.async && (
            <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
              async
            </span>
          )}
          {data.agent.capabilities.stateful && (
            <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
              stateful
            </span>
          )}
        </div>
      )}
      
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !border-2 !bg-white"
      />
    </div>
  );
};

export default AgentNode;
