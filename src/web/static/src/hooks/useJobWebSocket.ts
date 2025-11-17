import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket, ConnectionStatus } from './useWebSocket';
import { JobStatus, WebSocketEvent } from '@/types';

interface JobWebSocketData {
  type: string;
  data: any;
  timestamp: string;
}

interface UseJobWebSocketOptions {
  jobId: string | null;
  onJobUpdate?: (update: JobWebSocketData) => void;
  enabled?: boolean;
  fallbackPolling?: boolean;
  pollingInterval?: number;
}

interface UseJobWebSocketReturn {
  jobStatus: JobStatus | null;
  events: WebSocketEvent[];
  status: ConnectionStatus;
  error: string | null;
  send: (data: any) => void;
  reconnect: () => void;
}

export function useJobWebSocket(
  options: UseJobWebSocketOptions
): UseJobWebSocketReturn {
  const { 
    jobId, 
    onJobUpdate, 
    enabled = true,
    fallbackPolling = true,
    pollingInterval = 5000 
  } = options;

  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [shouldPoll, setShouldPoll] = useState(false);
  const pollingTimerRef = useRef<number | null>(null);

  const handleMessage = useCallback((data: JobWebSocketData) => {
    console.log('Job WebSocket message:', data);

    // Create event from message
    const event: WebSocketEvent = {
      type: data.type,
      timestamp: data.timestamp,
      job_id: jobId || '',
      data: data.data,
    };

    setEvents((prev) => [...prev, event]);
    
    // Update job status based on message type
    if (data.type === 'job.status' && data.data) {
      setJobStatus(data.data);
    } else if (data.type.startsWith('job.')) {
      // Update relevant fields
      setJobStatus((prev) => {
        if (!prev) return null;
        
        const updates: Partial<JobStatus> = {};
        
        if (data.data.status) {
          updates.status = data.data.status;
        }
        if (data.data.progress !== undefined) {
          updates.progress = data.data.progress;
        }
        if (data.data.current_node) {
          updates.current_node = data.data.current_node;
        }
        
        return { ...prev, ...updates };
      });
    }

    onJobUpdate?.(data);
  }, [jobId, onJobUpdate]);

  const { 
    data, 
    status, 
    error, 
    send, 
    reconnect 
  } = useWebSocket<JobWebSocketData>({
    url: jobId ? `/ws/jobs/${jobId}` : '',
    onMessage: handleMessage,
    enabled: enabled && !!jobId,
    reconnectAttempts: 5,
    reconnectDelay: 1000,
  });

  // Fallback polling when WebSocket fails
  useEffect(() => {
    if (!fallbackPolling || !jobId) return;

    // Enable polling if connection fails after max retries
    if (status === 'error' && error?.includes('Max reconnection')) {
      setShouldPoll(true);
    } else if (status === 'connected') {
      setShouldPoll(false);
    }
  }, [status, error, fallbackPolling, jobId]);

  // Polling implementation
  useEffect(() => {
    if (!shouldPoll || !jobId) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    const pollJobStatus = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}/status`);
        if (response.ok) {
          const status = await response.json();
          setJobStatus(status);
        }
      } catch (err) {
        console.error('Polling failed:', err);
      }
    };

    // Initial poll
    pollJobStatus();

    // Set up interval
    pollingTimerRef.current = window.setInterval(pollJobStatus, pollingInterval);

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [shouldPoll, jobId, pollingInterval]);

  // Request initial status when connected
  useEffect(() => {
    if (status === 'connected' && jobId) {
      send({ type: 'get_status' });
    }
  }, [status, jobId, send]);

  // Clear events when job changes
  useEffect(() => {
    setEvents([]);
    setJobStatus(null);
  }, [jobId]);

  return {
    jobStatus,
    events,
    status: shouldPoll ? 'disconnected' : status,
    error,
    send,
    reconnect,
  };
}

export default useJobWebSocket;
