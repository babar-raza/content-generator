import axios, { AxiosInstance } from 'axios';
import { Agent, Workflow, Job, JobStatus } from '@/types';
import {
  SystemHealth,
  AgentStatus,
  SystemMetrics,
  FlowRealtimeResponse,
  BottleneckResponse,
} from '@/types/monitoring';

class APIClient {
  private client: AxiosInstance;
  private apiClient: AxiosInstance;

  constructor(baseURL: string = '/mcp') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    // Direct API client for monitoring endpoints
    this.apiClient = axios.create({
      baseURL: '/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Agents
  async getAgents(): Promise<Record<string, Agent>> {
    const response = await this.client.get('/agents');
    return response.data.agents || {};
  }

  async getAgentConfig(agentId: string): Promise<Agent> {
    const response = await this.client.get(`/agents/${agentId}`);
    return response.data;
  }

  // Workflows
  async getWorkflows(): Promise<Record<string, Workflow>> {
    const response = await this.client.get('/workflows');
    return response.data.workflows || {};
  }

  async getWorkflow(name: string): Promise<Workflow> {
    const response = await this.client.get(`/workflows/${name}`);
    return response.data;
  }

  async saveWorkflow(workflow: Workflow): Promise<void> {
    await this.client.post('/workflows', workflow);
  }

  async updateWorkflow(name: string, workflow: Workflow): Promise<void> {
    await this.client.put(`/workflows/${name}`, workflow);
  }

  async deleteWorkflow(name: string): Promise<void> {
    await this.client.delete(`/workflows/${name}`);
  }

  // Jobs - Direct REST API (not MCP)
  async createJob(
    workflowId: string, 
    inputs: any, 
    configOverrides?: any
  ): Promise<Job> {
    const response = await this.apiClient.post('/jobs', {
      workflow_id: workflowId,
      inputs: inputs,
      config_overrides: configOverrides
    });
    return response.data;
  }

  async getJobs(
    status?: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<any> {
    let url = `/jobs?limit=${limit}&offset=${offset}`;
    if (status) url += `&status=${status}`;
    
    const response = await this.apiClient.get(url);
    return response.data;
  }

  async getJob(jobId: string): Promise<JobStatus> {
    const response = await this.apiClient.get(`/jobs/${jobId}`);
    return response.data;
  }

  async pauseJob(jobId: string): Promise<void> {
    await this.apiClient.post(`/jobs/${jobId}/pause`);
  }

  async resumeJob(jobId: string): Promise<void> {
    await this.apiClient.post(`/jobs/${jobId}/resume`);
  }

  async cancelJob(jobId: string): Promise<void> {
    await this.apiClient.post(`/jobs/${jobId}/cancel`);
  }

  async generateContent(spec: {
    topic: string;
    template?: string;
    workflow?: string;
    metadata?: any;
    config_overrides?: any;
  }): Promise<any> {
    const response = await this.apiClient.post('/generate', spec);
    return response.data;
  }

  async createBatchJobs(
    workflowId: string,
    jobs: any[],
    batchName?: string
  ): Promise<any> {
    const response = await this.apiClient.post('/batch', {
      workflow_id: workflowId,
      jobs: jobs,
      batch_name: batchName
    });
    return response.data;
  }

  // Configuration
  async getConfig(): Promise<any> {
    const response = await this.client.get('/config/snapshot');
    return response.data;
  }

  async getAgentConfigs(): Promise<any> {
    const response = await this.apiClient.get('/agents');
    return response.data;
  }

  async getWorkflowConfigs(): Promise<any> {
    const response = await this.client.get('/config/workflows');
    return response.data;
  }

  // Monitoring APIs
  async getSystemHealth(): Promise<SystemHealth> {
    const response = await this.apiClient.get('/health');
    return response.data;
  }

  async getAgentStatuses(): Promise<AgentStatus[]> {
    try {
      const response = await this.apiClient.get('/monitoring/agents');
      return response.data.agents || [];
    } catch (error) {
      // Fallback: derive from agents list
      const agents = await this.getAgents();
      return Object.entries(agents).map(([id, agent]) => ({
        agent_id: id,
        name: id,
        status: 'available' as const,
        last_execution: undefined,
        total_executions: 0,
        avg_latency_ms: 0,
        error_rate: 0,
      }));
    }
  }

  async getSystemMetrics(): Promise<SystemMetrics> {
    try {
      const response = await this.apiClient.get('/monitoring/system');
      return response.data;
    } catch (error) {
      // Fallback: derive from jobs
      const jobs = await this.getJobs();
      const activeJobs = jobs.filter(j => j.status === 'running').length;
      const queuedJobs = jobs.filter(j => j.status === 'pending').length;
      
      return {
        timestamp: new Date().toISOString(),
        active_jobs: activeJobs,
        queued_jobs: queuedJobs,
        completed_jobs_today: jobs.filter(j => j.status === 'completed').length,
      };
    }
  }

  async getRealtimeFlows(windowSeconds: number = 60): Promise<FlowRealtimeResponse> {
    const response = await this.apiClient.get(`/flows/realtime?window=${windowSeconds}`);
    return response.data;
  }

  async getBottlenecks(thresholdMs: number = 1000): Promise<BottleneckResponse> {
    const response = await this.apiClient.get(`/flows/bottlenecks?threshold_ms=${thresholdMs}`);
    return response.data;
  }

  async getRunningJobs(): Promise<Job[]> {
    try {
      const response = await this.apiClient.get('/jobs?status=running');
      return response.data.jobs || [];
    } catch (error) {
      // Fallback to all jobs filtered
      const jobs = await this.getJobs();
      return jobs.filter(j => j.status === 'running');
    }
  }

  // Checkpoints
  async listCheckpoints(jobId: string): Promise<any> {
    const response = await this.apiClient.get(`/checkpoints?job_id=${jobId}`);
    return response.data;
  }

  async getCheckpoint(checkpointId: string): Promise<any> {
    const response = await this.apiClient.get(`/checkpoints/${checkpointId}`);
    return response.data;
  }

  async restoreCheckpoint(
    checkpointId: string, 
    resume: boolean = false
  ): Promise<any> {
    const response = await this.apiClient.post(
      `/checkpoints/${checkpointId}/restore`,
      { resume }
    );
    return response.data;
  }

  async deleteCheckpoint(checkpointId: string): Promise<void> {
    await this.apiClient.delete(`/checkpoints/${checkpointId}`);
  }

  async cleanupCheckpoints(
    jobId: string, 
    keepLast: number = 10
  ): Promise<any> {
    const response = await this.apiClient.post('/checkpoints/cleanup', {
      job_id: jobId,
      keep_last: keepLast
    });
    return response.data;
  }

  // Agent Health & Logs
  async getAgentHealth(): Promise<any> {
    const response = await this.apiClient.get('/agents/health');
    return response.data;
  }

  async getAgentHealthById(agentId: string): Promise<any> {
    const response = await this.apiClient.get(`/agents/${agentId}/health`);
    return response.data;
  }

  async getAgentFailures(agentId: string): Promise<any> {
    const response = await this.apiClient.get(`/agents/${agentId}/failures`);
    return response.data;
  }

  async resetAgentHealth(agentId: string): Promise<void> {
    await this.apiClient.post(`/agents/${agentId}/health/reset`);
  }

  async getAgentLogs(agentId: string): Promise<any> {
    const response = await this.apiClient.get(`/agents/${agentId}/logs`);
    return response.data;
  }

  async getJobAgentLogs(jobId: string, agentName: string): Promise<any> {
    const response = await this.apiClient.get(`/jobs/${jobId}/logs/${agentName}`);
    return response.data;
  }

  // Flow History & Active
  async getFlowHistory(correlationId: string): Promise<any> {
    const response = await this.apiClient.get(`/flows/history/${correlationId}`);
    return response.data;
  }

  async getActiveFlows(): Promise<any> {
    const response = await this.apiClient.get('/flows/active');
    return response.data;
  }

  // Debug API
  async createDebugSession(config: any): Promise<any> {
    const response = await this.apiClient.post('/debug/sessions', config);
    return response.data;
  }

  async getDebugSessions(): Promise<any> {
    const response = await this.apiClient.get('/debug/sessions');
    return response.data;
  }

  async getDebugSession(sessionId: string): Promise<any> {
    const response = await this.apiClient.get(`/debug/sessions/${sessionId}`);
    return response.data;
  }

  async deleteDebugSession(sessionId: string): Promise<void> {
    await this.apiClient.delete(`/debug/sessions/${sessionId}`);
  }

  async addBreakpoint(sessionId: string, breakpoint: any): Promise<any> {
    const response = await this.apiClient.post(
      `/debug/sessions/${sessionId}/breakpoints`,
      breakpoint
    );
    return response.data;
  }

  async removeBreakpoint(sessionId: string, breakpointId: string): Promise<void> {
    await this.apiClient.delete(`/debug/sessions/${sessionId}/breakpoints/${breakpointId}`);
  }

  async stepDebug(sessionId: string): Promise<any> {
    const response = await this.apiClient.post(`/debug/sessions/${sessionId}/step`);
    return response.data;
  }

  async continueDebug(sessionId: string): Promise<any> {
    const response = await this.apiClient.post(`/debug/sessions/${sessionId}/continue`);
    return response.data;
  }

  async getDebugTrace(sessionId: string): Promise<any> {
    const response = await this.apiClient.get(`/debug/sessions/${sessionId}/trace`);
    return response.data;
  }

  async getDebugState(jobId: string): Promise<any> {
    const response = await this.apiClient.get(`/debug/state/${jobId}`);
    return response.data;
  }

  // Visualization
  async getWorkflowVisualizations(): Promise<any> {
    const response = await this.apiClient.get('/visualization/workflows');
    return response.data;
  }

  async getWorkflowGraph(workflowId: string): Promise<any> {
    const response = await this.apiClient.get(`/visualization/workflows/${workflowId}`);
    return response.data;
  }

  async renderWorkflow(workflowId: string): Promise<any> {
    const response = await this.apiClient.get(`/visualization/workflows/${workflowId}/render`);
    return response.data;
  }

  async getMonitoringAgents(): Promise<any> {
    const response = await this.apiClient.get('/monitoring/agents');
    return response.data;
  }

  async getMonitoringAgent(agentId: string): Promise<any> {
    const response = await this.apiClient.get(`/monitoring/agents/${agentId}`);
    return response.data;
  }

  // Ingestion APIs
  async ingestKB(kbPath: string): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'ingest/kb',
      params: { kb_path: kbPath },
      id: `ingest_kb_${Date.now()}`
    });
    return response.data;
  }

  async ingestDocs(docsPath: string): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'ingest/docs',
      params: { docs_path: docsPath },
      id: `ingest_docs_${Date.now()}`
    });
    return response.data;
  }

  async ingestAPI(apiPath: string): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'ingest/api',
      params: { api_path: apiPath },
      id: `ingest_api_${Date.now()}`
    });
    return response.data;
  }

  async ingestBlog(blogPath: string): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'ingest/blog',
      params: { blog_path: blogPath },
      id: `ingest_blog_${Date.now()}`
    });
    return response.data;
  }

  async ingestTutorial(tutorialPath: string): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'ingest/tutorial',
      params: { tutorial_path: tutorialPath },
      id: `ingest_tutorial_${Date.now()}`
    });
    return response.data;
  }

  // Topic Discovery API
  async discoverTopics(params: {
    kb_path?: string;
    docs_path?: string;
    max_topics?: number;
  }): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'topics/discover',
      params,
      id: `topics_discover_${Date.now()}`
    });
    return response.data;
  }

  // Agent Invocation API
  async invokeAgent(agentId: string, input: any, context?: any): Promise<any> {
    const response = await this.client.post('/request', {
      method: 'agent/invoke',
      params: {
        agent_id: agentId,
        input,
        context
      },
      id: `agent_invoke_${Date.now()}`
    });
    return response.data;
  }

  // Mesh Orchestration API
  async getMeshAgents(): Promise<any> {
    const response = await this.apiClient.get('/mesh/agents');
    return response.data;
  }

  async executeMeshWorkflow(params: {
    initial_agent: string;
    input_data: any;
    workflow_name?: string;
  }): Promise<any> {
    const response = await this.apiClient.post('/mesh/execute', params);
    return response.data;
  }

  async getMeshTrace(jobId: string): Promise<any> {
    const response = await this.apiClient.get(`/mesh/trace/${jobId}`);
    return response.data;
  }

  async getMeshStats(): Promise<any> {
    const response = await this.apiClient.get('/mesh/stats');
    return response.data;
  }
}

export const apiClient = new APIClient();
export default apiClient;
