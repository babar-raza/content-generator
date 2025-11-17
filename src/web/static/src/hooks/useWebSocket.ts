import { useEffect, useRef, useState, useCallback } from 'react';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'error';

interface UseWebSocketOptions<T> {
  url: string;
  onMessage?: (data: T) => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
  enabled?: boolean;
}

interface UseWebSocketReturn<T> {
  data: T | null;
  status: ConnectionStatus;
  error: string | null;
  send: (data: any) => void;
  reconnect: () => void;
}

export function useWebSocket<T = any>(
  options: UseWebSocketOptions<T>
): UseWebSocketReturn<T> {
  const {
    url,
    onMessage,
    onError,
    reconnectAttempts = 5,
    reconnectDelay = 1000,
    enabled = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const isManualCloseRef = useRef(false);

  const connect = useCallback(() => {
    if (!enabled || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      setStatus('connecting');
      setError(null);

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}${url}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected: ${url}`);
        setStatus('connected');
        reconnectCountRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const parsedData = JSON.parse(event.data);
          setData(parsedData);
          onMessage?.(parsedData);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setStatus('error');
        setError('Connection error');
        onError?.(event);
      };

      ws.onclose = () => {
        console.log(`WebSocket closed: ${url}`);
        
        if (!isManualCloseRef.current && enabled) {
          setStatus('disconnected');
          
          if (reconnectCountRef.current < reconnectAttempts) {
            const delay = reconnectDelay * Math.pow(2, reconnectCountRef.current);
            console.log(
              `Reconnecting in ${delay}ms (attempt ${reconnectCountRef.current + 1}/${reconnectAttempts})`
            );
            
            reconnectTimerRef.current = window.setTimeout(() => {
              reconnectCountRef.current++;
              connect();
            }, delay);
          } else {
            setError('Max reconnection attempts reached');
          }
        } else {
          setStatus('disconnected');
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [url, enabled, onMessage, onError, reconnectAttempts, reconnectDelay]);

  const disconnect = useCallback(() => {
    isManualCloseRef.current = true;
    
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus('disconnected');
  }, []);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    isManualCloseRef.current = false;
    reconnectCountRef.current = 0;
    connect();
  }, [connect, disconnect]);

  useEffect(() => {
    if (enabled) {
      isManualCloseRef.current = false;
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    data,
    status,
    error,
    send,
    reconnect,
  };
}

export default useWebSocket;
