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

interface MessageInspectorProps {
  message: MCPMessage;
  onClose: () => void;
}

export const MessageInspector: React.FC<MessageInspectorProps> = ({
  message,
  onClose
}) => {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          padding: '0',
          width: '90%',
          maxWidth: '900px',
          maxHeight: '90vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px',
            borderBottom: '1px solid #dee2e6',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <h2 style={{ margin: 0, fontSize: '20px' }}>Message Inspector</h2>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              border: '1px solid #dee2e6',
              backgroundColor: 'white',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>

        {/* Content */}
        <div style={{ padding: '20px', overflowY: 'auto', flex: 1 }}>
          {/* Metadata */}
          <div
            style={{
              marginBottom: '20px',
              padding: '15px',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px'
            }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
              <div>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  Message ID
                </div>
                <div style={{ fontSize: '14px', fontFamily: 'monospace' }}>{message.id}</div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  Timestamp
                </div>
                <div style={{ fontSize: '14px' }}>
                  {new Date(message.timestamp).toLocaleString()}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  From Agent
                </div>
                <div
                  style={{
                    fontSize: '14px',
                    fontFamily: 'monospace',
                    padding: '4px 8px',
                    backgroundColor: '#e9ecef',
                    borderRadius: '4px',
                    display: 'inline-block'
                  }}
                >
                  {message.from_agent}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  To Agent
                </div>
                <div
                  style={{
                    fontSize: '14px',
                    fontFamily: 'monospace',
                    padding: '4px 8px',
                    backgroundColor: '#e9ecef',
                    borderRadius: '4px',
                    display: 'inline-block'
                  }}
                >
                  {message.to_agent}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  Message Type
                </div>
                <div style={{ fontSize: '14px', fontFamily: 'monospace' }}>
                  {message.message_type}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                  Status
                </div>
                <div>
                  <span
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      backgroundColor:
                        message.status === 'success'
                          ? '#28a745'
                          : message.status === 'error'
                          ? '#dc3545'
                          : '#6c757d',
                      color: 'white',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}
                  >
                    {message.status || 'pending'}
                  </span>
                </div>
              </div>

              {message.duration_ms !== null && (
                <div>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                    Duration
                  </div>
                  <div
                    style={{
                      fontSize: '14px',
                      color:
                        message.duration_ms > 1000
                          ? '#dc3545'
                          : message.duration_ms > 500
                          ? '#ffc107'
                          : '#28a745'
                    }}
                  >
                    {message.duration_ms.toFixed(2)}ms
                  </div>
                </div>
              )}

              {message.error && (
                <div style={{ gridColumn: '1 / -1' }}>
                  <div style={{ fontSize: '12px', color: '#6c757d', marginBottom: '4px' }}>
                    Error
                  </div>
                  <div
                    style={{
                      fontSize: '14px',
                      color: '#dc3545',
                      padding: '8px',
                      backgroundColor: '#f8d7da',
                      borderRadius: '4px'
                    }}
                  >
                    {message.error}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Request */}
          <div style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', marginBottom: '10px' }}>Request Payload</h3>
            <pre
              style={{
                backgroundColor: '#f8f9fa',
                padding: '15px',
                borderRadius: '8px',
                border: '1px solid #dee2e6',
                overflow: 'auto',
                fontSize: '12px',
                fontFamily: 'monospace',
                maxHeight: '200px'
              }}
            >
              {JSON.stringify(message.request, null, 2)}
            </pre>
          </div>

          {/* Response */}
          <div>
            <h3 style={{ fontSize: '16px', marginBottom: '10px' }}>Response Payload</h3>
            {message.response ? (
              <pre
                style={{
                  backgroundColor: '#f8f9fa',
                  padding: '15px',
                  borderRadius: '8px',
                  border: '1px solid #dee2e6',
                  overflow: 'auto',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  maxHeight: '200px'
                }}
              >
                {JSON.stringify(message.response, null, 2)}
              </pre>
            ) : (
              <div
                style={{
                  padding: '15px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '8px',
                  border: '1px solid #dee2e6',
                  color: '#6c757d',
                  textAlign: 'center'
                }}
              >
                No response data available
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
