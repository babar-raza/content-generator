import React from 'react';
import { useNavigate } from 'react-router-dom';
import SystemHealthCard from '../components/monitoring/SystemHealthCard';
import ActiveJobsList from '../components/monitoring/ActiveJobsList';
import AgentStatusGrid from '../components/monitoring/AgentStatusGrid';
import SystemMetricsChart from '../components/monitoring/SystemMetricsChart';
import { Plus, Zap, FileText, Search } from 'lucide-react';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();

  const quickActions = [
    {
      icon: Plus,
      label: 'Create Job',
      onClick: () => navigate('/jobs'),
      color: 'bg-blue-500 hover:bg-blue-600'
    },
    {
      icon: Zap,
      label: 'Generate Content',
      onClick: () => navigate('/jobs'),
      color: 'bg-green-500 hover:bg-green-600'
    },
    {
      icon: FileText,
      label: 'New Workflow',
      onClick: () => navigate('/workflows'),
      color: 'bg-purple-500 hover:bg-purple-600'
    },
    {
      icon: Search,
      label: 'View All Jobs',
      onClick: () => navigate('/jobs'),
      color: 'bg-gray-500 hover:bg-gray-600'
    }
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-gray-600">System overview and quick actions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <SystemHealthCard />
          <ActiveJobsList limit={5} />
          <SystemMetricsChart />
        </div>

        <div className="space-y-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
            <div className="space-y-3">
              {quickActions.map((action, idx) => (
                <button
                  key={idx}
                  onClick={action.onClick}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-white transition-colors ${action.color}`}
                >
                  <action.icon className="w-5 h-5" />
                  <span className="font-medium">{action.label}</span>
                </button>
              ))}
            </div>
          </div>

          <AgentStatusGrid compact />
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
