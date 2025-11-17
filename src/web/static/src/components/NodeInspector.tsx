import React, { useState, useEffect } from 'react';
import { Node } from 'reactflow';
import { Agent } from '@/types';

interface NodeInspectorProps {
  node: Node;
  agents: Record<string, Agent>;
  onUpdateNode: (nodeId: string, data: any) => void;
}

const NodeInspector: React.FC<NodeInspectorProps> = ({
  node,
  agents,
  onUpdateNode,
}) => {
  const [config, setConfig] = useState<Record<string, any>>(
    node.data.config || {}
  );
  const [label, setLabel] = useState(node.data.label || '');

  useEffect(() => {
    setConfig(node.data.config || {});
    setLabel(node.data.label || '');
  }, [node.id, node.data.config, node.data.label]);

  const agent = node.data.agentId ? agents[node.data.agentId] : null;

  const handleLabelChange = (newLabel: string) => {
    setLabel(newLabel);
    onUpdateNode(node.id, { label: newLabel });
  };

  const handleConfigChange = (key: string, value: any) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    onUpdateNode(node.id, { config: newConfig });
  };

  const renderInputFields = () => {
    if (!agent || !agent.contract.inputs.properties) {
      return (
        <div className="text-sm text-gray-500">
          No configuration available
        </div>
      );
    }

    const properties = agent.contract.inputs.properties;
    const required = agent.contract.inputs.required || [];

    return Object.entries(properties).map(([key, schema]: [string, any]) => {
      if (key === 'config') return null; // Skip the config object itself

      const isRequired = required.includes(key);
      const value = config[key] || '';

      return (
        <div key={key} className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {key}
            {isRequired && <span className="text-red-500 ml-1">*</span>}
          </label>
          
          {schema.type === 'string' && (
            <input
              type="text"
              value={value}
              onChange={(e) => handleConfigChange(key, e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder={schema.description || `Enter ${key}`}
            />
          )}
          
          {schema.type === 'number' && (
            <input
              type="number"
              value={value}
              onChange={(e) => handleConfigChange(key, parseFloat(e.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder={schema.description || `Enter ${key}`}
            />
          )}
          
          {schema.type === 'boolean' && (
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => handleConfigChange(key, e.target.checked)}
                className="rounded border-gray-300 text-primary-500 focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-gray-600">
                {schema.description || key}
              </span>
            </label>
          )}
          
          {schema.description && (
            <p className="mt-1 text-xs text-gray-500">{schema.description}</p>
          )}
        </div>
      );
    });
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Node Inspector</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {/* Basic Info */}
        <div className="mb-6">
          <h4 className="font-medium text-gray-900 mb-3">Basic Information</h4>
          
          <div className="mb-4">
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

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Label
            </label>
            <input
              type="text"
              value={label}
              onChange={(e) => handleLabelChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Node label"
            />
          </div>

          {agent && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Agent Type
              </label>
              <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                <div className="font-medium text-sm">{agent.id}</div>
                <div className="text-xs text-gray-500 mt-1">
                  v{agent.version}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Agent Details */}
        {agent && (
          <div className="mb-6">
            <h4 className="font-medium text-gray-900 mb-3">Agent Details</h4>
            
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-gray-600">Description:</span>
                <p className="text-gray-900 mt-1">{agent.description}</p>
              </div>
              
              <div className="flex flex-wrap gap-2 mt-3">
                {agent.capabilities.async && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                    Async
                  </span>
                )}
                {agent.capabilities.stateful && (
                  <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                    Stateful
                  </span>
                )}
                {agent.capabilities.model_switchable && (
                  <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
                    Model Switchable
                  </span>
                )}
              </div>

              <div className="mt-3">
                <span className="text-gray-600">Resources:</span>
                <ul className="mt-1 text-gray-900 space-y-1">
                  <li>Runtime: {agent.resources.max_runtime_s}s</li>
                  <li>Tokens: {agent.resources.max_tokens}</li>
                  <li>Memory: {agent.resources.max_memory_mb}MB</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Configuration */}
        <div>
          <h4 className="font-medium text-gray-900 mb-3">Configuration</h4>
          {renderInputFields()}
        </div>
      </div>
    </div>
  );
};

export default NodeInspector;
