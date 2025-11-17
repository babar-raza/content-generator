import React from 'react';
import { CheckpointMetadata } from '../../types';
import { RotateCcw, Trash2 } from 'lucide-react';

interface CheckpointListProps {
  checkpoints: CheckpointMetadata[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onRestore: (id: string, resume: boolean) => void;
  onDelete: (id: string) => void;
}

const CheckpointList: React.FC<CheckpointListProps> = ({
  checkpoints,
  selectedId,
  onSelect,
  onRestore,
  onDelete,
}) => {
  return (
    <div className="overflow-auto">
      <div className="p-4 bg-gray-50 border-b">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Checkpoints</h3>
          <span className="text-sm text-gray-600">Total: {checkpoints.length}</span>
        </div>
      </div>

      <table className="w-full">
        <thead className="bg-gray-50 border-b sticky top-0">
          <tr>
            <th className="px-4 py-3 text-left text-sm font-semibold">Step</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Timestamp</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Version</th>
            <th className="px-4 py-3 text-left text-sm font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody>
          {checkpoints.map(checkpoint => (
            <tr
              key={checkpoint.checkpoint_id}
              onClick={() => onSelect(checkpoint.checkpoint_id)}
              className={`border-b cursor-pointer hover:bg-gray-50 ${
                selectedId === checkpoint.checkpoint_id ? 'bg-blue-50' : ''
              }`}
            >
              <td className="px-4 py-3">
                <div className="font-medium">{checkpoint.step_name}</div>
                <div className="text-xs text-gray-500 font-mono">
                  {checkpoint.checkpoint_id.slice(0, 20)}...
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                {formatTimestamp(checkpoint.timestamp)}
              </td>
              <td className="px-4 py-3 text-sm text-gray-600">
                v{checkpoint.workflow_version}
              </td>
              <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                <div className="flex gap-1">
                  <button
                    onClick={() => onRestore(checkpoint.checkpoint_id, false)}
                    className="p-1 hover:bg-gray-200 rounded text-blue-500"
                    title="Restore"
                  >
                    <RotateCcw size={16} />
                  </button>
                  <button
                    onClick={() => onDelete(checkpoint.checkpoint_id)}
                    className="p-1 hover:bg-gray-200 rounded text-red-500"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const formatTimestamp = (isoString: string): string => {
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

export default CheckpointList;
