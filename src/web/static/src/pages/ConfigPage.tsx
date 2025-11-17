import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Settings, Save, RefreshCw, Eye, Code } from 'lucide-react';

interface ConfigSection {
  name: string;
  data: any;
  expanded: boolean;
}

const ConfigPage: React.FC = () => {
  const [configSections, setConfigSections] = useState<ConfigSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'formatted' | 'raw'>('formatted');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const [snapshot, agents, workflows] = await Promise.all([
        apiClient.getConfig().catch(() => ({})),
        apiClient.getAgentConfigs().catch(() => ({ agents: {} })),
        apiClient.getWorkflowConfigs().catch(() => ({ workflows: {} }))
      ]);

      const sections: ConfigSection[] = [
        {
          name: 'System Snapshot',
          data: snapshot,
          expanded: false
        },
        {
          name: 'Agents',
          data: agents.agents || agents,
          expanded: false
        },
        {
          name: 'Workflows',
          data: workflows.workflows || workflows,
          expanded: false
        }
      ];

      setConfigSections(sections);
      if (sections.length > 0) {
        setSelectedSection(sections[0].name);
      }
    } catch (error) {
      console.error('Failed to load configuration:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (name: string) => {
    setConfigSections(sections =>
      sections.map(s =>
        s.name === name ? { ...s, expanded: !s.expanded } : s
      )
    );
  };

  const renderValue = (value: any, depth: number = 0): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400">null</span>;
    }

    if (typeof value === 'boolean') {
      return <span className={value ? 'text-green-600' : 'text-red-600'}>{String(value)}</span>;
    }

    if (typeof value === 'number') {
      return <span className="text-blue-600">{value}</span>;
    }

    if (typeof value === 'string') {
      return <span className="text-purple-600">"{value}"</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400">[]</span>;
      }
      return (
        <div className="ml-4">
          <div className="text-gray-400">[</div>
          {value.map((item, idx) => (
            <div key={idx} className="ml-4">
              {renderValue(item, depth + 1)}
              {idx < value.length - 1 && ','}
            </div>
          ))}
          <div className="text-gray-400">]</div>
        </div>
      );
    }

    if (typeof value === 'object') {
      const entries = Object.entries(value);
      if (entries.length === 0) {
        return <span className="text-gray-400">{'{}'}</span>;
      }
      return (
        <div className="ml-4">
          <div className="text-gray-400">{'{'}</div>
          {entries.map(([key, val], idx) => (
            <div key={key} className="ml-4">
              <span className="text-gray-700 font-medium">{key}:</span>{' '}
              {renderValue(val, depth + 1)}
              {idx < entries.length - 1 && ','}
            </div>
          ))}
          <div className="text-gray-400">{'}'}</div>
        </div>
      );
    }

    return String(value);
  };

  const selectedSectionData = configSections.find(s => s.name === selectedSection);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Configuration</h1>
          <p className="text-gray-600">System and component configuration</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setViewMode(viewMode === 'formatted' ? 'raw' : 'formatted')}
            className="flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            {viewMode === 'formatted' ? <Code className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {viewMode === 'formatted' ? 'Raw JSON' : 'Formatted'}
          </button>
          <button
            onClick={loadConfig}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Sections
              </h2>
            </div>
            <div className="divide-y">
              {configSections.map(section => (
                <button
                  key={section.name}
                  onClick={() => setSelectedSection(section.name)}
                  className={`w-full p-4 text-left hover:bg-gray-50 transition-colors ${
                    selectedSection === section.name ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                  }`}
                >
                  <div className="font-medium">{section.name}</div>
                  <div className="text-sm text-gray-500">
                    {Object.keys(section.data).length} items
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">Actions</h3>
            <button
              className="w-full flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors mb-2"
              disabled
            >
              <Save className="w-4 h-4" />
              Save Changes
            </button>
            <p className="text-xs text-gray-500 mt-2">
              Configuration editing coming soon
            </p>
          </div>
        </div>

        <div className="lg:col-span-3">
          {selectedSectionData ? (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-2xl font-bold mb-4">{selectedSectionData.name}</h2>
              
              {viewMode === 'formatted' ? (
                <div className="bg-gray-50 p-4 rounded-lg font-mono text-sm overflow-x-auto">
                  {renderValue(selectedSectionData.data)}
                </div>
              ) : (
                <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto max-h-[600px] overflow-y-auto">
                  <pre>{JSON.stringify(selectedSectionData.data, null, 2)}</pre>
                </div>
              )}

              <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <div className="flex items-start gap-3">
                  <Eye className="w-5 h-5 text-blue-500 mt-0.5" />
                  <div className="text-sm text-blue-800">
                    <strong>Read-only view:</strong> This configuration is currently displayed in read-only mode.
                    Configuration editing will be available in a future update.
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-12">
              <div className="text-center text-gray-500">
                <Settings className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg">Select a configuration section to view</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConfigPage;
