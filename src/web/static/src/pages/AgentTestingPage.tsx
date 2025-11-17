import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { 
  Play, 
  Save, 
  Upload,
  Clock,
  CheckCircle,
  XCircle,
  Copy
} from 'lucide-react';

interface AgentCategory {
  name: string;
  agents: string[];
}

interface TestCase {
  id: string;
  name: string;
  agentId: string;
  input: string;
  context?: string;
}

interface ExecutionHistory {
  id: string;
  agentId: string;
  timestamp: string;
  duration: number;
  success: boolean;
  input: any;
  output: any;
  error?: string;
}

const AgentTestingPage: React.FC = () => {
  const [categories, setCategories] = useState<AgentCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [inputJson, setInputJson] = useState('{\n  \n}');
  const [contextJson, setContextJson] = useState('{}');
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState<any>(null);
  const [error, setError] = useState<string>('');
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [history, setHistory] = useState<ExecutionHistory[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [testCaseName, setTestCaseName] = useState('');

  // Example inputs for common agents
  const exampleInputs: Record<string, any> = {
    topic_identifier: {
      content: 'Sample blog content about AI and machine learning...',
      metadata: { source: 'kb', format: 'markdown' }
    },
    content_generator: {
      topic: 'Getting Started with Python',
      template: 'blog_post',
      style: 'technical'
    },
    code_validator: {
      code: 'public void Example() { }',
      language: 'csharp',
      api_reference: 'Aspose.Words'
    },
    seo_optimizer: {
      title: 'Introduction to Document Processing',
      content: 'Learn about document processing...',
      keywords: ['documents', 'processing', 'API']
    }
  };

  useEffect(() => {
    loadAgents();
    loadTestCases();
    loadHistory();
  }, []);

  const loadAgents = async () => {
    try {
      const response = await apiClient.getAgents();
      const agentList = Object.keys(response);
      
      // Group agents by category (simplified)
      const grouped: Record<string, string[]> = {
        'Ingestion': agentList.filter(a => a.includes('ingest')),
        'Content': agentList.filter(a => a.includes('content') || a.includes('generator')),
        'Validation': agentList.filter(a => a.includes('validator') || a.includes('verify')),
        'SEO': agentList.filter(a => a.includes('seo') || a.includes('optimizer')),
        'Other': agentList.filter(a => 
          !a.includes('ingest') && 
          !a.includes('content') && 
          !a.includes('generator') &&
          !a.includes('validator') && 
          !a.includes('verify') &&
          !a.includes('seo') && 
          !a.includes('optimizer')
        )
      };

      const cats = Object.entries(grouped)
        .filter(([_, agents]) => agents.length > 0)
        .map(([name, agents]) => ({ name, agents }));
      
      setCategories(cats);
      
      if (cats.length > 0 && cats[0].agents.length > 0) {
        setSelectedCategory(cats[0].name);
        setSelectedAgent(cats[0].agents[0]);
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
    }
  };

  const loadTestCases = () => {
    const saved = localStorage.getItem('agentTestCases');
    if (saved) {
      setTestCases(JSON.parse(saved));
    }
  };

  const loadHistory = () => {
    const saved = localStorage.getItem('agentExecutionHistory');
    if (saved) {
      setHistory(JSON.parse(saved));
    }
  };

  const saveTestCase = () => {
    if (!testCaseName) {
      alert('Please enter a test case name');
      return;
    }

    try {
      JSON.parse(inputJson);
    } catch (e) {
      alert('Invalid JSON input');
      return;
    }

    const newCase: TestCase = {
      id: `test_${Date.now()}`,
      name: testCaseName,
      agentId: selectedAgent,
      input: inputJson,
      context: contextJson
    };

    const updated = [...testCases, newCase];
    setTestCases(updated);
    localStorage.setItem('agentTestCases', JSON.stringify(updated));
    
    setShowSaveDialog(false);
    setTestCaseName('');
  };

  const loadTestCase = (testCase: TestCase) => {
    setSelectedAgent(testCase.agentId);
    setInputJson(testCase.input);
    setContextJson(testCase.context || '{}');
  };

  const deleteTestCase = (id: string) => {
    const updated = testCases.filter(tc => tc.id !== id);
    setTestCases(updated);
    localStorage.setItem('agentTestCases', JSON.stringify(updated));
  };

  const handleInvoke = async () => {
    setLoading(true);
    setError('');
    setOutput(null);

    const startTime = Date.now();

    try {
      const input = JSON.parse(inputJson);
      const context = contextJson ? JSON.parse(contextJson) : undefined;

      const result = await apiClient.invokeAgent(selectedAgent, input, context);
      
      const duration = Date.now() - startTime;

      // Save to history
      const historyEntry: ExecutionHistory = {
        id: `exec_${Date.now()}`,
        agentId: selectedAgent,
        timestamp: new Date().toISOString(),
        duration,
        success: !result.error,
        input,
        output: result.result || result.error,
        error: result.error?.message
      };

      const updatedHistory = [historyEntry, ...history].slice(0, 50);
      setHistory(updatedHistory);
      localStorage.setItem('agentExecutionHistory', JSON.stringify(updatedHistory));

      if (result.error) {
        setError(result.error.message || 'Agent invocation failed');
      } else {
        setOutput(result.result);
      }
    } catch (e: any) {
      setError(e.message || 'Invalid JSON or invocation failed');
    } finally {
      setLoading(false);
    }
  };

  const loadExample = () => {
    const example = exampleInputs[selectedAgent];
    if (example) {
      setInputJson(JSON.stringify(example, null, 2));
    } else {
      setInputJson('{\n  "content": "Sample input"\n}');
    }
  };

  const copyOutput = () => {
    if (output) {
      navigator.clipboard.writeText(JSON.stringify(output, null, 2));
    }
  };

  const getAgentsForCategory = () => {
    const category = categories.find(c => c.name === selectedCategory);
    return category?.agents || [];
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Agent Testing</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Test agent invocations with custom inputs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Panel - Input */}
        <div className="space-y-6">
          {/* Agent Selection */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Agent Selection</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Category
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => {
                    setSelectedCategory(e.target.value);
                    const agents = categories.find(c => c.name === e.target.value)?.agents || [];
                    if (agents.length > 0) {
                      setSelectedAgent(agents[0]);
                    }
                  }}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                >
                  {categories.map(cat => (
                    <option key={cat.name} value={cat.name}>
                      {cat.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Agent
                </label>
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
                >
                  {getAgentsForCategory().map(agent => (
                    <option key={agent} value={agent}>
                      {agent}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Input Editor */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Input JSON</h3>
              <button
                onClick={loadExample}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                Load Example
              </button>
            </div>
            
            <textarea
              value={inputJson}
              onChange={(e) => setInputJson(e.target.value)}
              className="w-full h-64 px-4 py-2 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              placeholder="Enter JSON input..."
            />
          </div>

          {/* Context Editor */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Context JSON (Optional)</h3>
            
            <textarea
              value={contextJson}
              onChange={(e) => setContextJson(e.target.value)}
              className="w-full h-32 px-4 py-2 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
              placeholder="Enter context JSON..."
            />
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleInvoke}
              disabled={loading}
              className="flex-1 flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Clock className="w-4 h-4 mr-2 animate-spin" />
                  Invoking...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Invoke Agent
                </>
              )}
            </button>
            
            <button
              onClick={() => setShowSaveDialog(true)}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <Save className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Right Panel - Output */}
        <div className="space-y-6">
          {/* Output Display */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Output</h3>
              {output && (
                <button
                  onClick={copyOutput}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  <Copy className="w-4 h-4" />
                </button>
              )}
            </div>
            
            {error ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-start">
                  <XCircle className="w-5 h-5 text-red-500 mr-2 mt-0.5" />
                  <div className="text-red-700 dark:text-red-300 text-sm">
                    {error}
                  </div>
                </div>
              </div>
            ) : output ? (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-start mb-2">
                  <CheckCircle className="w-5 h-5 text-green-500 mr-2 mt-0.5" />
                  <div className="text-green-700 dark:text-green-300 font-medium">
                    Success
                  </div>
                </div>
                <pre className="mt-4 p-4 bg-gray-900 text-gray-100 rounded-lg overflow-auto max-h-96 text-sm">
                  {JSON.stringify(output, null, 2)}
                </pre>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-12">
                No output yet. Invoke an agent to see results.
              </div>
            )}
          </div>

          {/* Test Cases */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Saved Test Cases</h3>
            
            {testCases.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                No saved test cases
              </div>
            ) : (
              <div className="space-y-2">
                {testCases.map(tc => (
                  <div 
                    key={tc.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <div>
                      <div className="font-medium">{tc.name}</div>
                      <div className="text-sm text-gray-500">{tc.agentId}</div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => loadTestCase(tc)}
                        className="text-blue-600 hover:text-blue-700"
                      >
                        <Upload className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteTestCase(tc.id)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Execution History */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Execution History</h3>
            
            {history.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                No execution history
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {history.slice(0, 10).map(entry => (
                  <div 
                    key={entry.id}
                    className="p-3 border rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium">{entry.agentId}</div>
                      <div className="flex items-center gap-2">
                        {entry.success ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                        <span className="text-xs text-gray-500">
                          {entry.duration}ms
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(entry.timestamp).toLocaleString()}
                    </div>
                    {entry.error && (
                      <div className="mt-2 text-xs text-red-600">
                        {entry.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Save Test Case</h3>
            
            <input
              type="text"
              value={testCaseName}
              onChange={(e) => setTestCaseName(e.target.value)}
              placeholder="Test case name"
              className="w-full px-4 py-2 border rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600"
            />
            
            <div className="flex gap-2">
              <button
                onClick={saveTestCase}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setShowSaveDialog(false);
                  setTestCaseName('');
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentTestingPage;
