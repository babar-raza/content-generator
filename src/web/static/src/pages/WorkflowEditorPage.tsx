import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useWorkflowStore } from '@/utils/workflowStore';
import WorkflowEditor from '@/components/WorkflowEditor';
import AgentPalette from '@/components/AgentPalette';
import WorkflowValidator, { ValidationResult } from '@/components/workflow/WorkflowValidator';
import NodeEditor from '@/components/workflow/NodeEditor';
import { Node } from 'reactflow';

interface Agent {
  id: string;
  description: string;
  category?: string;
  capabilities: {
    async: boolean;
    stateful: boolean;
    model_switchable: boolean;
  };
}

const WorkflowEditorPage: React.FC = () => {
  const navigate = useNavigate();
  const { workflowId } = useParams<{ workflowId?: string }>();
  
  const [agents, setAgents] = useState<Record<string, Agent>>({});
  const [agentsList, setAgentsList] = useState<Agent[]>([]);
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string>(workflowId || '');
  const [workflowName, setWorkflowName] = useState<string>('');
  const [workflowDescription, setWorkflowDescription] = useState<string>('');
  const [validationResult, setValidationResult] = useState<ValidationResult>({
    valid: true,
    errors: [],
    warnings: []
  });
  const [editingNode, setEditingNode] = useState<Node | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showNewWorkflowDialog, setShowNewWorkflowDialog] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const {
    nodes,
    edges,
    selectedNode,
    isDirty,
    loadWorkflow,
    clearWorkflow,
    getWorkflowData,
    updateNodeData,
    setDirty
  } = useWorkflowStore();

  // Load agents
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        
        // Convert array to object keyed by id
        const agentsMap: Record<string, Agent> = {};
        data.agents.forEach((agent: Agent) => {
          agentsMap[agent.id] = agent;
        });
        
        setAgents(agentsMap);
        setAgentsList(data.agents);
      } catch (error) {
        console.error('Failed to load agents:', error);
      }
    };

    fetchAgents();
  }, []);

  // Load available workflows
  useEffect(() => {
    const fetchWorkflows = async () => {
      try {
        const response = await fetch('/api/workflows/editor/list');
        const data = await response.json();
        setWorkflows(data.workflows || []);
      } catch (error) {
        console.error('Failed to load workflows:', error);
      }
    };

    fetchWorkflows();
  }, []);

  // Load workflow if ID provided
  useEffect(() => {
    if (workflowId) {
      handleLoadWorkflow(workflowId);
    }
  }, [workflowId]);

  const handleLoadWorkflow = async (id: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/workflows/editor/${id}`);
      if (!response.ok) {
        throw new Error('Failed to load workflow');
      }
      
      const workflow = await response.json();
      
      // Load into store
      loadWorkflow({
        name: workflow.name,
        description: workflow.description,
        nodes: workflow.nodes,
        edges: workflow.edges
      });
      
      setCurrentWorkflowId(id);
      setWorkflowName(workflow.name);
      setWorkflowDescription(workflow.description || '');
      setSaveMessage({ type: 'success', text: 'Workflow loaded successfully' });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      console.error('Failed to load workflow:', error);
      setSaveMessage({ type: 'error', text: 'Failed to load workflow' });
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveWorkflow = async () => {
    if (!workflowName.trim()) {
      setSaveMessage({ type: 'error', text: 'Please enter a workflow name' });
      setTimeout(() => setSaveMessage(null), 3000);
      return;
    }

    if (!validationResult.valid) {
      setSaveMessage({ type: 'error', text: 'Cannot save workflow with validation errors' });
      setTimeout(() => setSaveMessage(null), 3000);
      return;
    }

    setIsSaving(true);
    try {
      const workflowData = {
        id: currentWorkflowId || workflowName.toLowerCase().replace(/\s+/g, '_'),
        name: workflowName,
        description: workflowDescription,
        nodes,
        edges,
        metadata: {
          category: 'custom',
          version: '1.0'
        }
      };

      const response = await fetch('/api/workflows/editor/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(workflowData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail?.message || 'Failed to save workflow');
      }

      const result = await response.json();
      setCurrentWorkflowId(result.id);
      setDirty(false);
      setSaveMessage({ type: 'success', text: 'Workflow saved successfully' });
      
      // Refresh workflows list
      const workflowsResponse = await fetch('/api/workflows/editor/list');
      const workflowsData = await workflowsResponse.json();
      setWorkflows(workflowsData.workflows || []);
      
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error: any) {
      console.error('Failed to save workflow:', error);
      setSaveMessage({ type: 'error', text: error.message || 'Failed to save workflow' });
      setTimeout(() => setSaveMessage(null), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestRun = async () => {
    if (!validationResult.valid) {
      setSaveMessage({ type: 'error', text: 'Cannot test run workflow with validation errors' });
      setTimeout(() => setSaveMessage(null), 3000);
      return;
    }

    try {
      const workflowData = {
        id: currentWorkflowId || 'test_workflow',
        name: workflowName || 'Test Workflow',
        description: workflowDescription,
        nodes,
        edges
      };

      const response = await fetch('/api/workflows/editor/test-run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(workflowData),
      });

      if (!response.ok) {
        throw new Error('Test run failed');
      }

      const result = await response.json();
      setSaveMessage({ type: 'success', text: `Test run successful: ${result.steps} steps validated` });
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (error) {
      console.error('Test run failed:', error);
      setSaveMessage({ type: 'error', text: 'Test run failed' });
      setTimeout(() => setSaveMessage(null), 3000);
    }
  };

  const handleNewWorkflow = () => {
    clearWorkflow();
    setCurrentWorkflowId('');
    setWorkflowName('');
    setWorkflowDescription('');
    setShowNewWorkflowDialog(false);
    navigate('/workflow-editor');
  };

  const handleNodeDoubleClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setEditingNode(node);
  }, []);

  const handleSaveNode = useCallback((updatedNode: Node) => {
    updateNodeData(updatedNode.id, updatedNode.data);
    setEditingNode(null);
  }, [updateNodeData]);

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex-1 max-w-xl">
            <input
              type="text"
              value={workflowName}
              onChange={(e) => {
                setWorkflowName(e.target.value);
                setDirty(true);
              }}
              placeholder="Workflow Name"
              className="text-2xl font-semibold text-gray-900 bg-transparent border-none focus:outline-none focus:ring-0 w-full"
            />
            <input
              type="text"
              value={workflowDescription}
              onChange={(e) => {
                setWorkflowDescription(e.target.value);
                setDirty(true);
              }}
              placeholder="Description (optional)"
              className="text-sm text-gray-600 bg-transparent border-none focus:outline-none focus:ring-0 w-full mt-1"
            />
          </div>

          <div className="flex items-center gap-3">
            {/* Workflow Selector */}
            <select
              value={currentWorkflowId}
              onChange={(e) => {
                if (e.target.value === '__new__') {
                  setShowNewWorkflowDialog(true);
                } else if (e.target.value) {
                  handleLoadWorkflow(e.target.value);
                }
              }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">New Workflow</option>
              {workflows.map((wf) => (
                <option key={wf.id} value={wf.id}>
                  {wf.name}
                </option>
              ))}
              <option value="__new__">+ Create New</option>
            </select>

            {/* Action Buttons */}
            <button
              onClick={handleTestRun}
              disabled={!validationResult.valid || nodes.length === 0}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Test Run
            </button>

            <button
              onClick={handleSaveWorkflow}
              disabled={!isDirty || !validationResult.valid || isSaving || nodes.length === 0}
              className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSaving ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                  </svg>
                  Save
                </>
              )}
            </button>
          </div>
        </div>

        {/* Save Message */}
        {saveMessage && (
          <div className={`mt-3 px-4 py-2 rounded-lg ${
            saveMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {saveMessage.text}
          </div>
        )}

        {/* Stats */}
        <div className="mt-3 flex items-center gap-6 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <span className="font-medium">{nodes.length}</span>
            <span>nodes</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{edges.length}</span>
            <span>connections</span>
          </div>
          {isDirty && (
            <div className="flex items-center gap-2 text-amber-600">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              <span>Unsaved changes</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Agent Palette */}
        <div className="w-80 border-r border-gray-200 bg-white">
          <AgentPalette agents={agentsList} onDragStart={() => {}} />
        </div>

        {/* Editor */}
        <div className="flex-1 flex flex-col">
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <svg className="animate-spin h-12 w-12 text-primary-500 mx-auto" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p className="mt-4 text-gray-600">Loading workflow...</p>
              </div>
            </div>
          ) : (
            <>
              <div className="flex-1">
                <WorkflowEditor
                  agents={agents}
                  onSave={handleSaveWorkflow}
                  onRun={handleTestRun}
                  onNodeDoubleClick={handleNodeDoubleClick}
                />
              </div>

              {/* Validation Panel */}
              <div className="border-t border-gray-200 bg-white p-4">
                <WorkflowValidator
                  nodes={nodes}
                  edges={edges}
                  onValidationChange={setValidationResult}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Node Editor Modal */}
      {editingNode && (
        <NodeEditor
          node={editingNode}
          agents={agents}
          onSave={handleSaveNode}
          onClose={() => setEditingNode(null)}
        />
      )}

      {/* New Workflow Dialog */}
      {showNewWorkflowDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Create New Workflow</h3>
            <p className="text-gray-600 mb-4">
              Current unsaved changes will be lost. Are you sure you want to create a new workflow?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowNewWorkflowDialog(false)}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleNewWorkflow}
                className="px-4 py-2 text-white bg-primary-500 rounded-lg hover:bg-primary-600"
              >
                Create New
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkflowEditorPage;
