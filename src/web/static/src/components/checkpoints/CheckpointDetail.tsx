import React, { useState } from 'react';
import { CheckpointResponse } from '../../types';
import { X, RotateCcw, Play, Trash2 } from 'lucide-react';

interface CheckpointDetailProps {
  checkpoint: CheckpointResponse;
  onClose: () => void;
  onRestore: (id: string, resume: boolean) => void;
  onDelete: (id: string) => void;
}

const CheckpointDetail: React.FC<CheckpointDetailProps> = ({
  checkpoint,
  onClose,
  onRestore,
  onDelete,
}) => {
  const [expandedState, setExpandedState] = useState(true);

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="border-b px-4 py-3 flex items-center justify-between">
        <h2 className="text-lg font-bold">Checkpoint Detail</h2>
        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-4">
        <div className="bg-gray-50 p-4 rounded">
          <h3 className="font-semibold mb-3">Metadata</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Checkpoint ID:</span>
              <span className="font-mono">{checkpoint.checkpoint_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Job ID:</span>
              <span className="font-mono">{checkpoint.job_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Step:</span>
              <span>{checkpoint.step_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Created:</span>
              <span>{new Date(checkpoint.timestamp).toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Workflow Version:</span>
              <span>v{checkpoint.workflow_version}</span>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded">
          <div
            className="p-4 flex items-center justify-between cursor-pointer"
            onClick={() => setExpandedState(!expandedState)}
          >
            <h3 className="font-semibold">State Snapshot</h3>
            <span className="text-gray-500 text-sm">
              {expandedState ? '▼' : '▶'}
            </span>
          </div>
          {expandedState && checkpoint.state_snapshot && (
            <div className="px-4 pb-4">
              <pre className="bg-white p-3 rounded text-xs overflow-auto max-h-96 border">
                {JSON.stringify(checkpoint.state_snapshot, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {checkpoint.metadata && (
          <div className="bg-gray-50 p-4 rounded">
            <h3 className="font-semibold mb-3">Additional Metadata</h3>
            <pre className="bg-white p-3 rounded text-xs overflow-auto max-h-48 border">
              {JSON.stringify(checkpoint.metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>

      <div className="border-t p-4 bg-gray-50 flex gap-2">
        <button
          onClick={() => onRestore(checkpoint.checkpoint_id, false)}
          className="flex-1 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center justify-center gap-2"
        >
          <RotateCcw size={16} />
          Restore Only
        </button>
        <button
          onClick={() => onRestore(checkpoint.checkpoint_id, true)}
          className="flex-1 px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 flex items-center justify-center gap-2"
        >
          <Play size={16} />
          Restore & Resume
        </button>
        <button
          onClick={() => onDelete(checkpoint.checkpoint_id)}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 flex items-center justify-center gap-2"
        >
          <Trash2 size={16} />
          Delete
        </button>
      </div>
    </div>
  );
};

export default CheckpointDetail;
