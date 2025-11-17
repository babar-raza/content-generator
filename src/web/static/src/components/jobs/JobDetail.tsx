import React, { useState } from 'react';
import { JobStatus } from '../../types';
import { X, Play, Pause, XCircle } from 'lucide-react';
import OverviewTab from './OverviewTab';
import LogsTab from './LogsTab';
import CheckpointsTab from './CheckpointsTab';

interface JobDetailProps {
  job: JobStatus;
  onClose: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
}

const JobDetail: React.FC<JobDetailProps> = ({
  job,
  onClose,
  onPause,
  onResume,
  onCancel,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'logs' | 'checkpoints'>('overview');

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="border-b px-4 py-3 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold">Job: {job.job_id.slice(0, 12)}...</h2>
            <StatusBadge status={job.status} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          {job.status === 'running' && (
            <button
              onClick={onPause}
              className="px-3 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600 flex items-center gap-1"
            >
              <Pause size={14} />
              Pause
            </button>
          )}
          {job.status === 'paused' && (
            <button
              onClick={onResume}
              className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 flex items-center gap-1"
            >
              <Play size={14} />
              Resume
            </button>
          )}
          {(job.status === 'running' || job.status === 'paused') && (
            <button
              onClick={onCancel}
              className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 flex items-center gap-1"
            >
              <XCircle size={14} />
              Cancel
            </button>
          )}
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X size={18} />
          </button>
        </div>
      </div>

      <div className="border-b">
        <div className="flex">
          {['overview', 'logs', 'checkpoints'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 text-sm font-medium capitalize ${
                activeTab === tab
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'overview' && <OverviewTab job={job} />}
        {activeTab === 'logs' && <LogsTab jobId={job.job_id} />}
        {activeTab === 'checkpoints' && <CheckpointsTab jobId={job.job_id} />}
      </div>
    </div>
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

export default JobDetail;
