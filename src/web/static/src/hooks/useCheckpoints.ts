import { useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { CheckpointMetadata, CheckpointResponse, RestoreResponse, CleanupResponse } from '../types';

export function useCheckpoints(jobId: string | null) {
  const [checkpoints, setCheckpoints] = useState<CheckpointMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchCheckpoints = useCallback(async () => {
    if (!jobId) {
      setCheckpoints([]);
      return;
    }

    try {
      setLoading(true);
      const data = await apiClient.listCheckpoints(jobId);
      setCheckpoints(data.checkpoints || []);
      setError(null);
    } catch (err) {
      console.error('Failed to fetch checkpoints:', err);
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchCheckpoints();
  }, [fetchCheckpoints]);

  const restore = useCallback(async (
    checkpointId: string, 
    resume: boolean
  ): Promise<RestoreResponse> => {
    return await apiClient.restoreCheckpoint(checkpointId, resume);
  }, []);

  const deleteCheckpoint = useCallback(async (checkpointId: string) => {
    await apiClient.deleteCheckpoint(checkpointId);
    await fetchCheckpoints();
  }, [fetchCheckpoints]);

  const cleanup = useCallback(async (
    jobId: string, 
    keepLast: number
  ): Promise<CleanupResponse> => {
    return await apiClient.cleanupCheckpoints(jobId, keepLast);
  }, []);

  return {
    checkpoints,
    loading,
    error,
    restore,
    deleteCheckpoint,
    cleanup,
    refresh: fetchCheckpoints,
  };
}
