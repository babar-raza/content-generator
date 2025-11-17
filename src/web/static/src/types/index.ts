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
  workflow_id: string;
  status: string;
  progress?: number;
  current_stage?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
  metadata?: any;
  inputs?: any;
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
  progress?: number;
  current_stage?: string;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
  metadata?: any;
  logs?: LogEntry[];
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

export interface JobListResponse {
  jobs: JobStatus[];
  total: number;
}

export interface JobResponse {
  job_id: string;
  status: string;
  message?: string;
}

export interface BatchJobResponse {
  batch_id: string;
  job_ids: string[];
  status: string;
  message?: string;
}

export interface RunSpec {
  topic: string;
  template?: string;
  workflow?: string;
  metadata?: any;
  config_overrides?: any;
}

export interface CheckpointMetadata {
  checkpoint_id: string;
  job_id: string;
  step_name: string;
  timestamp: string;
  workflow_version: string;
  file_path?: string;
  size_bytes?: number;
}

export interface CheckpointResponse {
  checkpoint_id: string;
  job_id: string;
  step_name: string;
  timestamp: string;
  workflow_version: string;
  state_snapshot?: any;
  metadata?: any;
}

export interface CheckpointList {
  checkpoints: CheckpointMetadata[];
  total: number;
}

export interface RestoreResponse {
  job_id: string;
  job_status: string;
  message?: string;
  checkpoint_id: string;
}

export interface CleanupResponse {
  deleted_count: number;
  kept_count: number;
  deleted_checkpoints: string[];
}
