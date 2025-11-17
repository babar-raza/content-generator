// Add these fields to the JobStatus interface in src/web/static/src/types/index.ts
// Insert after the metadata?: any; field (around line 11-12)

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
  retry_count?: number;        // ADD THIS LINE
  max_retries?: number;        // ADD THIS LINE
  archived_at?: string;        // ADD THIS LINE
  workflow_id?: string;        // ADD THIS LINE
  logs?: LogEntry[];
  metrics?: {
    nodes_completed: number;
    nodes_total: number;
    runtime_seconds: number;
  };
}
