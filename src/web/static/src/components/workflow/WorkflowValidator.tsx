import React, { useEffect, useState } from 'react';
import { Node, Edge } from 'reactflow';

export interface ValidationError {
  type: string;
  message: string;
  nodes?: string[];
}

export interface ValidationWarning {
  type: string;
  message: string;
  nodes?: string[];
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

interface WorkflowValidatorProps {
  nodes: Node[];
  edges: Edge[];
  onValidationChange?: (result: ValidationResult) => void;
}

const WorkflowValidator: React.FC<WorkflowValidatorProps> = ({ 
  nodes, 
  edges,
  onValidationChange 
}) => {
  const [result, setResult] = useState<ValidationResult>({
    valid: true,
    errors: [],
    warnings: []
  });

  useEffect(() => {
    const validate = () => {
      const errors: ValidationError[] = [];
      const warnings: ValidationWarning[] = [];

      // Check for cycles
      if (hasCycles(nodes, edges)) {
        errors.push({
          type: 'cycle',
          message: 'Workflow contains circular dependencies',
          nodes: findCycleNodes(nodes, edges)
        });
      }

      // Check for orphan nodes
      const orphans = findOrphanNodes(nodes, edges);
      if (orphans.length > 0) {
        warnings.push({
          type: 'orphan',
          message: `${orphans.length} node(s) are not connected`,
          nodes: orphans
        });
      }

      // Check for missing agent IDs
      nodes.forEach(node => {
        if (node.type === 'default' || node.type === 'agent') {
          const agentId = node.data?.agentId;
          if (!agentId) {
            errors.push({
              type: 'missing_agent',
              message: `Node "${node.data?.label || node.id}" is missing an agent`,
              nodes: [node.id]
            });
          }
        }
      });

      const validationResult = {
        valid: errors.length === 0,
        errors,
        warnings
      };

      setResult(validationResult);
      
      if (onValidationChange) {
        onValidationChange(validationResult);
      }
    };

    validate();
  }, [nodes, edges, onValidationChange]);

  if (result.valid && result.warnings.length === 0) {
    return (
      <div className="validation-panel bg-green-50 border border-green-200 rounded-lg p-3">
        <div className="flex items-center gap-2 text-green-700">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-medium">Workflow is valid</span>
        </div>
      </div>
    );
  }

  return (
    <div className="validation-panel space-y-3">
      {result.errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <h3 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Errors ({result.errors.length})
          </h3>
          <div className="space-y-2">
            {result.errors.map((error, i) => (
              <div key={i} className="text-sm text-red-700">
                <div className="font-medium">{error.message}</div>
                {error.nodes && error.nodes.length > 0 && (
                  <div className="text-xs text-red-600 mt-1">
                    Affected nodes: {error.nodes.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <h3 className="font-semibold text-yellow-800 mb-2 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Warnings ({result.warnings.length})
          </h3>
          <div className="space-y-2">
            {result.warnings.map((warning, i) => (
              <div key={i} className="text-sm text-yellow-700">
                <div className="font-medium">{warning.message}</div>
                {warning.nodes && warning.nodes.length > 0 && (
                  <div className="text-xs text-yellow-600 mt-1">
                    Affected nodes: {warning.nodes.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper functions
function hasCycles(nodes: Node[], edges: Edge[]): boolean {
  const graph: Record<string, string[]> = {};
  
  nodes.forEach(node => {
    graph[node.id] = [];
  });
  
  edges.forEach(edge => {
    if (graph[edge.source]) {
      graph[edge.source].push(edge.target);
    }
  });

  const visited = new Set<string>();
  const recStack = new Set<string>();

  function detectCycle(nodeId: string): boolean {
    visited.add(nodeId);
    recStack.add(nodeId);

    const neighbors = graph[nodeId] || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (detectCycle(neighbor)) {
          return true;
        }
      } else if (recStack.has(neighbor)) {
        return true;
      }
    }

    recStack.delete(nodeId);
    return false;
  }

  for (const nodeId in graph) {
    if (!visited.has(nodeId)) {
      if (detectCycle(nodeId)) {
        return true;
      }
    }
  }

  return false;
}

function findCycleNodes(nodes: Node[], edges: Edge[]): string[] {
  // Simplified - returns all nodes involved in any cycle
  // A more sophisticated implementation would identify the exact cycle
  if (!hasCycles(nodes, edges)) {
    return [];
  }
  
  // For now, return all connected nodes
  const connectedNodes = new Set<string>();
  edges.forEach(edge => {
    connectedNodes.add(edge.source);
    connectedNodes.add(edge.target);
  });
  
  return Array.from(connectedNodes);
}

function findOrphanNodes(nodes: Node[], edges: Edge[]): string[] {
  if (nodes.length <= 1) {
    return [];
  }

  const connectedNodes = new Set<string>();
  edges.forEach(edge => {
    connectedNodes.add(edge.source);
    connectedNodes.add(edge.target);
  });

  return nodes
    .filter(node => !connectedNodes.has(node.id))
    .map(node => node.id);
}

export default WorkflowValidator;
