import { useEffect, useState, useRef, useCallback } from 'react';

export interface LiveFlowMessage {
  type: 'connected' | 'agent_started' | 'agent_completed' | 'agent_failed' | 'data_flow' | 'progress_update';
  job_id?: string;
  agent_id?: string;
  from_agent?: string;
  to_agent?: string;
  output?: any;
  error?: string;
  duration?: number;
  data_size?: number;
  progress?: number;
  message?: string;
  timestamp: string;
  correlation_id?: string;
}

export interface UseWebSocketResult {
  socket: WebSocket | null;
  isConnected: boolean;
  lastMessage: LiveFlowMessage | null;
  sendMessage: (message: any) => void;
  disconnect: () => void;
}

export function useWebSocket(url: string): UseWebSocketResult {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<LiveFlowMessage | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 10;
  const isManualClose = useRef(false);

  const connect = useCallback(() => {
    if (isManualClose.current) return;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') {
            return;
          }
          
          const data: LiveFlowMessage = JSON.parse(event.data);
          setLastMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        setSocket(null);

        if (!isManualClose.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          const delay = 1000 * Math.pow(2, reconnectAttemptsRef.current - 1);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimerRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        }
      };

      setSocket(ws);
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
    }
  }, [url]);

  useEffect(() => {
    connect();

    return () => {
      isManualClose.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (socket) {
        socket.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: any) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, [socket]);

  const disconnect = useCallback(() => {
    isManualClose.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
    }
    if (socket) {
      socket.close();
    }
  }, [socket]);

  return {
    socket,
    isConnected,
    lastMessage,
    sendMessage,
    disconnect
  };
}
