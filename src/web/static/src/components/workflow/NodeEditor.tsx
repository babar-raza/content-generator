import React, { useState, useEffect } from 'react';
import { Node } from 'reactflow';
import { Agent } from '@/types';

interface NodeEditorProps {
  node: Node;
  agents: Record<string, Agent>;
  onSave: (node: Node) => void;
  onClose: () => void;
}

const NodeEditor: React.FC<NodeEditorProps> = ({ 
  node, 
  agents,
  onSave, 
  onClose 
}) => {
  const [label, setLabel] = useState(node.data?.label || '');
  const [agentId, setAgentId] = useState(node.data?.agentId || '');
  const [action, setAction] = useState(node.data?.action || '');
  const [inputs, setInputs] = useState<string[]>(
    Array.isArray(node.data?.inputs) ? node.data.inputs : []
  );
  const [outputs, setOutputs] = useState<string[]>(
    Array.isArray(node.data?.outputs) ? node.data.outputs : []
  );
  const [config, setConfig] = useState(
    JSON.stringify(node.data?.config || {}, null, 2)
  );
  const [params, setParams] = useState(
    JSON.stringify(node.data?.params || {}, null, 2)
  );
  const [configError, setConfigError] = useState<string | null>(null);
  const [paramsError, setParamsError] = useState<string | null>(null);

  const selectedAgent = agents[agentId];

  const handleSave = () => {
    // Validate JSON
    let configObj = {};
    let paramsObj = {};

    try {
      configObj = config.trim() ? JSON.parse(config) : {};
    } catch (e) {
      setConfigError('Invalid JSON in configuration');
      return;
    }

    try {
      paramsObj = params.trim() ? JSON.parse(params) : {};
    } catch (e) {
      setParamsError('Invalid JSON in parameters');
      return;
    }

    const updatedNode: Node = {
      ...node,
      data: {
        ...node.data,
        label,
        agentId,
        action,
        inputs,
        outputs,
        config: configObj,
        params: paramsObj
      }
    };

    onSave(updatedNode);
    onClose();
  };

  const addInput = () => {
    setInputs([...inputs, '']);
  };

  const removeInput = (index: number) => {
    setInputs(inputs.filter((_, i) => i !== index));
  };

  const updateInput = (index: number, value: string) => {
    const newInputs = [...inputs];
    newInputs[index] = value;
    setInputs(newInputs);
  };

  const addOutput = () => {
    setOutputs([...outputs, '']);
  };

  const removeOutput = (index: number) => {
    setOutputs(outputs.filter((_, i) => i !== index));
  };

  const updateOutput = (index: number, value: string) => {
    const newOutputs = [...outputs];
    newOutputs[index] = value;
    setOutputs(newOutputs);
  };

  useEffect(() => {
    // Update label when agent changes
    if (agentId && agents[agentId]) {
      setLabel(agents[agentId].description);
    }
  }, [agentId, agents]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">
            Edit Node: {node.id}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {/* Node ID (read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Node ID
            </label>
            <input
              type="text"
              value={node.id}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500"
            />
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Display Name
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Enter display name"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Agent Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Agent
            </label>
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">Select an agent</option>
              {Object.entries(agents).map(([id, agent]) => (
                <option key={id} value={id}>
                  {agent.description}
                </option>
              ))}
            </select>
            {selectedAgent && (
              <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                <div><strong>Category:</strong> {selectedAgent.category || 'General'}</div>
                <div><strong>Async:</strong> {selectedAgent.capabilities.async ? 'Yes' : 'No'}</div>
                <div><strong>Stateful:</strong> {selectedAgent.capabilities.stateful ? 'Yes' : 'No'}</div>
              </div>
            )}
          </div>

          {/* Action */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Action (optional)
            </label>
            <input
              type="text"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="e.g., gather_sources, create_outline"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Inputs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Inputs
              </label>
              <button
                onClick={addInput}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                + Add Input
              </button>
            </div>
            <div className="space-y-2">
              {inputs.map((input, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => updateInput(index, e.target.value)}
                    placeholder="Input name"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <button
                    onClick={() => removeInput(index)}
                    className="px-3 py-2 text-red-600 hover:text-red-700 transition-colors"
                  >
                    ×
                  </button>
                </div>
              ))}
              {inputs.length === 0 && (
                <div className="text-sm text-gray-500 italic">No inputs defined</div>
              )}
            </div>
          </div>

          {/* Outputs */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                Outputs
              </label>
              <button
                onClick={addOutput}
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                + Add Output
              </button>
            </div>
            <div className="space-y-2">
              {outputs.map((output, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={output}
                    onChange={(e) => updateOutput(index, e.target.value)}
                    placeholder="Output name"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <button
                    onClick={() => removeOutput(index)}
                    className="px-3 py-2 text-red-600 hover:text-red-700 transition-colors"
                  >
                    ×
                  </button>
                </div>
              ))}
              {outputs.length === 0 && (
                <div className="text-sm text-gray-500 italic">No outputs defined</div>
              )}
            </div>
          </div>

          {/* Configuration (JSON) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Configuration (JSON)
            </label>
            <textarea
              value={config}
              onChange={(e) => {
                setConfig(e.target.value);
                setConfigError(null);
              }}
              placeholder="{}"
              rows={6}
              className={`w-full px-3 py-2 border rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                configError ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {configError && (
              <div className="mt-1 text-sm text-red-600">{configError}</div>
            )}
          </div>

          {/* Parameters (JSON) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Parameters (JSON)
            </label>
            <textarea
              value={params}
              onChange={(e) => {
                setParams(e.target.value);
                setParamsError(null);
              }}
              placeholder="{}"
              rows={6}
              className={`w-full px-3 py-2 border rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 ${
                paramsError ? 'border-red-500' : 'border-gray-300'
              }`}
            />
            {paramsError && (
              <div className="mt-1 text-sm text-red-600">{paramsError}</div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-white bg-primary-500 rounded-lg hover:bg-primary-600 transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default NodeEditor;
