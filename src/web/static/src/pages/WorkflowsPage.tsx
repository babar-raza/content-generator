import React from 'react';
import WorkflowEditor from '../components/WorkflowEditor';
import AgentPalette from '../components/AgentPalette';
import { useAgents, useWorkflows } from '../hooks/useAPI';
import { useWorkflowStore } from '../utils/workflowStore';

const WorkflowsPage: React.FC = () => {
  const { agents } = useAgents();
  const { saveWorkflow } = useWorkflows();
  const { getWorkflowData } = useWorkflowStore();

  const handleSave = async () => {
    const workflow = getWorkflowData();
    await saveWorkflow(workflow);
  };

  const handleRun = async () => {
    console.log('Run workflow');
  };

  return (
    <div className="flex h-full">
      <div className="w-80 border-r">
        <AgentPalette agents={agents} onDragStart={() => {}} />
      </div>
      <div className="flex-1">
        <WorkflowEditor 
          agents={agents}
          onSave={handleSave}
          onRun={handleRun}
        />
      </div>
    </div>
  );
};

export default WorkflowsPage;
