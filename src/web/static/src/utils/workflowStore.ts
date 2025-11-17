import { create } from 'zustand';
import { Node, Edge, Connection, addEdge, applyNodeChanges, applyEdgeChanges, NodeChange, EdgeChange } from 'reactflow';
import { Agent, Workflow } from '@/types';

interface WorkflowState {
  nodes: Node[];
  edges: Edge[];
  selectedNode: Node | null;
  currentWorkflow: Workflow | null;
  isDirty: boolean;
  
  // Actions
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  addNode: (type: string, agent?: Agent, position?: { x: number; y: number }) => void;
  removeNode: (nodeId: string) => void;
  updateNodeData: (nodeId: string, data: any) => void;
  selectNode: (node: Node | null) => void;
  loadWorkflow: (workflow: Workflow) => void;
  clearWorkflow: () => void;
  getWorkflowData: () => Workflow;
  setDirty: (dirty: boolean) => void;
}

let nodeIdCounter = 0;

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNode: null,
  currentWorkflow: null,
  isDirty: false,

  setNodes: (nodes) => set({ nodes }),
  
  setEdges: (edges) => set({ edges }),

  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
      isDirty: true,
    });
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
      isDirty: true,
    });
  },

  onConnect: (connection) => {
    const { nodes, edges } = get();
    
    // Validate connection
    const sourceNode = nodes.find((n) => n.id === connection.source);
    const targetNode = nodes.find((n) => n.id === connection.target);
    
    if (!sourceNode || !targetNode) return;
    
    // Check if connection already exists
    const existingEdge = edges.find(
      (e) => e.source === connection.source && e.target === connection.target
    );
    
    if (existingEdge) return;
    
    set({
      edges: addEdge({ ...connection, type: 'smoothstep' }, edges),
      isDirty: true,
    });
  },

  addNode: (type, agent, position) => {
    const { nodes } = get();
    const id = `node-${++nodeIdCounter}`;
    
    const newNode: Node = {
      id,
      type: type === 'agent' ? 'default' : type,
      position: position || { x: 250, y: 250 },
      data: {
        label: agent ? agent.description : type === 'start' ? 'Start' : 'End',
        agentId: agent?.id,
        agent,
        status: 'idle',
      },
    };
    
    set({
      nodes: [...nodes, newNode],
      isDirty: true,
    });
    
    return newNode;
  },

  removeNode: (nodeId) => {
    const { nodes, edges } = get();
    set({
      nodes: nodes.filter((n) => n.id !== nodeId),
      edges: edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNode: null,
      isDirty: true,
    });
  },

  updateNodeData: (nodeId, data) => {
    const { nodes } = get();
    set({
      nodes: nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
      isDirty: true,
    });
  },

  selectNode: (node) => {
    set({ selectedNode: node });
  },

  loadWorkflow: (workflow) => {
    set({
      nodes: workflow.nodes || [],
      edges: workflow.edges || [],
      currentWorkflow: workflow,
      isDirty: false,
      selectedNode: null,
    });
  },

  clearWorkflow: () => {
    set({
      nodes: [],
      edges: [],
      currentWorkflow: null,
      isDirty: false,
      selectedNode: null,
    });
  },

  getWorkflowData: () => {
    const { nodes, edges, currentWorkflow } = get();
    return {
      name: currentWorkflow?.name || 'untitled',
      description: currentWorkflow?.description || '',
      nodes: nodes.map((node) => ({
        id: node.id,
        type: node.type as 'agent' | 'start' | 'end',
        position: node.position,
        data: {
          label: node.data.label,
          agentId: node.data.agentId,
          config: node.data.config,
        },
      })),
      edges: edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle || undefined,
        targetHandle: edge.targetHandle || undefined,
        type: edge.type,
      })),
    };
  },

  setDirty: (dirty) => set({ isDirty: dirty }),
}));
