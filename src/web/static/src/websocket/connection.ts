import { WebSocketEvent } from '@/types';

type EventHandler = (event: WebSocketEvent) => void;

export class WebSocketConnection {
  private ws: WebSocket | null = null;
  private url: string;
  private jobId: string;
  private handlers: Set<EventHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private reconnectTimer: number | null = null;
  private isManualClose = false;

  constructor(jobId: string, baseURL: string = '') {
    this.jobId = jobId;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = baseURL || window.location.host;
    this.url = `${protocol}//${host}/ws/mesh?job=${jobId}`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.isManualClose = false;
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log(`WebSocket connected for job ${this.jobId}`);
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data: WebSocketEvent = JSON.parse(event.data);
            this.handlers.forEach((handler) => handler(data));
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = () => {
          console.log(`WebSocket disconnected for job ${this.jobId}`);
          if (!this.isManualClose) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(
      `Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`
    );

    this.reconnectTimer = window.setTimeout(() => {
      this.connect().catch((error) => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  disconnect(): void {
    this.isManualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.handlers.clear();
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Connection manager for multiple jobs
class WebSocketManager {
  private connections: Map<string, WebSocketConnection> = new Map();

  getConnection(jobId: string): WebSocketConnection {
    if (!this.connections.has(jobId)) {
      const connection = new WebSocketConnection(jobId);
      this.connections.set(jobId, connection);
    }
    return this.connections.get(jobId)!;
  }

  disconnect(jobId: string): void {
    const connection = this.connections.get(jobId);
    if (connection) {
      connection.disconnect();
      this.connections.delete(jobId);
    }
  }

  disconnectAll(): void {
    this.connections.forEach((connection) => connection.disconnect());
    this.connections.clear();
  }
}

export const wsManager = new WebSocketManager();
export default wsManager;
