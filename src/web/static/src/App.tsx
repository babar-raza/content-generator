import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import DashboardPage from './pages/DashboardPage';
import JobsPage from './pages/JobsPage';
import WorkflowsPage from './pages/WorkflowsPage';
import AgentsPage from './pages/AgentsPage';
import CheckpointsPage from './pages/CheckpointsPage';
import DebugPage from './pages/DebugPage';
import FlowsPage from './pages/FlowsPage';
import ConfigPage from './pages/ConfigPage';
import IngestionPage from './pages/IngestionPage';
import TopicDiscoveryPage from './pages/TopicDiscoveryPage';
import AgentTestingPage from './pages/AgentTestingPage';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="workflows" element={<WorkflowsPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="checkpoints" element={<CheckpointsPage />} />
          <Route path="debug" element={<DebugPage />} />
          <Route path="flows" element={<FlowsPage />} />
          <Route path="config" element={<ConfigPage />} />
          <Route path="ingestion" element={<IngestionPage />} />
          <Route path="topics/discover" element={<TopicDiscoveryPage />} />
          <Route path="agents/test" element={<AgentTestingPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

const NotFoundPage: React.FC = () => {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-300">404</h1>
        <p className="text-xl text-gray-600 mt-4">Page not found</p>
        <a href="/" className="text-blue-500 hover:underline mt-4 inline-block">
          Go to Dashboard
        </a>
      </div>
    </div>
  );
};

export default App;
