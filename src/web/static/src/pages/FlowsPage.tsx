import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Activity, AlertTriangle, Clock, RefreshCw, TrendingUp } from 'lucide-react';

interface FlowData {
  correlation_id: string;
  agent_name: string;
  timestamp: string;
  duration_ms: number;
  status: string;
}

const FlowsPage: React.FC = () => {
  const [realtimeFlows, setRealtimeFlows] = useState<FlowData[]>([]);
  const [bottlenecks, setBottlenecks] = useState<any[]>([]);
  const [activeFlows, setActiveFlows] = useState<any[]>([]);
  const [selectedFlow, setSelectedFlow] = useState<string | null>(null);
  const [flowHistory, setFlowHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [windowSeconds, setWindowSeconds] = useState(60);
  const [thresholdMs, setThresholdMs] = useState(1000);

  useEffect(() => {
    loadData();
    
    if (autoRefresh) {
      const interval = setInterval(loadData, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, windowSeconds, thresholdMs]);

  const loadData = async () => {
    try {
      const [flows, bottlenecksData, active] = await Promise.all([
        apiClient.getRealtimeFlows(windowSeconds).catch(() => ({ flows: [] })),
        apiClient.getBottlenecks(thresholdMs).catch(() => ({ bottlenecks: [] })),
        apiClient.getActiveFlows().catch(() => ({ flows: [] }))
      ]);

      setRealtimeFlows(flows.flows || []);
      setBottlenecks(bottlenecksData.bottlenecks || []);
      setActiveFlows(active.flows || []);
    } catch (error) {
      console.error('Failed to load flows:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFlowHistory = async (correlationId: string) => {
    try {
      const history = await apiClient.getFlowHistory(correlationId);
      setFlowHistory(history.flows || []);
      setSelectedFlow(correlationId);
    } catch (error) {
      console.error('Failed to load flow history:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
      case 'success':
        return 'text-green-600 bg-green-50';
      case 'running':
      case 'processing':
        return 'text-blue-600 bg-blue-50';
      case 'error':
      case 'failed':
        return 'text-red-600 bg-red-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading flow data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Flow Monitor</h1>
          <p className="text-gray-600">Real-time agent interaction monitoring</p>
        </div>
        <div className="flex gap-3 items-center">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Auto-refresh</span>
          </label>
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-2">
            <Activity className="w-6 h-6 text-blue-500" />
            <h3 className="text-lg font-semibold">Realtime Flows</h3>
          </div>
          <div className="text-3xl font-bold">{realtimeFlows.length}</div>
          <div className="text-sm text-gray-500">Last {windowSeconds}s</div>
          <div className="mt-4">
            <label className="text-sm text-gray-600">Window (seconds)</label>
            <input
              type="number"
              value={windowSeconds}
              onChange={e => setWindowSeconds(Number(e.target.value))}
              className="w-full mt-1 px-3 py-2 border rounded-lg"
              min="10"
              max="300"
            />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-2">
            <TrendingUp className="w-6 h-6 text-green-500" />
            <h3 className="text-lg font-semibold">Active Flows</h3>
          </div>
          <div className="text-3xl font-bold">{activeFlows.length}</div>
          <div className="text-sm text-gray-500">Currently processing</div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="w-6 h-6 text-yellow-500" />
            <h3 className="text-lg font-semibold">Bottlenecks</h3>
          </div>
          <div className="text-3xl font-bold">{bottlenecks.length}</div>
          <div className="text-sm text-gray-500">Over {thresholdMs}ms</div>
          <div className="mt-4">
            <label className="text-sm text-gray-600">Threshold (ms)</label>
            <input
              type="number"
              value={thresholdMs}
              onChange={e => setThresholdMs(Number(e.target.value))}
              className="w-full mt-1 px-3 py-2 border rounded-lg"
              min="100"
              max="10000"
              step="100"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Recent Flows</h2>
          </div>
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {realtimeFlows.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <Activity className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>No recent flows</p>
              </div>
            ) : (
              realtimeFlows.map((flow, idx) => (
                <button
                  key={idx}
                  onClick={() => loadFlowHistory(flow.correlation_id)}
                  className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                    selectedFlow === flow.correlation_id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-medium">{flow.agent_name}</div>
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(flow.status)}`}>
                      {flow.status}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 flex items-center gap-2">
                    <Clock className="w-3 h-3" />
                    {flow.duration_ms}ms
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {flow.correlation_id.slice(0, 16)}...
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">Bottlenecks</h2>
          </div>
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {bottlenecks.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <AlertTriangle className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>No bottlenecks detected</p>
              </div>
            ) : (
              bottlenecks.map((bottleneck, idx) => (
                <div key={idx} className="p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div className="font-medium">{bottleneck.agent_name || 'Unknown'}</div>
                    <span className="text-red-600 font-semibold">
                      {bottleneck.duration_ms || bottleneck.avg_duration_ms}ms
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    {bottleneck.description || 'Slow processing detected'}
                  </div>
                  {bottleneck.count && (
                    <div className="text-xs text-gray-400 mt-1">
                      Occurrences: {bottleneck.count}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {selectedFlow && flowHistory.length > 0 && (
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">
            Flow History: {selectedFlow.slice(0, 32)}...
          </h2>
          <div className="space-y-3">
            {flowHistory.map((flow, idx) => (
              <div key={idx} className="border-l-4 border-blue-500 pl-4 py-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-medium">{flow.agent_name}</div>
                    <div className="text-sm text-gray-500">{flow.timestamp}</div>
                  </div>
                  <div className="text-right">
                    <div className={`px-2 py-1 text-xs rounded-full inline-block ${getStatusColor(flow.status)}`}>
                      {flow.status}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">{flow.duration_ms}ms</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FlowsPage;
