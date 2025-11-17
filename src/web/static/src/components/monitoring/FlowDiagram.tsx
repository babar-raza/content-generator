import React, { useMemo } from 'react';
import { FlowRealtimeResponse, BottleneckResponse } from '@/types/monitoring';

interface FlowDiagramProps {
  flows: FlowRealtimeResponse | null;
  bottlenecks: BottleneckResponse | null;
  loading: boolean;
}

const FlowDiagram: React.FC<FlowDiagramProps> = ({ flows, bottlenecks, loading }) => {
  // Build agent graph from flows
  const agentGraph = useMemo(() => {
    if (!flows || !flows.flows.length) return { nodes: [], edges: [] };

    const nodesMap = new Map<string, { id: string; count: number; isBottleneck: boolean }>();
    const edges: { source: string; target: string; count: number; latency: number }[] = [];

    // Collect unique agents and edges
    flows.flows.forEach((flow) => {
      // Source node
      if (!nodesMap.has(flow.source_agent)) {
        nodesMap.set(flow.source_agent, {
          id: flow.source_agent,
          count: 0,
          isBottleneck: bottlenecks?.bottlenecks.some(b => b.agent_id === flow.source_agent) || false,
        });
      }
      const sourceNode = nodesMap.get(flow.source_agent)!;
      sourceNode.count++;

      // Target node
      if (!nodesMap.has(flow.target_agent)) {
        nodesMap.set(flow.target_agent, {
          id: flow.target_agent,
          count: 0,
          isBottleneck: bottlenecks?.bottlenecks.some(b => b.agent_id === flow.target_agent) || false,
        });
      }

      // Edge
      const edgeKey = `${flow.source_agent}-${flow.target_agent}`;
      const existingEdge = edges.find(
        (e) => e.source === flow.source_agent && e.target === flow.target_agent
      );
      
      if (existingEdge) {
        existingEdge.count++;
        existingEdge.latency += flow.latency_ms || 0;
      } else {
        edges.push({
          source: flow.source_agent,
          target: flow.target_agent,
          count: 1,
          latency: flow.latency_ms || 0,
        });
      }
    });

    return {
      nodes: Array.from(nodesMap.values()),
      edges: edges.map(e => ({ ...e, latency: e.latency / e.count })),
    };
  }, [flows, bottlenecks]);

  if (loading && !flows) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Agent Flow Diagram</h2>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-600">
            {flows?.count || 0} flows in last {flows?.window_seconds || 60}s
          </span>
          {bottlenecks && bottlenecks.count > 0 && (
            <span className="text-red-600">
              ⚠ {bottlenecks.count} {bottlenecks.count === 1 ? 'bottleneck' : 'bottlenecks'}
            </span>
          )}
        </div>
      </div>

      {agentGraph.nodes.length > 0 ? (
        <div className="space-y-6">
          {/* Simple visualization using divs */}
          <div className="flex flex-wrap gap-4 justify-center">
            {agentGraph.nodes.map((node) => (
              <div
                key={node.id}
                className={`px-4 py-3 rounded-lg border-2 ${
                  node.isBottleneck
                    ? 'bg-red-50 border-red-400 text-red-900'
                    : 'bg-blue-50 border-blue-400 text-blue-900'
                }`}
              >
                <div className="font-medium text-sm">{node.id}</div>
                <div className="text-xs opacity-75 mt-1">
                  {node.count} {node.count === 1 ? 'flow' : 'flows'}
                </div>
                {node.isBottleneck && (
                  <div className="text-xs font-semibold mt-1">⚠ Bottleneck</div>
                )}
              </div>
            ))}
          </div>

          {/* Flow connections */}
          {agentGraph.edges.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium text-gray-700 mb-3">Flow Connections</h3>
              <div className="space-y-2">
                {agentGraph.edges.map((edge, idx) => (
                  <div
                    key={`${edge.source}-${edge.target}-${idx}`}
                    className="flex items-center gap-3 p-2 bg-gray-50 rounded"
                  >
                    <span className="text-sm font-medium text-blue-700">
                      {edge.source}
                    </span>
                    <div className="flex-1 flex items-center gap-2">
                      <div className="flex-1 h-0.5 bg-blue-400"></div>
                      <span className="text-xs text-gray-600">
                        {edge.count} × {edge.latency.toFixed(0)}ms
                      </span>
                      <div className="w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-8 border-l-blue-400"></div>
                    </div>
                    <span className="text-sm font-medium text-blue-700">
                      {edge.target}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bottleneck details */}
          {bottlenecks && bottlenecks.bottlenecks.length > 0 && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <h3 className="text-sm font-semibold text-red-900 mb-3">
                Detected Bottlenecks
              </h3>
              <div className="space-y-2">
                {bottlenecks.bottlenecks.map((bottleneck) => (
                  <div
                    key={bottleneck.agent_id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="font-medium text-red-800">
                      {bottleneck.agent_id}
                    </span>
                    <div className="flex items-center gap-4">
                      <span className="text-red-700">
                        Avg: {bottleneck.avg_latency_ms.toFixed(0)}ms
                      </span>
                      <span className="text-red-700">
                        Max: {bottleneck.max_latency_ms.toFixed(0)}ms
                      </span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-semibold ${
                          bottleneck.severity === 'critical'
                            ? 'bg-red-200 text-red-900'
                            : bottleneck.severity === 'high'
                            ? 'bg-orange-200 text-orange-900'
                            : bottleneck.severity === 'medium'
                            ? 'bg-yellow-200 text-yellow-900'
                            : 'bg-gray-200 text-gray-900'
                        }`}
                      >
                        {bottleneck.severity.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          No flow data available
        </div>
      )}
    </div>
  );
};

export default FlowDiagram;
