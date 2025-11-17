import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  NodeTypes,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Agent } from '@/types';
import { useWorkflowStore } from '@/utils/workflowStore';
import AgentNode from './nodes/AgentNode';
import NodeInspector from './NodeInspector';

const nodeTypes: NodeTypes = {
  default: AgentNode,
};

interface WorkflowEditorProps {
  agents: Record<string, Agent>;
  onSave: () => void;
  onRun: () => void;
  activeNodeId?: string;
}

const WorkflowEditorInner: React.FC<WorkflowEditorProps> = ({
  agents,
  onSave,
  onRun,
  activeNodeId,
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  const {
    nodes,
    edges,
    selectedNode,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    selectNode,
    updateNodeData,
    isDirty,
  } = useWorkflowStore();

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const agentData = event.dataTransfer.getData('application/json');

      if (!agentData) return;

      const agent: Agent = JSON.parse(agentData);
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      addNode('agent', agent, position);
    },
    [reactFlowInstance, addNode]
  );

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      selectNode(node);
    },
    [selectNode]
  );

  const onPaneClick = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  // Update active node styling
  const nodesWithActiveState = nodes.map((node) => ({
    ...node,
    className: node.id === activeNodeId ? 'active' : '',
  }));

  return (
    <div className="h-full flex">
      <div className="flex-1 relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodesWithActiveState}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onInit={setReactFlowInstance}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          snapToGrid
          snapGrid={[15, 15]}
        >
          <Background />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              if (node.id === activeNodeId) return '#0ea5e9';
              return node.type === 'start' ? '#22c55e' : '#0284c7';
            }}
            nodeStrokeWidth={3}
          />
        </ReactFlow>

        {/* Toolbar */}
        <div className="absolute top-4 right-4 flex gap-2 bg-white rounded-lg shadow-lg p-2">
          <button
            onClick={onSave}
            disabled={!isDirty}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              isDirty
                ? 'bg-primary-500 text-white hover:bg-primary-600'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Save
          </button>
          <button
            onClick={onRun}
            className="px-4 py-2 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600 transition-colors"
          >
            ▶ Run
          </button>
        </div>
      </div>

      {/* Node Inspector */}
      {selectedNode && (
        <div className="w-80 border-l border-gray-200 bg-white overflow-y-auto">
          <NodeInspector
            node={selectedNode}
            agents={agents}
            onUpdateNode={updateNodeData}
          />
        </div>
      )}
    </div>
  );
};

const WorkflowEditor: React.FC<WorkflowEditorProps> = (props) => {
  return (
    <ReactFlowProvider>
      <WorkflowEditorInner {...props} />
    </ReactFlowProvider>
  );
};

export default WorkflowEditor;
