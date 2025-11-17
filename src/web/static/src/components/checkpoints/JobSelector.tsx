import React, { useState } from 'react';
import { Search } from 'lucide-react';

interface JobSelectorProps {
  selectedJobId: string | null;
  onSelectJob: (jobId: string | null) => void;
}

const JobSelector: React.FC<JobSelectorProps> = ({ selectedJobId, onSelectJob }) => {
  const [manualJobId, setManualJobId] = useState('');

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (manualJobId.trim()) {
      onSelectJob(manualJobId.trim());
    }
  };

  return (
    <form onSubmit={handleManualSubmit} className="flex gap-4">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
        <input
          type="text"
          placeholder="Enter job ID..."
          value={manualJobId}
          onChange={(e) => setManualJobId(e.target.value)}
          className="w-full pl-10 pr-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <button
        type="submit"
        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
      >
        Load Checkpoints
      </button>
      {selectedJobId && (
        <button
          type="button"
          onClick={() => {
            onSelectJob(null);
            setManualJobId('');
          }}
          className="px-4 py-2 border rounded hover:bg-gray-50"
        >
          Clear
        </button>
      )}
    </form>
  );
};

export default JobSelector;
