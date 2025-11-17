import React from 'react';
import { JobStatus } from '../../types';
import { Play, Pause, X } from 'lucide-react';

interface JobListProps {
  jobs: JobStatus[];
  selectedJobs: Set<string>;
  onSelectJobs: (jobs: Set<string>) => void;
  onSelectJob: (jobId: string) => void;
  onPauseJob: (jobId: string) => void;
  onResumeJob: (jobId: string) => void;
  onCancelJob: (jobId: string) => void;
}

const JobList: React.FC<JobListProps> = ({
  jobs,
  selectedJobs,
  onSelectJobs,
  onSelectJob,
  onPauseJob,
  onResumeJob,
  onCancelJob,
}) => {
  const toggleJobSelection = (jobId: string) => {
    const newSelected = new Set(selectedJobs);
    if (newSelected.has(jobId)) {
      newSelected.delete(jobId);
    } else {
      newSelected.add(jobId);
    }
    onSelectJobs(newSelected);
  };

  const toggleAll = () => {
    if (selectedJobs.size === jobs.length) {
      onSelectJobs(new Set());
    } else {
      onSelectJobs(new Set(jobs.map(j => j.job_id)));
    }
  };

  if (jobs.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No jobs found
      </div>
    );
  }

  return (
    <div className="overflow-auto">
      <table className="w-full">
        <thead className="bg-gray-50 border-b sticky top-0">
          <tr>
            <th className="px-4 py-3 text-left">
              <input
                type="checkbox"
                checked={selectedJobs.size === jobs.length && jobs.length > 0}
                onChange={toggleAll}
              />
            </th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Job ID</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Status</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Workflow</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Stage</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Progress</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Time</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map(job => (
            <JobRow
              key={job.job_id}
              job={job}
              selected={selectedJobs.has(job.job_id)}
              onToggleSelect={() => toggleJobSelection(job.job_id)}
              onClick={() => onSelectJob(job.job_id)}
              onPause={() => onPauseJob(job.job_id)}
              onResume={() => onResumeJob(job.job_id)}
              onCancel={() => onCancelJob(job.job_id)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};

const JobRow: React.FC<{
  job: JobStatus;
  selected: boolean;
  onToggleSelect: () => void;
  onClick: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
}> = ({ job, selected, onToggleSelect, onClick, onPause, onResume, onCancel }) => {
  return (
    <tr className="border-b hover:bg-gray-50 cursor-pointer">
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggleSelect}
        />
      </td>
      <td className="px-4 py-3" onClick={onClick}>
        <span className="font-mono text-sm">{job.job_id.slice(0, 8)}</span>
      </td>
      <td className="px-4 py-3" onClick={onClick}>
        <StatusBadge status={job.status} />
      </td>
      <td className="px-4 py-3" onClick={onClick}>
        {job.workflow_id || '-'}
      </td>
      <td className="px-4 py-3" onClick={onClick}>
        {job.current_stage || '-'}
      </td>
      <td className="px-4 py-3" onClick={onClick}>
        {job.progress !== undefined && (
          <div className="w-24">
            <div className="bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full"
                style={{ width: `${job.progress}%` }}
              />
            </div>
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-gray-600" onClick={onClick}>
        {job.created_at ? formatTime(job.created_at) : '-'}
      </td>
      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex gap-1">
          {job.status === 'running' && (
            <button
              onClick={onPause}
              className="p-1 hover:bg-gray-200 rounded"
              title="Pause"
            >
              <Pause size={16} />
            </button>
          )}
          {job.status === 'paused' && (
            <button
              onClick={onResume}
              className="p-1 hover:bg-gray-200 rounded"
              title="Resume"
            >
              <Play size={16} />
            </button>
          )}
          {(job.status === 'running' || job.status === 'paused') && (
            <button
              onClick={onCancel}
              className="p-1 hover:bg-gray-200 rounded text-red-500"
              title="Cancel"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    running: 'bg-blue-500',
    paused: 'bg-yellow-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-500',
    pending: 'bg-gray-400',
  };

  return (
    <span className={`px-2 py-1 text-xs text-white rounded ${colors[status] || 'bg-gray-500'}`}>
      {status}
    </span>
  );
};

const formatTime = (isoString: string): string => {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
};

export default JobList;
