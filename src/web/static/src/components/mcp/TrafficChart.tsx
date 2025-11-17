import React from 'react';

interface MCPMetrics {
  total_messages: number;
  avg_latency_ms: number;
  error_rate: number;
  error_count: number;
  top_agents: Record<string, number>;
  by_type: Record<string, number>;
}

interface TrafficChartProps {
  metrics: MCPMetrics;
}

export const TrafficChart: React.FC<TrafficChartProps> = ({ metrics }) => {
  // Calculate max value for scaling
  const maxAgentCount = Math.max(...Object.values(metrics.top_agents), 1);
  const maxTypeCount = Math.max(...Object.values(metrics.by_type), 1);

  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
        {/* Top Agents Chart */}
        <div
          style={{
            padding: '20px',
            backgroundColor: 'white',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}
        >
          <h3 style={{ margin: '0 0 15px 0', fontSize: '16px' }}>Top Agents</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {Object.entries(metrics.top_agents).length > 0 ? (
              Object.entries(metrics.top_agents)
                .slice(0, 5)
                .map(([agent, count]) => (
                  <div key={agent}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '4px',
                        fontSize: '14px'
                      }}
                    >
                      <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                        {agent}
                      </span>
                      <span style={{ fontWeight: 'bold' }}>{count}</span>
                    </div>
                    <div
                      style={{
                        width: '100%',
                        height: '8px',
                        backgroundColor: '#e9ecef',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}
                    >
                      <div
                        style={{
                          width: `${(count / maxAgentCount) * 100}%`,
                          height: '100%',
                          backgroundColor: '#007bff',
                          transition: 'width 0.3s ease'
                        }}
                      />
                    </div>
                  </div>
                ))
            ) : (
              <div style={{ color: '#6c757d', textAlign: 'center', padding: '20px' }}>
                No agent data available
              </div>
            )}
          </div>
        </div>

        {/* Message Types Chart */}
        <div
          style={{
            padding: '20px',
            backgroundColor: 'white',
            borderRadius: '8px',
            border: '1px solid #dee2e6'
          }}
        >
          <h3 style={{ margin: '0 0 15px 0', fontSize: '16px' }}>Message Types</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {Object.entries(metrics.by_type).length > 0 ? (
              Object.entries(metrics.by_type).map(([type, count]) => (
                <div key={type}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '4px',
                      fontSize: '14px'
                    }}
                  >
                    <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{type}</span>
                    <span style={{ fontWeight: 'bold' }}>{count}</span>
                  </div>
                  <div
                    style={{
                      width: '100%',
                      height: '8px',
                      backgroundColor: '#e9ecef',
                      borderRadius: '4px',
                      overflow: 'hidden'
                    }}
                  >
                    <div
                      style={{
                        width: `${(count / maxTypeCount) * 100}%`,
                        height: '100%',
                        backgroundColor: '#28a745',
                        transition: 'width 0.3s ease'
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div style={{ color: '#6c757d', textAlign: 'center', padding: '20px' }}>
                No message type data available
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
