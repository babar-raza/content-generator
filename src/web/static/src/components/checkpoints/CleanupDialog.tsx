import React, { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';

interface CleanupDialogProps {
  jobId: string;
  totalCheckpoints: number;
  onClose: () => void;
  onCleanup: (keepLast: number) => void;
}

const CleanupDialog: React.FC<CleanupDialogProps> = ({
  jobId,
  totalCheckpoints,
  onClose,
  onCleanup,
}) => {
  const [keepLast, setKeepLast] = useState(10);

  const toDelete = Math.max(0, totalCheckpoints - keepLast);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Cleanup Old Checkpoints</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-50 p-3 rounded">
            <div className="text-sm">
              <div className="text-gray-600">Job ID:</div>
              <div className="font-mono">{jobId}</div>
            </div>
            <div className="text-sm mt-2">
              <div className="text-gray-600">Total Checkpoints:</div>
              <div className="font-semibold">{totalCheckpoints}</div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Keep Last N Checkpoints
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={keepLast}
              onChange={(e) => setKeepLast(parseInt(e.target.value) || 10)}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Value must be between 1 and 100
            </p>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 p-3 rounded flex gap-2">
            <AlertTriangle size={20} className="text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <div className="font-semibold text-yellow-800">
                This will delete {toDelete} checkpoint{toDelete !== 1 ? 's' : ''}
              </div>
              <div className="text-yellow-700 mt-1">
                Keeping the {keepLast} most recent checkpoints. This action cannot be undone.
              </div>
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded"
            >
              Cancel
            </button>
            <button
              onClick={() => onCleanup(keepLast)}
              disabled={toDelete === 0}
              className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 disabled:opacity-50"
            >
              Cleanup {toDelete > 0 ? `(Delete ${toDelete})` : ''}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CleanupDialog;
