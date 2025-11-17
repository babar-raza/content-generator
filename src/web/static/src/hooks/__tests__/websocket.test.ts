import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useJobWebSocket } from '../useJobWebSocket';
import { useAgentWebSocket } from '../useAgentWebSocket';
import { useWorkflowWebSocket } from '../useWorkflowWebSocket';

// Mock WebSocket
class MockWebSocket {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  readyState: number = WebSocket.CONNECTING;

  constructor(public url: string) {
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 0);
  }

  send(data: string) {
    console.log('MockWebSocket send:', data);
  }

  close() {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  // Helper method to simulate receiving a message
  simulateMessage(data: any) {
    const event = new MessageEvent('message', {
      data: JSON.stringify(data),
    });
    this.onmessage?.(event);
  }
}

describe('WebSocket Hooks', () => {
  let originalWebSocket: typeof WebSocket;

  beforeEach(() => {
    originalWebSocket = global.WebSocket;
    global.WebSocket = MockWebSocket as any;
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
  });

  describe('useJobWebSocket', () => {
    it('should connect to job WebSocket endpoint', async () => {
      const { result } = renderHook(() =>
        useJobWebSocket({ jobId: 'test-job-123' })
      );

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });
    });

    it('should handle job status messages', async () => {
      const { result } = renderHook(() =>
        useJobWebSocket({ jobId: 'test-job-123' })
      );

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });

      // Simulate receiving a job status message
      const ws = (global.WebSocket as any).mock?.instances?.[0];
      if (ws) {
        ws.simulateMessage({
          type: 'job.status',
          data: {
            job_id: 'test-job-123',
            status: 'running',
            progress: 50,
          },
          timestamp: new Date().toISOString(),
        });

        await waitFor(() => {
          expect(result.current.jobStatus?.status).toBe('running');
          expect(result.current.jobStatus?.progress).toBe(50);
        });
      }
    });

    it('should reconnect on disconnect', async () => {
      const { result } = renderHook(() =>
        useJobWebSocket({ jobId: 'test-job-123' })
      );

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });

      // Simulate disconnect
      const ws = (global.WebSocket as any).mock?.instances?.[0];
      if (ws) {
        ws.close();
      }

      await waitFor(() => {
        expect(result.current.status).toBe('connecting');
      });
    });
  });

  describe('useAgentWebSocket', () => {
    it('should connect to agents WebSocket endpoint', async () => {
      const { result } = renderHook(() => useAgentWebSocket());

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });
    });

    it('should handle agent execution messages', async () => {
      const { result } = renderHook(() => useAgentWebSocket());

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });

      const ws = (global.WebSocket as any).mock?.instances?.[0];
      if (ws) {
        ws.simulateMessage({
          type: 'agent.started',
          data: {
            agent_id: 'test-agent',
          },
          timestamp: new Date().toISOString(),
        });

        await waitFor(() => {
          expect(result.current.executions.length).toBeGreaterThan(0);
          expect(result.current.executions[0].agent_id).toBe('test-agent');
          expect(result.current.executions[0].status).toBe('running');
        });
      }
    });
  });

  describe('useWorkflowWebSocket', () => {
    it('should connect to workflow WebSocket endpoint', async () => {
      const { result } = renderHook(() => useWorkflowWebSocket());

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });
    });

    it('should handle workflow state messages', async () => {
      const { result } = renderHook(() => useWorkflowWebSocket());

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });

      const ws = (global.WebSocket as any).mock?.instances?.[0];
      if (ws) {
        ws.simulateMessage({
          type: 'workflow.state',
          data: {
            workflow_id: 'test-workflow',
            status: 'running',
          },
          timestamp: new Date().toISOString(),
        });

        await waitFor(() => {
          expect(result.current.workflowState?.workflow_id).toBe('test-workflow');
          expect(result.current.workflowState?.status).toBe('running');
        });
      }
    });

    it('should track agent executions for visualization', async () => {
      const { result } = renderHook(() => useWorkflowWebSocket());

      await waitFor(() => {
        expect(result.current.status).toBe('connected');
      });

      const ws = (global.WebSocket as any).mock?.instances?.[0];
      if (ws) {
        ws.simulateMessage({
          type: 'agent.execution',
          data: {
            source_agent: 'agent-a',
            target_agent: 'agent-b',
            status: 'running',
            correlation_id: 'test-123',
          },
          timestamp: new Date().toISOString(),
        });

        await waitFor(() => {
          expect(result.current.agentExecutions.length).toBeGreaterThan(0);
          expect(result.current.agentExecutions[0].source_agent).toBe('agent-a');
          expect(result.current.agentExecutions[0].target_agent).toBe('agent-b');
        });
      }
    });
  });
});
