import React, { useState } from 'react';
import { Job, LogEntry, WebSocketEvent } from '@/types';
import { useJobWebSocket } from '@/hooks/useJobWebSocket';
import ConnectionStatus from './ConnectionStatus';

interface JobMonitorProps {
  jobs: Job[];
  onPauseJob: (jobId: string) => void;
  onResumeJob: (jobId: string) => void;
  onCancelJob: (jobId: string) => void;
}

const JobStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    paused: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-700',
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded ${
        colors[status] || 'bg-gray-100 text-gray-700'
      }`}
    >
      {status.toUpperCase()}
    </span>
  );
};

const JobCard: React.FC<{
  job: Job;
  isSelected: boolean;
  onClick: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
}> = ({ job, isSelected, onClick, onPause, onResume, onCancel }) => {
  return (
    <div
      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
        isSelected
          ? 'border-primary-500 bg-primary-50'
          : 'border-gray-200 hover:border-gray-300 bg-white'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-gray-900 truncate">
            {job.workflow_id}
          </div>
          <div className="text-xs text-gray-500 truncate">{job.job_id}</div>
        </div>
        <JobStatusBadge status={job.status} />
      </div>

      {job.progress !== undefined && (
        <div className="mb-2">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>Progress</span>
            <span>{Math.round(job.progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-primary-500 h-1.5 rounded-full transition-all"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>
      )}

      {job.current_stage && (
        <div className="text-xs text-gray-600 mb-2">
          Current: <span className="font-medium">{job.current_stage}</span>
        </div>
      )}

      <div className="flex gap-2">
        {job.status === 'running' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPause();
            }}
            className="text-xs px-2 py-1 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200"
          >
            Pause
          </button>
        )}
        {job.status === 'paused' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onResume();
            }}
            className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
          >
            Resume
          </button>
        )}
        {(job.status === 'running' || job.status === 'paused') && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCancel();
            }}
            className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
};

const LogViewer: React.FC<{ events: WebSocketEvent[] }> = ({ events }) => {
  const logs: LogEntry[] = events.map((event) => ({
    timestamp: event.timestamp,
    level: event.type.includes('ERROR') ? 'error' : 'info',
    node_id: event.data.node_id,
    message: event.data.message || JSON.stringify(event.data),
  }));

  return (
    <div className="bg-gray-900 text-gray-100 p-3 rounded-lg font-mono text-xs h-64 overflow-y-auto">
      {logs.length === 0 ? (
        <div className="text-gray-500">No logs yet...</div>
      ) : (
        logs.map((log, index) => (
          <div key={index} className="mb-1">
            <span className="text-gray-500">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            {log.node_id && (
              <span className="text-blue-400 ml-2">[{log.node_id}]</span>
            )}
            <span
              className={`ml-2 ${
                log.level === 'error'
                  ? 'text-red-400'
                  : log.level === 'warning'
                  ? 'text-yellow-400'
                  : 'text-gray-300'
              }`}
            >
              {log.message}
            </span>
          </div>
        ))
      )}
    </div>
  );
};

const JobMonitor: React.FC<JobMonitorProps> = ({
  jobs,
  onPauseJob,
  onResumeJob,
  onCancelJob,
}) => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const { jobStatus, events, status, reconnect } = useJobWebSocket({
    jobId: selectedJobId,
    fallbackPolling: true,
  });

  return (
    <div className="h-full flex flex-col bg-gray-50">
      <div className="p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">Jobs</h2>
          <ConnectionStatus
            status={status}
            onReconnect={reconnect}
          />
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="p-4 space-y-2 overflow-y-auto" style={{ maxHeight: '40%' }}>
          {jobs.length === 0 ? (
            <div className="text-center text-gray-500 py-8">No jobs yet</div>
          ) : (
            jobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                isSelected={selectedJobId === job.job_id}
                onClick={() => setSelectedJobId(job.job_id)}
                onPause={() => onPauseJob(job.job_id)}
                onResume={() => onResumeJob(job.job_id)}
                onCancel={() => onCancelJob(job.job_id)}
              />
            ))
          )}
        </div>

        {selectedJobId && (
          <div className="flex-1 border-t border-gray-200 p-4 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">Logs</h3>
              {jobStatus && (
                <div className="text-sm text-gray-600">
                  {jobStatus.metrics?.nodes_completed || 0} /{' '}
                  {jobStatus.metrics?.nodes_total || 0} nodes
                </div>
              )}
            </div>
            <LogViewer events={events} />
          </div>
        )}
      </div>
    </div>
  );
};

export default JobMonitor;
