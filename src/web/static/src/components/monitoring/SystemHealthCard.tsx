import React, { useEffect, useState } from 'react';
import { SystemHealth } from '@/types/monitoring';
import { apiClient } from '@/api/client';

const SystemHealthCard: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHealth();
    const interval = setInterval(loadHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadHealth = async () => {
    try {
      const data = await apiClient.getSystemHealth();
      setHealth(data);
    } catch (error) {
      console.error('Failed to load system health:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !health) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'operational':
        return 'text-green-600 bg-green-50';
      case 'degraded':
        return 'text-yellow-600 bg-yellow-50';
      case 'error':
      case 'down':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
      case 'operational':
        return '✓';
      case 'degraded':
        return '⚠';
      case 'error':
      case 'down':
        return '✗';
      default:
        return '?';
    }
  };

  const formatUptime = (seconds: number | undefined) => {
    if (!seconds) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days}d ${hours % 24}h`;
    }
    
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">System Health</h2>
        {health && (
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
              health.status
            )}`}
          >
            {getStatusIcon(health.status)} {health.status}
          </span>
        )}
      </div>

      {health ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-600">Uptime</p>
              <p className="text-2xl font-bold text-gray-900">
                {formatUptime(health.uptime)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Version</p>
              <p className="text-2xl font-bold text-gray-900">
                {health.version || '1.0.0'}
              </p>
            </div>
          </div>

          {health.components && Object.keys(health.components).length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Components</p>
              <div className="space-y-2">
                {Object.entries(health.components).map(([name, component]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded"
                  >
                    <span className="text-sm font-medium text-gray-700">
                      {name}
                    </span>
                    <span
                      className={`text-sm px-2 py-1 rounded ${getStatusColor(
                        component.status
                      )}`}
                    >
                      {getStatusIcon(component.status)} {component.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-xs text-gray-500 pt-2 border-t">
            Last updated: {new Date(health.timestamp).toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No health data available
        </div>
      )}
    </div>
  );
};

export default SystemHealthCard;
