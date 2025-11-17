import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { 
  BookOpen, 
  FileText, 
  Code, 
  BookMarked, 
  GraduationCap,
  Upload,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw
} from 'lucide-react';

interface IngestionResult {
  id: string;
  type: string;
  path: string;
  timestamp: string;
  status: 'running' | 'completed' | 'failed';
  filesProcessed?: number;
  filesSkipped?: number;
  errors?: number;
  errorMessage?: string;
}

const IngestionPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'kb' | 'docs' | 'api' | 'blog' | 'tutorial'>('kb');
  const [paths, setPaths] = useState({
    kb: '',
    docs: '',
    api: '',
    blog: '',
    tutorial: ''
  });
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, any>>({});
  const [history, setHistory] = useState<IngestionResult[]>([]);

  const tabs = [
    { id: 'kb', label: 'Knowledge Base', icon: BookOpen },
    { id: 'docs', label: 'Documentation', icon: FileText },
    { id: 'api', label: 'API Reference', icon: Code },
    { id: 'blog', label: 'Blog Posts', icon: BookMarked },
    { id: 'tutorial', label: 'Tutorials', icon: GraduationCap }
  ];

  useEffect(() => {
    // Load history from localStorage
    const savedHistory = localStorage.getItem('ingestionHistory');
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
  }, []);

  const saveToHistory = (result: IngestionResult) => {
    const updated = [result, ...history].slice(0, 50);
    setHistory(updated);
    localStorage.setItem('ingestionHistory', JSON.stringify(updated));
  };

  const handleIngest = async (type: string) => {
    const path = paths[type as keyof typeof paths];
    if (!path) {
      alert('Please enter a path');
      return;
    }

    setLoading({ ...loading, [type]: true });
    
    const historyEntry: IngestionResult = {
      id: `${type}_${Date.now()}`,
      type,
      path,
      timestamp: new Date().toISOString(),
      status: 'running'
    };
    
    saveToHistory(historyEntry);

    try {
      let result;
      switch (type) {
        case 'kb':
          result = await apiClient.ingestKB(path);
          break;
        case 'docs':
          result = await apiClient.ingestDocs(path);
          break;
        case 'api':
          result = await apiClient.ingestAPI(path);
          break;
        case 'blog':
          result = await apiClient.ingestBlog(path);
          break;
        case 'tutorial':
          result = await apiClient.ingestTutorial(path);
          break;
        default:
          throw new Error('Unknown ingestion type');
      }

      setResults({ ...results, [type]: result });
      
      // Update history entry
      historyEntry.status = 'completed';
      if (result.result) {
        historyEntry.filesProcessed = result.result.files_processed || 0;
        historyEntry.filesSkipped = result.result.files_skipped || 0;
        historyEntry.errors = result.result.errors || 0;
      }
      saveToHistory(historyEntry);
      
    } catch (error: any) {
      console.error('Ingestion failed:', error);
      
      // Update history entry
      historyEntry.status = 'failed';
      historyEntry.errorMessage = error.message || 'Unknown error';
      saveToHistory(historyEntry);
      
      setResults({ 
        ...results, 
        [type]: { 
          error: error.message || 'Ingestion failed' 
        } 
      });
    } finally {
      setLoading({ ...loading, [type]: false });
    }
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('ingestionHistory');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Clock className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const renderTabContent = () => {
    const IconComponent = tabs.find(t => t.id === activeTab)?.icon || BookOpen;
    const isLoading = loading[activeTab];
    const result = results[activeTab];

    return (
      <div className="space-y-6">
        {/* Path Input */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center mb-4">
            <IconComponent className="w-6 h-6 mr-2 text-blue-600" />
            <h3 className="text-lg font-semibold">
              {tabs.find(t => t.id === activeTab)?.label} Ingestion
            </h3>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Path to {activeTab.toUpperCase()} files
              </label>
              <input
                type="text"
                value={paths[activeTab as keyof typeof paths]}
                onChange={(e) => setPaths({ ...paths, [activeTab]: e.target.value })}
                placeholder={`/path/to/${activeTab}/files`}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                disabled={isLoading}
              />
            </div>
            
            <button
              onClick={() => handleIngest(activeTab)}
              disabled={isLoading || !paths[activeTab as keyof typeof paths]}
              className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Ingesting...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Start Ingestion
                </>
              )}
            </button>
          </div>
        </div>

        {/* Results */}
        {result && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Ingestion Results</h3>
            
            {result.error ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-center">
                  <XCircle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="text-red-700 dark:text-red-300">{result.error}</span>
                </div>
              </div>
            ) : result.result ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {result.result.files_processed || 0}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Files Processed
                  </div>
                </div>
                
                <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                    {result.result.files_skipped || 0}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Files Skipped
                  </div>
                </div>
                
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {result.result.errors || 0}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Errors
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Content Ingestion</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Ingest content from various sources into the system
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex -mb-px">
            {tabs.map((tab) => {
              const IconComponent = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center px-6 py-4 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <IconComponent className="w-5 h-5 mr-2" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      {renderTabContent()}

      {/* History */}
      <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <h3 className="text-lg font-semibold">Ingestion History</h3>
          {history.length > 0 && (
            <button
              onClick={clearHistory}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Clear History
            </button>
          )}
        </div>
        
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {history.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No ingestion history yet
            </div>
          ) : (
            history.slice(0, 20).map((item) => (
              <div key={item.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(item.status)}
                    <div>
                      <div className="font-medium">{item.type.toUpperCase()}</div>
                      <div className="text-sm text-gray-500">{item.path}</div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-sm text-gray-500">
                      {new Date(item.timestamp).toLocaleString()}
                    </div>
                    {item.status === 'completed' && (
                      <div className="text-xs text-gray-400 mt-1">
                        {item.filesProcessed} processed, {item.filesSkipped} skipped
                      </div>
                    )}
                    {item.status === 'failed' && item.errorMessage && (
                      <div className="text-xs text-red-500 mt-1">
                        {item.errorMessage}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default IngestionPage;
