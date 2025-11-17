import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { WorkflowTemplate } from '@/types';

export function useWorkflows() {
  const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWorkflows();
  }, []);

  const loadWorkflows = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getWorkflows();
      const workflowArray = Array.isArray(data) ? data : Object.values(data);
      setWorkflows(workflowArray);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load workflows');
      console.error('Failed to load workflows:', err);
    } finally {
      setLoading(false);
    }
  };

  return {
    workflows,
    loading,
    error,
    refetch: loadWorkflows,
  };
}

export default useWorkflows;
