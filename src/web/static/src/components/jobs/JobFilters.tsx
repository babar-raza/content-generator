import React from 'react';
import { Search, RefreshCw } from 'lucide-react';

interface JobFiltersProps {
  filters: {
    search: string;
    status: string;
    dateFrom: string;
    dateTo: string;
  };
  onChange: (filters: any) => void;
  onRefresh: () => void;
}

const JobFilters: React.FC<JobFiltersProps> = ({ filters, onChange, onRefresh }) => {
  return (
    <div className="flex items-center gap-4">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
        <input
          type="text"
          placeholder="Search job ID..."
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          className="w-full pl-10 pr-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value })}
        className="px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="all">All Status</option>
        <option value="running">Running</option>
        <option value="paused">Paused</option>
        <option value="completed">Completed</option>
        <option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option>
        <option value="pending">Pending</option>
      </select>

      <button
        onClick={onRefresh}
        className="px-3 py-2 border rounded hover:bg-gray-50 flex items-center gap-2"
      >
        <RefreshCw size={18} />
        Refresh
      </button>
    </div>
  );
};

export default JobFilters;
