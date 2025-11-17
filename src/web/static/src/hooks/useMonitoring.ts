import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '@/api/client';
import {
  SystemHealth,
  AgentStatus,
  SystemMetrics,
  FlowRealtimeResponse,
  BottleneckResponse,
} from '@/types/monitoring';
import { Job } from '@/types';

interface MonitoringData {
  health: SystemHealth | null;
  agents: AgentStatus[];
  metrics: SystemMetrics | null;
  flows: FlowRealtimeResponse | null;
  bottlenecks: BottleneckResponse | null;
  runningJobs: Job[];
  loading: boolean;
  error: string | null;
}

interface UseMonitoringOptions {
  pollInterval?: number; // milliseconds
  enabled?: boolean;
}

export const useMonitoring = (options: UseMonitoringOptions = {}) => {
  const { pollInterval = 10000, enabled = true } = options;
  
  const [data, setData] = useState<MonitoringData>({
    health: null,
    agents: [],
    metrics: null,
    flows: null,
    bottlenecks: null,
    runningJobs: [],
    loading: true,
    error: null,
  });

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    if (!enabled) return;

    try {
      // Fetch all monitoring data in parallel
      const [health, agents, metrics, flows, bottlenecks, runningJobs] = await Promise.all([
        apiClient.getSystemHealth().catch(() => null),
        apiClient.getAgentStatuses().catch(() => []),
        apiClient.getSystemMetrics().catch(() => null),
        apiClient.getRealtimeFlows(60).catch(() => null),
        apiClient.getBottlenecks(1000).catch(() => null),
        apiClient.getRunningJobs().catch(() => []),
      ]);

      if (isMountedRef.current) {
        setData({
          health,
          agents,
          metrics,
          flows,
          bottlenecks,
          runningJobs,
          loading: false,
          error: null,
        });
      }
    } catch (err) {
      if (isMountedRef.current) {
        setData((prev) => ({
          ...prev,
          loading: false,
          error: err instanceof Error ? err.message : 'Failed to fetch monitoring data',
        }));
      }
    }
  }, [enabled]);

  useEffect(() => {
    isMountedRef.current = true;

    // Initial fetch
    fetchData();

    // Set up polling if enabled
    if (enabled && pollInterval > 0) {
      pollIntervalRef.current = setInterval(fetchData, pollInterval);
    }

    return () => {
      isMountedRef.current = false;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [fetchData, enabled, pollInterval]);

  const refresh = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return {
    ...data,
    refresh,
  };
};

export default useMonitoring;
