import React from 'react';
import { JobStatus } from '../../types';

const OverviewTab: React.FC<{ job: JobStatus }> = ({ job }) => {
  return (
    <div className="space-y-4">
      <div className="bg-gray-50 p-4 rounded">
        <h3 className="font-semibold mb-2">Basic Information</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Job ID:</span>
            <div className="font-mono">{job.job_id}</div>
          </div>
          <div>
            <span className="text-gray-600">Workflow:</span>
            <div>{job.workflow_id || '-'}</div>
          </div>
          <div>
            <span className="text-gray-600">Created:</span>
            <div>{job.created_at ? new Date(job.created_at).toLocaleString() : '-'}</div>
          </div>
          <div>
            <span className="text-gray-600">Updated:</span>
            <div>{job.updated_at ? new Date(job.updated_at).toLocaleString() : '-'}</div>
          </div>
        </div>
      </div>

      {job.progress !== undefined && (
        <div className="bg-gray-50 p-4 rounded">
          <h3 className="font-semibold mb-2">Progress</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>{job.current_stage || 'Processing'}</span>
              <span>{job.progress}%</span>
            </div>
            <div className="bg-gray-200 rounded-full h-3">
              <div
                className="bg-blue-500 h-3 rounded-full transition-all"
                style={{ width: `${job.progress}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {job.error && (
        <div className="bg-red-50 border border-red-200 p-4 rounded">
          <h3 className="font-semibold text-red-700 mb-2">Error</h3>
          <pre className="text-sm text-red-600 whitespace-pre-wrap">{job.error}</pre>
        </div>
      )}

      {job.result && (
        <div className="bg-gray-50 p-4 rounded">
          <h3 className="font-semibold mb-2">Result</h3>
          <pre className="text-sm bg-white p-2 rounded overflow-auto max-h-64">
            {JSON.stringify(job.result, null, 2)}
          </pre>
        </div>
      )}

      {job.metadata && (
        <div className="bg-gray-50 p-4 rounded">
          <h3 className="font-semibold mb-2">Metadata</h3>
          <pre className="text-sm bg-white p-2 rounded overflow-auto max-h-64">
            {JSON.stringify(job.metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default OverviewTab;
