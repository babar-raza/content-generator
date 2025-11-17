import React, { useEffect, useState } from 'react';
import { SystemMetrics } from '@/types/monitoring';
import { apiClient } from '@/api/client';

const SystemMetricsChart: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadMetrics = async () => {
    try {
      const data = await apiClient.getSystemMetrics();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to load system metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !metrics) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  const getPercentageColor = (percentage: number | undefined) => {
    if (!percentage) return 'bg-gray-400';
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">System Metrics</h2>

      {metrics ? (
        <div className="space-y-4">
          {/* CPU & Memory gauges */}
          {(metrics.cpu_percent !== undefined || metrics.memory_percent !== undefined) && (
            <div className="grid grid-cols-2 gap-4">
              {metrics.cpu_percent !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">CPU</span>
                    <span className="text-sm font-bold text-gray-900">
                      {metrics.cpu_percent.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all duration-300 ${getPercentageColor(
                        metrics.cpu_percent
                      )}`}
                      style={{ width: `${Math.min(metrics.cpu_percent, 100)}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {metrics.memory_percent !== undefined && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">Memory</span>
                    <span className="text-sm font-bold text-gray-900">
                      {metrics.memory_percent.toFixed(1)}%
                      {metrics.memory_mb && (
                        <span className="text-xs text-gray-500 ml-1">
                          ({(metrics.memory_mb / 1024).toFixed(1)} GB)
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all duration-300 ${getPercentageColor(
                        metrics.memory_percent
                      )}`}
                      style={{ width: `${Math.min(metrics.memory_percent, 100)}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Job statistics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
            <div className="bg-blue-50 rounded-lg p-3">
              <p className="text-xs text-blue-600 font-medium mb-1">Active Jobs</p>
              <p className="text-2xl font-bold text-blue-900">{metrics.active_jobs}</p>
            </div>

            <div className="bg-yellow-50 rounded-lg p-3">
              <p className="text-xs text-yellow-600 font-medium mb-1">Queued</p>
              <p className="text-2xl font-bold text-yellow-900">{metrics.queued_jobs}</p>
            </div>

            {metrics.completed_jobs_today !== undefined && (
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-xs text-green-600 font-medium mb-1">Completed Today</p>
                <p className="text-2xl font-bold text-green-900">
                  {metrics.completed_jobs_today}
                </p>
              </div>
            )}

            {metrics.agents_active !== undefined && (
              <div className="bg-purple-50 rounded-lg p-3">
                <p className="text-xs text-purple-600 font-medium mb-1">Active Agents</p>
                <p className="text-2xl font-bold text-purple-900">{metrics.agents_active}</p>
              </div>
            )}
          </div>

          <div className="text-xs text-gray-500 pt-2 border-t">
            Last updated: {new Date(metrics.timestamp).toLocaleTimeString()}
          </div>
        </div>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No metrics data available
        </div>
      )}
    </div>
  );
};

export default SystemMetricsChart;
