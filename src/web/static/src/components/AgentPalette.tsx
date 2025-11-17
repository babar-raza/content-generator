import React, { useMemo, useState } from 'react';
import { Agent, AgentCategory } from '@/types';

interface AgentPaletteProps {
  agents: Agent[];
  onDragStart: (agent: Agent) => void;
}

const categorizeAgents = (agents: Agent[]): AgentCategory[] => {
  const categories: Record<string, Agent[]> = {};
  
  agents.forEach((agent) => {
    const category = agent.category || 'General';
    if (!categories[category]) {
      categories[category] = [];
    }
    categories[category].push(agent);
  });
  
  return Object.entries(categories).map(([name, agents]) => ({
    name,
    icon: getCategoryIcon(name),
    agents,
  }));
};

const getCategoryIcon = (category: string): string => {
  const icons: Record<string, string> = {
    ingestion: '📥',
    research: '🔍',
    content: '✍️',
    code: '💻',
    seo: '📊',
    publishing: '🚀',
    support: '🛠️',
    general: '⚙️',
  };
  
  return icons[category.toLowerCase()] || '⚙️';
};

const AgentCard: React.FC<{
  agent: Agent;
  onDragStart: (agent: Agent) => void;
}> = ({ agent, onDragStart }) => {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('application/json', JSON.stringify(agent));
    onDragStart(agent);
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className="bg-white border border-gray-200 rounded-lg p-3 cursor-move hover:shadow-md transition-shadow"
    >
      <div className="font-medium text-sm text-gray-900 truncate">
        {agent.id}
      </div>
      <div className="text-xs text-gray-500 mt-1 line-clamp-2">
        {agent.description}
      </div>
      <div className="flex gap-1 mt-2">
        {agent.capabilities.async && (
          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
            async
          </span>
        )}
        {agent.capabilities.stateful && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
            stateful
          </span>
        )}
      </div>
    </div>
  );
};

const AgentPalette: React.FC<AgentPaletteProps> = ({ agents, onDragStart }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(['ingestion', 'research', 'content'])
  );

  const categories = useMemo(() => categorizeAgents(agents), [agents]);

  const filteredCategories = useMemo(() => {
    if (!searchTerm) return categories;
    
    return categories
      .map((category) => ({
        ...category,
        agents: category.agents.filter(
          (agent) =>
            agent.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
            agent.description.toLowerCase().includes(searchTerm.toLowerCase())
        ),
      }))
      .filter((category) => category.agents.length > 0);
  }, [categories, searchTerm]);

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(categoryName)) {
        next.delete(categoryName);
      } else {
        next.add(categoryName);
      }
      return next;
    });
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      <div className="p-4 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Agents</h2>
        <input
          type="text"
          placeholder="Search agents..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {filteredCategories.map((category) => (
          <div key={category.name} className="bg-white rounded-lg border border-gray-200">
            <button
              onClick={() => toggleCategory(category.name)}
              className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">{category.icon}</span>
                <span className="font-medium text-gray-900">{category.name}</span>
                <span className="text-sm text-gray-500">({category.agents.length})</span>
              </div>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${
                  expandedCategories.has(category.name) ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            
            {expandedCategories.has(category.name) && (
              <div className="p-3 space-y-2 border-t border-gray-200">
                {category.agents.map((agent) => (
                  <AgentCard
                    key={agent.id}
                    agent={agent}
                    onDragStart={onDragStart}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentPalette;
