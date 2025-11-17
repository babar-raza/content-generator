import { create } from 'zustand';
import { Agent, Job, LogEntry } from '@/types';
import { Node, Edge } from 'reactflow';

interface WorkflowStore {
  // Workflow state
  nodes: Node[];
  edges: Edge[];
  selectedNode: Node | null;
  
  // Agent state
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  
  // Job state
  currentJob: Job | null;
  jobs: Job[];
  setJobs: (jobs: Job[]) => void;
  setCurrentJob: (job: Job | null) => void;
  
  // Logs
  logs: LogEntry[];
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
  
  // Node management
  setNodes: (nodes: Node[]) => void;
  addNode: (node: Node) => void;
  updateNode: (nodeId: string, data: Partial<Node['data']>) => void;
  removeNode: (nodeId: string) => void;
  
  // Edge management
  setEdges: (edges: Edge[]) => void;
  addEdge: (edge: Edge) => void;
  removeEdge: (edgeId: string) => void;
  
  // Selection
  selectNode: (node: Node | null) => void;
  
  // Workflow operations
  loadWorkflow: (nodes: Node[], edges: Edge[]) => void;
  clearWorkflow: () => void;
  
  // Job updates from WebSocket
  updateJobStatus: (jobId: string, status: Job['status']) => void;
  updateNodeStatus: (nodeId: string, status: string) => void;
}

export const useWorkflowStore = create<WorkflowStore>((set) => ({
  // Initial state
  nodes: [],
  edges: [],
  selectedNode: null,
  agents: [],
  currentJob: null,
  jobs: [],
  logs: [],
  
  // Agents
  setAgents: (agents) => set({ agents }),
  
  // Jobs
  setJobs: (jobs) => set({ jobs }),
  setCurrentJob: (job) => set({ currentJob: job }),
  
  // Logs
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  clearLogs: () => set({ logs: [] }),
  
  // Nodes
  setNodes: (nodes) => set({ nodes }),
  
  addNode: (node) => set((state) => ({
    nodes: [...state.nodes, node],
  })),
  
  updateNode: (nodeId, data) => set((state) => ({
    nodes: state.nodes.map((node) =>
      node.id === nodeId
        ? { ...node, data: { ...node.data, ...data } }
        : node
    ),
  })),
  
  removeNode: (nodeId) => set((state) => ({
    nodes: state.nodes.filter((node) => node.id !== nodeId),
    edges: state.edges.filter(
      (edge) => edge.source !== nodeId && edge.target !== nodeId
    ),
  })),
  
  // Edges
  setEdges: (edges) => set({ edges }),
  
  addEdge: (edge) => set((state) => ({
    edges: [...state.edges, edge],
  })),
  
  removeEdge: (edgeId) => set((state) => ({
    edges: state.edges.filter((edge) => edge.id !== edgeId),
  })),
  
  // Selection
  selectNode: (node) => set({ selectedNode: node }),
  
  // Workflow operations
  loadWorkflow: (nodes, edges) => set({ nodes, edges }),
  
  clearWorkflow: () => set({ nodes: [], edges: [], selectedNode: null }),
  
  // Job updates
  updateJobStatus: (jobId, status) => set((state) => ({
    currentJob: state.currentJob?.job_id === jobId
      ? { ...state.currentJob, status }
      : state.currentJob,
    jobs: state.jobs.map((job) =>
      job.job_id === jobId ? { ...job, status } : job
    ),
  })),
  
  updateNodeStatus: (nodeId, status) => set((state) => ({
    nodes: state.nodes.map((node) =>
      node.id === nodeId
        ? { ...node, data: { ...node.data, status } }
        : node
    ),
  })),
}));

export default useWorkflowStore;
