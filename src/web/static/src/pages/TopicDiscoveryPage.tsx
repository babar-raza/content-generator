import React, { useState } from 'react';
import { apiClient } from '../api/client';
import { 
  Search, 
  Download, 
  FileText,
  RefreshCw,
  CheckSquare,
  Square,
  ArrowUpDown,
  Filter
} from 'lucide-react';

interface Topic {
  title: string;
  priority: number;
  description: string;
  sourceFile: string;
  category?: string;
}

const TopicDiscoveryPage: React.FC = () => {
  const [kbPath, setKbPath] = useState('');
  const [docsPath, setDocsPath] = useState('');
  const [maxTopics, setMaxTopics] = useState(50);
  const [loading, setLoading] = useState(false);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<Set<number>>(new Set());
  const [sortBy, setSortBy] = useState<'priority' | 'title'>('priority');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filterText, setFilterText] = useState('');

  const handleDiscover = async () => {
    if (!kbPath && !docsPath) {
      alert('Please enter at least one path (KB or Docs)');
      return;
    }

    setLoading(true);
    setTopics([]);
    setSelectedTopics(new Set());

    try {
      const result = await apiClient.discoverTopics({
        kb_path: kbPath || undefined,
        docs_path: docsPath || undefined,
        max_topics: maxTopics
      });

      if (result.error) {
        throw new Error(result.error.message || 'Topic discovery failed');
      }

      if (result.result && Array.isArray(result.result.topics)) {
        setTopics(result.result.topics);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error: any) {
      console.error('Topic discovery failed:', error);
      alert(`Discovery failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleTopic = (index: number) => {
    const newSelected = new Set(selectedTopics);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedTopics(newSelected);
  };

  const toggleAll = () => {
    if (selectedTopics.size === topics.length) {
      setSelectedTopics(new Set());
    } else {
      setSelectedTopics(new Set(topics.map((_, i) => i)));
    }
  };

  const handleSort = (field: 'priority' | 'title') => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const exportToCSV = () => {
    const headers = ['Title', 'Priority', 'Description', 'Source File', 'Category'];
    const rows = topics.map(t => [
      t.title,
      t.priority,
      t.description,
      t.sourceFile,
      t.category || ''
    ]);

    const csv = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `topics_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportToJSON = () => {
    const json = JSON.stringify(topics, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `topics_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const createWorkflows = async () => {
    if (selectedTopics.size === 0) {
      alert('Please select at least one topic');
      return;
    }

    const selectedTopicsList = Array.from(selectedTopics).map(i => topics[i]);
    
    try {
      // Create batch workflow jobs
      const jobs = selectedTopicsList.map(topic => ({
        inputs: { topic: topic.title, description: topic.description }
      }));

      await apiClient.createBatchJobs('blog-workflow', jobs, `Topics ${Date.now()}`);
      alert(`Created ${selectedTopics.size} blog workflow jobs`);
    } catch (error: any) {
      console.error('Failed to create workflows:', error);
      alert(`Failed to create workflows: ${error.message}`);
    }
  };

  const filteredAndSortedTopics = topics
    .filter(t => 
      !filterText || 
      t.title.toLowerCase().includes(filterText.toLowerCase()) ||
      t.description.toLowerCase().includes(filterText.toLowerCase())
    )
    .sort((a, b) => {
      let comparison = 0;
      if (sortBy === 'priority') {
        comparison = a.priority - b.priority;
      } else {
        comparison = a.title.localeCompare(b.title);
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Topic Discovery</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Discover blog topics from your content library
        </p>
      </div>

      {/* Discovery Form */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Knowledge Base Path
            </label>
            <input
              type="text"
              value={kbPath}
              onChange={(e) => setKbPath(e.target.value)}
              placeholder="/path/to/kb"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              disabled={loading}
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">
              Documentation Path
            </label>
            <input
              type="text"
              value={docsPath}
              onChange={(e) => setDocsPath(e.target.value)}
              placeholder="/path/to/docs"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              disabled={loading}
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Maximum Topics: {maxTopics}
          </label>
          <input
            type="range"
            min="1"
            max="200"
            value={maxTopics}
            onChange={(e) => setMaxTopics(parseInt(e.target.value))}
            className="w-full"
            disabled={loading}
          />
        </div>

        <button
          onClick={handleDiscover}
          disabled={loading || (!kbPath && !docsPath)}
          className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Discovering Topics...
            </>
          ) : (
            <>
              <Search className="w-4 h-4 mr-2" />
              Discover Topics
            </>
          )}
        </button>
      </div>

      {/* Results */}
      {topics.length > 0 && (
        <>
          {/* Toolbar */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-4">
            <div className="flex flex-wrap gap-4 items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleAll}
                  className="flex items-center px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  {selectedTopics.size === topics.length ? (
                    <CheckSquare className="w-4 h-4 mr-2" />
                  ) : (
                    <Square className="w-4 h-4 mr-2" />
                  )}
                  Select All
                </button>
                
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {selectedTopics.size} selected
                </span>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                  placeholder="Filter topics..."
                  className="px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                />
                
                <button
                  onClick={exportToCSV}
                  className="flex items-center px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  CSV
                </button>
                
                <button
                  onClick={exportToJSON}
                  className="flex items-center px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <Download className="w-4 h-4 mr-2" />
                  JSON
                </button>
                
                <button
                  onClick={createWorkflows}
                  disabled={selectedTopics.size === 0}
                  className="flex items-center px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Create Workflows ({selectedTopics.size})
                </button>
              </div>
            </div>
          </div>

          {/* Topics Table */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={selectedTopics.size === topics.length}
                        onChange={toggleAll}
                        className="rounded"
                      />
                    </th>
                    <th 
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
                      onClick={() => handleSort('title')}
                    >
                      <div className="flex items-center">
                        Title
                        {sortBy === 'title' && <ArrowUpDown className="w-4 h-4 ml-1" />}
                      </div>
                    </th>
                    <th 
                      className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
                      onClick={() => handleSort('priority')}
                    >
                      <div className="flex items-center">
                        Priority
                        {sortBy === 'priority' && <ArrowUpDown className="w-4 h-4 ml-1" />}
                      </div>
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Description
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Source
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredAndSortedTopics.map((topic, index) => (
                    <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={selectedTopics.has(index)}
                          onChange={() => toggleTopic(index)}
                          className="rounded"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <div className="font-medium">{topic.title}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          topic.priority >= 8 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                          topic.priority >= 5 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                          'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
                        }`}>
                          {topic.priority}/10
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-500 dark:text-gray-400 max-w-md truncate">
                          {topic.description}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {topic.sourceFile}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Statistics */}
          <div className="mt-4 bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {topics.length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Total Topics
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {topics.filter(t => t.priority >= 8).length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  High Priority
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                  {topics.filter(t => t.priority >= 5 && t.priority < 8).length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Medium Priority
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600 dark:text-gray-400">
                  {topics.filter(t => t.priority < 5).length}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Low Priority
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default TopicDiscoveryPage;
