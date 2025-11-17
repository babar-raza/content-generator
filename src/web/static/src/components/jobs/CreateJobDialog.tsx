import React, { useState } from 'react';
import { X } from 'lucide-react';

interface CreateJobDialogProps {
  onClose: () => void;
  onCreate: (workflowId: string, inputs: any) => Promise<any>;
}

const CreateJobDialog: React.FC<CreateJobDialogProps> = ({ onClose, onCreate }) => {
  const [workflowId, setWorkflowId] = useState('');
  const [inputJson, setInputJson] = useState('{\n  \n}');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError('');
      
      const inputs = JSON.parse(inputJson);
      await onCreate(workflowId, inputs);
      
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Create Job</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Workflow ID
            </label>
            <input
              type="text"
              value={workflowId}
              onChange={(e) => setWorkflowId(e.target.value)}
              className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., blog_generator"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Inputs (JSON)
            </label>
            <textarea
              value={inputJson}
              onChange={(e) => setInputJson(e.target.value)}
              className="w-full px-3 py-2 border rounded font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={10}
              placeholder='{\n  "topic": "AI trends",\n  "keywords": ["AI", "ML"]\n}'
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 p-3 rounded text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex gap-3 justify-end">
            <button
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !workflowId}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Job'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateJobDialog;
