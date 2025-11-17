import React from 'react';
import { ConnectionStatus as Status } from '@/hooks/useWebSocket';

interface ConnectionStatusProps {
  status: Status;
  label?: string;
  showLabel?: boolean;
  onReconnect?: () => void;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  status,
  label,
  showLabel = true,
  onReconnect,
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          color: 'bg-green-500',
          text: 'Connected',
          textColor: 'text-green-700',
          icon: '●',
        };
      case 'connecting':
        return {
          color: 'bg-yellow-500',
          text: 'Connecting',
          textColor: 'text-yellow-700',
          icon: '◐',
          animate: true,
        };
      case 'disconnected':
        return {
          color: 'bg-gray-400',
          text: 'Disconnected',
          textColor: 'text-gray-700',
          icon: '○',
        };
      case 'error':
        return {
          color: 'bg-red-500',
          text: 'Error',
          textColor: 'text-red-700',
          icon: '✕',
        };
      default:
        return {
          color: 'bg-gray-400',
          text: 'Unknown',
          textColor: 'text-gray-700',
          icon: '?',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${config.color} ${
            config.animate ? 'animate-pulse' : ''
          }`}
          title={config.text}
        />
        {showLabel && (
          <span className={`text-xs ${config.textColor}`}>
            {label || config.text}
          </span>
        )}
      </div>
      
      {(status === 'disconnected' || status === 'error') && onReconnect && (
        <button
          onClick={onReconnect}
          className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
          title="Reconnect"
        >
          ↻
        </button>
      )}
    </div>
  );
};

export default ConnectionStatus;
