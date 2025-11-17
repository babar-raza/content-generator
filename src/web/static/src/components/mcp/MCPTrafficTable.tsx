import React from 'react';

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

interface MCPTrafficTableProps {
  traffic: MCPMessage[];
  onMessageClick: (message: MCPMessage) => void;
}

const formatTime = (timestamp: string): string => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  } catch {
    return timestamp;
  }
};

const StatusBadge: React.FC<{ status: string | null }> = ({ status }) => {
  let backgroundColor = '#6c757d';
  let text = status || 'pending';

  if (status === 'success') {
    backgroundColor = '#28a745';
    text = '✓ Success';
  } else if (status === 'error') {
    backgroundColor = '#dc3545';
    text = '✗ Error';
  } else if (status === 'timeout') {
    backgroundColor = '#ffc107';
    text = '⏱ Timeout';
  }

  return (
    <span
      style={{
        padding: '4px 8px',
        borderRadius: '4px',
        backgroundColor,
        color: 'white',
        fontSize: '12px',
        fontWeight: 'bold'
      }}
    >
      {text}
    </span>
  );
};

const AgentBadge: React.FC<{ agent: string }> = ({ agent }) => (
  <span
    style={{
      padding: '2px 8px',
      borderRadius: '4px',
      backgroundColor: '#e9ecef',
      color: '#495057',
      fontSize: '12px',
      fontFamily: 'monospace'
    }}
  >
    {agent}
  </span>
);

export const MCPTrafficTable: React.FC<MCPTrafficTableProps> = ({
  traffic,
  onMessageClick
}) => {
  if (traffic.length === 0) {
    return (
      <div
        style={{
          textAlign: 'center',
          padding: '40px',
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}
      >
        No MCP traffic to display. Start a job to see traffic here.
      </div>
    );
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          backgroundColor: 'white',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
        }}
      >
        <thead>
          <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: 600 }}>Time</th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: 600 }}>Route</th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: 600 }}>Type</th>
            <th style={{ padding: '12px', textAlign: 'left', fontWeight: 600 }}>Status</th>
            <th style={{ padding: '12px', textAlign: 'right', fontWeight: 600 }}>Duration</th>
          </tr>
        </thead>
        <tbody>
          {traffic.map((msg) => (
            <tr
              key={msg.id}
              onClick={() => onMessageClick(msg)}
              style={{
                cursor: 'pointer',
                borderBottom: '1px solid #dee2e6',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#f8f9fa';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'white';
              }}
            >
              <td style={{ padding: '12px', fontSize: '14px' }}>
                {formatTime(msg.timestamp)}
              </td>
              <td style={{ padding: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AgentBadge agent={msg.from_agent} />
                  <span style={{ color: '#6c757d' }}>→</span>
                  <AgentBadge agent={msg.to_agent} />
                </div>
              </td>
              <td style={{ padding: '12px', fontSize: '14px', fontFamily: 'monospace' }}>
                {msg.message_type}
              </td>
              <td style={{ padding: '12px' }}>
                <StatusBadge status={msg.status} />
              </td>
              <td style={{ padding: '12px', textAlign: 'right', fontSize: '14px' }}>
                {msg.duration_ms !== null ? (
                  <span
                    style={{
                      color: msg.duration_ms > 1000 ? '#dc3545' : msg.duration_ms > 500 ? '#ffc107' : '#28a745'
                    }}
                  >
                    {msg.duration_ms.toFixed(0)}ms
                  </span>
                ) : (
                  <span style={{ color: '#6c757d' }}>-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
