import React, { useState, useEffect } from 'react';
import { useWebSocket } from '@/websocket/liveFlow';
import { LiveWorkflowCanvas } from '@/components/live/LiveWorkflowCanvas';
import { ExecutionTimeline, TimelineStep } from '@/components/live/ExecutionTimeline';
import { DataInspector } from '@/components/live/DataInspector';
import { apiClient } from '@/api/client';
import { Activity, AlertCircle } from 'lucide-react';

interface Job {
  job_id: string;
  workflow_id: string;
  status: string;
  created_at: string;
}

export const LiveFlowPage: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [workflowSteps, setWorkflowSteps] = useState<string[]>([]);
  const [timelineSteps, setTimelineSteps] = useState<TimelineStep[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [agentData, setAgentData] = useState<{
    input?: any;
    output?: any;
    error?: string;
  }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  const wsUrl = selectedJobId 
    ? `${protocol}//${host}/ws/live-flow/${selectedJobId}`
    : '';

  const { lastMessage } = useWebSocket(wsUrl);

  // Load jobs on mount
  useEffect(() => {
    loadJobs();
  }, []);

  // Load workflow steps when job is selected
  useEffect(() => {
    if (selectedJobId) {
      loadWorkflowSteps(selectedJobId);
    }
  }, [selectedJobId]);

  // Handle WebSocket messages for timeline and data inspector
  useEffect(() => {
    if (!lastMessage) return;

    switch (lastMessage.type) {
      case 'agent_started':
        if (lastMessage.agent_id) {
          setTimelineSteps(prev => [
            ...prev,
            {
              agentId: lastMessage.agent_id!,
              status: 'running',
              startTime: lastMessage.timestamp
            }
          ]);
        }
        break;

      case 'agent_completed':
        if (lastMessage.agent_id) {
          setTimelineSteps(prev =>
            prev.map(step =>
              step.agentId === lastMessage.agent_id
                ? {
                    ...step,
                    status: 'completed',
                    endTime: lastMessage.timestamp,
                    duration: lastMessage.duration
                  }
                : step
            )
          );

          // Update agent data if this is the selected agent
          if (selectedAgent === lastMessage.agent_id) {
            setAgentData(prev => ({
              ...prev,
              output: lastMessage.output
            }));
          }
        }
        break;

      case 'agent_failed':
        if (lastMessage.agent_id) {
          setTimelineSteps(prev =>
            prev.map(step =>
              step.agentId === lastMessage.agent_id
                ? {
                    ...step,
                    status: 'failed'
                  }
                : step
            )
          );

          // Update agent data if this is the selected agent
          if (selectedAgent === lastMessage.agent_id) {
            setAgentData(prev => ({
              ...prev,
              error: lastMessage.error
            }));
          }
        }
        break;
    }
  }, [lastMessage, selectedAgent]);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const response = await apiClient.getJobs();
      setJobs(response.jobs || []);
      
      // Auto-select first running or queued job
      const activeJob = response.jobs?.find((j: Job) => 
        j.status === 'running' || j.status === 'queued'
      );
      if (activeJob) {
        setSelectedJobId(activeJob.job_id);
      }
    } catch (err) {
      console.error('Failed to load jobs:', err);
      setError('Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const loadWorkflowSteps = async (jobId: string) => {
    try {
      // Try to get workflow details
      const job = jobs.find(j => j.job_id === jobId);
      if (!job) return;

      // Get workflow details to extract steps
      const workflow = await apiClient.getWorkflow(job.workflow_id).catch(() => null);
      
      if (workflow && workflow.steps) {
        const stepIds = workflow.steps.map((s: any) => s.agent_id || s.id);
        setWorkflowSteps(stepIds);
      } else {
        // Default steps if we can't fetch workflow
        setWorkflowSteps([
          'topic_identification',
          'kb_ingestion',
          'outline_creation',
          'section_writer',
          'content_assembly',
          'file_writer'
        ]);
      }
    } catch (err) {
      console.error('Failed to load workflow steps:', err);
      // Use default steps
      setWorkflowSteps([
        'topic_identification',
        'kb_ingestion',
        'outline_creation',
        'section_writer',
        'content_assembly',
        'file_writer'
      ]);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Activity className="w-8 h-8 animate-pulse text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading jobs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-red-600">
          <AlertCircle className="w-8 h-8 mx-auto mb-2" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Live Flow Monitor</h1>
        <p className="text-gray-600">Real-time workflow execution monitoring</p>
      </div>

      {/* Job Selector */}
      <div className="bg-white rounded-lg shadow p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select Job to Monitor
        </label>
        <select
          value={selectedJobId}
          onChange={(e) => {
            setSelectedJobId(e.target.value);
            setTimelineSteps([]);
            setAgentData({});
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">-- Select a job --</option>
          {jobs.map((job) => (
            <option key={job.job_id} value={job.job_id}>
              {job.job_id} - {job.workflow_id} ({job.status})
            </option>
          ))}
        </select>
      </div>

      {selectedJobId ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Workflow Canvas - Takes 2 columns */}
          <div className="lg:col-span-2">
            <LiveWorkflowCanvas
              jobId={selectedJobId}
              workflowSteps={workflowSteps}
            />
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            {/* Execution Timeline */}
            <ExecutionTimeline
              steps={timelineSteps}
              currentAgent={timelineSteps.find(s => s.status === 'running')?.agentId}
            />

            {/* Data Inspector */}
            {selectedAgent && (
              <DataInspector
                agentId={selectedAgent}
                inputData={agentData.input}
                outputData={agentData.output}
                error={agentData.error}
              />
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            No Job Selected
          </h3>
          <p className="text-gray-600">
            Select a job from the dropdown above to monitor its execution in real-time
          </p>
        </div>
      )}
    </div>
  );
};

export default LiveFlowPage;
