import { useState, useEffect, useCallback } from 'react';
import { Agent, Workflow, Job, JobStatus, WebSocketEvent } from '@/types';
import apiClient from '@/api/client';
import { wsManager } from '@/websocket/connection';

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getAgentConfigs();
        
        // Handle both response formats
        if (Array.isArray(data.agents)) {
          setAgents(data.agents);
        } else if (typeof data.agents === 'object') {
          // Convert object to array
          const agentArray = Object.entries(data.agents).map(([id, config]: [string, any]) => ({
            id: config.id || id,
            version: config.version || '1.0.0',
            description: config.description || '',
            category: config.category || 'general',
            entrypoint: config.entrypoint || {
              type: 'python',
              module: '',
              function: '',
              async: false
            },
            contract: config.contract || {
              inputs: { type: 'object' },
              outputs: { type: 'object' }
            },
            capabilities: config.capabilities || {
              stateful: false,
              async: false,
              model_switchable: false
            },
            resources: config.resources || {
              max_runtime_s: 300,
              max_tokens: 4000,
              max_memory_mb: 512
            }
          }));
          setAgents(agentArray);
        } else {
          setAgents([]);
        }
        
        setError(null);
      } catch (err) {
        console.error('Failed to fetch agents:', err);
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchAgents();
  }, []);

  return { agents, loading, error };
}

export function useWorkflows() {
  const [workflows, setWorkflows] = useState<Record<string, Workflow>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchWorkflows = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getWorkflowConfigs();
      setWorkflows(data.workflows || {});
      setError(null);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  const saveWorkflow = useCallback(async (workflow: Workflow) => {
    try {
      await apiClient.saveWorkflow(workflow);
      await fetchWorkflows();
    } catch (err) {
      throw err;
    }
  }, [fetchWorkflows]);

  return { workflows, loading, error, saveWorkflow, refresh: fetchWorkflows };
}

export function useJobs() {
  const [jobs, setJobs] = useState<JobStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient.getJobs();
      setJobs(data.jobs || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    
    // Poll every 3 seconds for updates
    const interval = setInterval(fetchJobs, 3000);
    
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const createJob = useCallback(async (
    workflowId: string,
    inputs: any,
    configOverrides?: any
  ): Promise<any> => {
    try {
      const job = await apiClient.createJob(workflowId, inputs, configOverrides);
      await fetchJobs(); // Refresh list
      return job;
    } catch (err) {
      console.error('Failed to create job:', err);
      throw err;
    }
  }, [fetchJobs]);

  const pauseJob = useCallback(async (jobId: string) => {
    try {
      await apiClient.pauseJob(jobId);
      await fetchJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to pause job:', err);
      throw err;
    }
  }, [fetchJobs]);

  const resumeJob = useCallback(async (jobId: string) => {
    try {
      await apiClient.resumeJob(jobId);
      await fetchJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to resume job:', err);
      throw err;
    }
  }, [fetchJobs]);

  const cancelJob = useCallback(async (jobId: string) => {
    try {
      await apiClient.cancelJob(jobId);
      await fetchJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to cancel job:', err);
      throw err;
    }
  }, [fetchJobs]);

  return {
    jobs,
    loading,
    error,
    createJob,
    pauseJob,
    resumeJob,
    cancelJob,
    refresh: fetchJobs,
  };
}

export function useJobUpdates(jobId: string | null) {
  const [events, setEvents] = useState<WebSocketEvent[]>([]);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!jobId) return;

    const connection = wsManager.getConnection(jobId);
    
    const connectWebSocket = async () => {
      try {
        await connection.connect();
        setConnected(true);
      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        setConnected(false);
      }
    };

    connectWebSocket();

    const unsubscribe = connection.subscribe((event: WebSocketEvent) => {
      setEvents((prev) => [...prev, event]);
      
      // Update status based on event type
      if (event.type === 'NODE.START' || event.type === 'NODE.OUTPUT' || 
          event.type === 'RUN.FINISHED' || event.type === 'NODE.ERROR') {
        apiClient.getJob(jobId).then(setStatus).catch(console.error);
      }
    });

    // Fetch initial status
    apiClient.getJob(jobId).then(setStatus).catch(console.error);

    return () => {
      unsubscribe();
      wsManager.disconnect(jobId);
      setConnected(false);
    };
  }, [jobId]);

  const sendCommand = useCallback((command: any) => {
    if (!jobId) return;
    const connection = wsManager.getConnection(jobId);
    connection.send(command);
  }, [jobId]);

  return {
    events,
    status,
    connected,
    sendCommand,
  };
}

export function useConfig() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getConfig();
        setConfig(data);
        setError(null);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  return { config, loading, error };
}
