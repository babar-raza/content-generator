import React, { useState, useEffect } from 'react';
import { MCPTrafficTable } from '../components/mcp/MCPTrafficTable';
import { MessageInspector } from '../components/mcp/MessageInspector';
import { TrafficChart } from '../components/mcp/TrafficChart';

interface MCPMessage {
  id: string;
  timestamp: string;
  message_type: string;
  from_agent: string;
  to_agent: string;
  request: any;
  response: any;
  status: string | null;
  duration_ms: number | null;
  error: string | null;
}

interface MCPMetrics {
  total_messages: number;
  avg_latency_ms: number;
  error_rate: number;
  error_count: number;
  top_agents: Record<string, number>;
  by_type: Record<string, number>;
}

interface Filters {
  agentId: string;
  messageType: string;
  status: string;
}

export const MCPMonitorPage: React.FC = () => {
  const [traffic, setTraffic] = useState<MCPMessage[]>([]);
  const [metrics, setMetrics] = useState<MCPMetrics | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<MCPMessage | null>(null);
  const [filters, setFilters] = useState<Filters>({
    agentId: '',
    messageType: '',
    status: ''
  });
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadTraffic();
    loadMetrics();

    // Auto-refresh every 5 seconds if enabled
    if (autoRefresh) {
      const interval = setInterval(() => {
        loadTraffic();
        loadMetrics();
      }, 5000);

      return () => clearInterval(interval);
    }
  }, [filters, autoRefresh]);

  const loadTraffic = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.append('limit', '100');
      
      if (filters.agentId) params.append('agent_id', filters.agentId);
      if (filters.messageType) params.append('message_type', filters.messageType);
      if (filters.status) params.append('status', filters.status);

      const response = await fetch(`/api/mcp/traffic?${params.toString()}`);
      const data = await response.json();
      
      setTraffic(data.messages || []);
    } catch (error) {
      console.error('Failed to load MCP traffic:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      const response = await fetch('/api/mcp/metrics');
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to load MCP metrics:', error);
    }
  };

  const handleExport = async (format: 'json' | 'csv') => {
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      
      if (filters.agentId) params.append('agent_id', filters.agentId);
      if (filters.messageType) params.append('message_type', filters.messageType);
      if (filters.status) params.append('status', filters.status);

      const response = await fetch(`/api/mcp/export?${params.toString()}`);
      const blob = await response.blob();
      
      // Download the file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mcp_traffic.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export MCP traffic:', error);
    }
  };

  const handleCleanup = async () => {
    if (!confirm('Are you sure you want to cleanup old traffic data?')) {
      return;
    }

    try {
      const response = await fetch('/api/mcp/cleanup', { method: 'POST' });
      const data = await response.json();
      alert(`Deleted ${data.deleted} old records`);
      loadTraffic();
      loadMetrics();
    } catch (error) {
      console.error('Failed to cleanup traffic:', error);
      alert('Failed to cleanup traffic');
    }
  };

  return (
    <div className="mcp-monitor-page" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1 style={{ margin: 0 }}>MCP Traffic Monitor</h1>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            {' Auto-refresh'}
          </label>
          <button onClick={() => loadTraffic()}>Refresh</button>
        </div>
      </div>

      {/* Metrics Panel */}
      {metrics && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '15px',
          marginBottom: '20px'
        }}>
          <div style={{
            padding: '15px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '5px' }}>
              Total Messages
            </div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {metrics.total_messages.toLocaleString()}
            </div>
          </div>

          <div style={{
            padding: '15px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '5px' }}>
              Avg Latency
            </div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {metrics.avg_latency_ms.toFixed(0)}ms
            </div>
          </div>

          <div style={{
            padding: '15px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '5px' }}>
              Error Rate
            </div>
            <div style={{
              fontSize: '24px',
              fontWeight: 'bold',
              color: metrics.error_rate > 5 ? '#dc3545' : '#28a745'
            }}>
              {metrics.error_rate.toFixed(1)}%
            </div>
          </div>

          <div style={{
            padding: '15px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}>
            <div style={{ fontSize: '14px', color: '#6c757d', marginBottom: '5px' }}>
              Errors
            </div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#dc3545' }}>
              {metrics.error_count}
            </div>
          </div>
        </div>
      )}

      {/* Traffic Chart */}
      {metrics && <TrafficChart metrics={metrics} />}

      {/* Toolbar */}
      <div style={{
        display: 'flex',
        gap: '15px',
        marginBottom: '20px',
        padding: '15px',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #dee2e6'
      }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
            Agent ID
          </label>
          <input
            type="text"
            value={filters.agentId}
            onChange={(e) => setFilters({ ...filters, agentId: e.target.value })}
            placeholder="Filter by agent..."
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ced4da'
            }}
          />
        </div>

        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
            Message Type
          </label>
          <select
            value={filters.messageType}
            onChange={(e) => setFilters({ ...filters, messageType: e.target.value })}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ced4da'
            }}
          >
            <option value="">All Types</option>
            <option value="workflow.execute">workflow.execute</option>
            <option value="workflow.status">workflow.status</option>
            <option value="agent.invoke">agent.invoke</option>
            <option value="agent.list">agent.list</option>
          </select>
        </div>

        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
            Status
          </label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            style={{
              width: '100%',
              padding: '8px',
              borderRadius: '4px',
              border: '1px solid #ced4da'
            }}
          >
            <option value="">All Statuses</option>
            <option value="success">Success</option>
            <option value="error">Error</option>
            <option value="timeout">Timeout</option>
          </select>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          <button
            onClick={() => handleExport('json')}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #007bff',
              backgroundColor: '#007bff',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Export JSON
          </button>
          <button
            onClick={() => handleExport('csv')}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #007bff',
              backgroundColor: '#007bff',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Export CSV
          </button>
          <button
            onClick={handleCleanup}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #dc3545',
              backgroundColor: '#dc3545',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Cleanup Old
          </button>
        </div>
      </div>

      {/* Traffic Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>
      ) : (
        <MCPTrafficTable
          traffic={traffic}
          onMessageClick={setSelectedMessage}
        />
      )}

      {/* Message Inspector */}
      {selectedMessage && (
        <MessageInspector
          message={selectedMessage}
          onClose={() => setSelectedMessage(null)}
        />
      )}
    </div>
  );
};
