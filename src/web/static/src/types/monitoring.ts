export interface Agent {
  id: string;
  version: string;
  description: string;
  category?: string;
  entrypoint: {
    type: string;
    module: string;
    function: string;
    async: boolean;
  };
  contract: {
    inputs: {
      type: string;
      required?: string[];
      properties?: Record<string, any>;
    };
    outputs: {
      type: string;
      required?: string[];
      properties?: Record<string, any>;
    };
  };
  capabilities: {
    stateful: boolean;
    async: boolean;
    model_switchable: boolean;
    side_effects?: string;
  };
  resources: {
    max_runtime_s: number;
    max_tokens: number;
    max_memory_mb: number;
  };
}

export interface Workflow {
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export type WorkflowTemplate = Workflow;

export interface WorkflowNode {
  id: string;
  type: 'agent' | 'start' | 'end';
  position: { x: number; y: number };
  data: {
    label: string;
    agentId?: string;
    config?: Record<string, any>;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: string;
}

export interface Job {
  job_id: string;
  workflow_name: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  started_at: string;
  completed_at?: string;
  current_node?: string;
  error?: string;
}

export interface WebSocketEvent {
  type: string;
  timestamp: string;
  job_id: string;
  data: any;
}

export type JobUpdate = WebSocketEvent;

export interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  current_node?: string;
  logs: LogEntry[];
  metrics?: {
    nodes_completed: number;
    nodes_total: number;
    runtime_seconds: number;
  };
}

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  node_id?: string;
  message: string;
  agent?: string;
}

export interface AgentCategory {
  name: string;
  icon: string;
  agents: Agent[];
}

export interface NodeData {
  label: string;
  agentId?: string;
  agent?: Agent;
  config?: Record<string, any>;
  status?: 'idle' | 'running' | 'completed' | 'error';
}

export interface EdgeData {
  validated?: boolean;
  label?: string;
}

// Monitoring types
export interface SystemHealth {
  status: string;
  timestamp: string;
  components: Record<string, ComponentHealth>;
  version?: string;
  uptime?: number;
}

export interface ComponentHealth {
  status: string;
  message?: string;
  details?: Record<string, any>;
}

export interface AgentStatus {
  agent_id: string;
  name: string;
  status: 'available' | 'busy' | 'error' | 'offline';
  last_execution?: string;
  total_executions?: number;
  avg_latency_ms?: number;
  error_rate?: number;
}

export interface SystemMetrics {
  timestamp: string;
  cpu_percent?: number;
  memory_percent?: number;
  memory_mb?: number;
  active_jobs: number;
  queued_jobs: number;
  completed_jobs_today?: number;
  agents_active?: number;
}

export interface FlowEvent {
  flow_id: string;
  source_agent: string;
  target_agent: string;
  event_type: string;
  timestamp: string;
  correlation_id: string;
  status: string;
  latency_ms?: number;
  data_size_bytes?: number;
  metadata?: Record<string, any>;
}

export interface FlowRealtimeResponse {
  flows: FlowEvent[];
  window_seconds: number;
  count: number;
  timestamp: string;
}

export interface BottleneckReport {
  agent_id: string;
  avg_latency_ms: number;
  max_latency_ms: number;
  flow_count: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
}

export interface BottleneckResponse {
  bottlenecks: BottleneckReport[];
  threshold_ms: number;
  count: number;
  timestamp: string;
}
