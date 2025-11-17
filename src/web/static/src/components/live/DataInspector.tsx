import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Database, Eye, Code } from 'lucide-react';

interface DataInspectorProps {
  agentId: string;
  inputData?: any;
  outputData?: any;
  error?: string;
}

interface AccordionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

const Accordion: React.FC<AccordionProps> = ({ 
  title, 
  icon, 
  children, 
  defaultOpen = false 
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-sm">{title}</span>
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-600" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-600" />
        )}
      </button>
      {isOpen && (
        <div className="p-3 bg-white">
          {children}
        </div>
      )}
    </div>
  );
};

const JsonViewer: React.FC<{ data: any }> = ({ data }) => {
  if (!data) {
    return (
      <div className="text-sm text-gray-500 italic">
        No data available
      </div>
    );
  }

  const renderValue = (value: any, depth: number = 0): React.ReactNode => {
    const indent = depth * 16;

    if (value === null || value === undefined) {
      return <span className="text-gray-400">null</span>;
    }

    if (typeof value === 'boolean') {
      return <span className="text-purple-600">{value.toString()}</span>;
    }

    if (typeof value === 'number') {
      return <span className="text-blue-600">{value}</span>;
    }

    if (typeof value === 'string') {
      return <span className="text-green-600">"{value}"</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-600">[]</span>;
      }
      return (
        <div>
          <span className="text-gray-600">[</span>
          <div style={{ paddingLeft: '16px' }}>
            {value.map((item, index) => (
              <div key={index}>
                {renderValue(item, depth + 1)}
                {index < value.length - 1 && <span>,</span>}
              </div>
            ))}
          </div>
          <span className="text-gray-600">]</span>
        </div>
      );
    }

    if (typeof value === 'object') {
      const keys = Object.keys(value);
      if (keys.length === 0) {
        return <span className="text-gray-600">{'{}'}</span>;
      }
      return (
        <div>
          <span className="text-gray-600">{'{'}</span>
          <div style={{ paddingLeft: '16px' }}>
            {keys.map((key, index) => (
              <div key={key}>
                <span className="text-pink-600">"{key}"</span>
                <span className="text-gray-600">: </span>
                {renderValue(value[key], depth + 1)}
                {index < keys.length - 1 && <span>,</span>}
              </div>
            ))}
          </div>
          <span className="text-gray-600">{'}'}</span>
        </div>
      );
    }

    return <span>{String(value)}</span>;
  };

  return (
    <div className="font-mono text-xs bg-gray-50 p-3 rounded border border-gray-200 overflow-auto max-h-96">
      {renderValue(data)}
    </div>
  );
};

export const DataInspector: React.FC<DataInspectorProps> = ({
  agentId,
  inputData,
  outputData,
  error
}) => {
  return (
    <div className="bg-white rounded-lg shadow p-4 space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <Eye className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-semibold">Agent Data Inspector</h3>
      </div>

      <div className="mb-3">
        <div className="flex items-center gap-2 text-sm">
          <Database className="w-4 h-4 text-blue-500" />
          <span className="font-medium">Agent:</span>
          <span className="text-gray-700">{agentId}</span>
        </div>
      </div>

      <div className="space-y-2">
        <Accordion 
          title="Input Data" 
          icon={<Code className="w-4 h-4 text-blue-500" />}
          defaultOpen={false}
        >
          <JsonViewer data={inputData} />
        </Accordion>

        <Accordion 
          title="Output Data" 
          icon={<Code className="w-4 h-4 text-green-500" />}
          defaultOpen={!!outputData}
        >
          <JsonViewer data={outputData} />
        </Accordion>

        {error && (
          <Accordion 
            title="Error Details" 
            icon={<Code className="w-4 h-4 text-red-500" />}
            defaultOpen={true}
          >
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
              {error}
            </div>
          </Accordion>
        )}
      </div>
    </div>
  );
};
