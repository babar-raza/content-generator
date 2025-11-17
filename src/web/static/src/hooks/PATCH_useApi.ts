// Add these callbacks to src/web/static/src/hooks/useApi.ts
// Insert after the cancelJob callback in the useJobs function (around line 173)

  const archiveJob = useCallback(async (jobId: string) => {
    try:
      await apiClient.archiveJob(jobId);
      await fetchJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to archive job:', err);
      throw err;
    }
  }, [fetchJobs]);

  const unarchiveJob = useCallback(async (jobId: string) => {
    try {
      await apiClient.unarchiveJob(jobId);
      await fetchJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to unarchive job:', err);
      throw err;
    }
  }, [fetchJobs]);

  const retryJob = useCallback(async (jobId: string) => {
    try {
      await apiClient.retryJob(jobId);
      await fetchJobs(); // Refresh list
    } catch (err) {
      console.error('Failed to retry job:', err);
      throw err;
    }
  }, [fetchJobs]);

// Then update the return statement to include the new methods:
// Change the return statement (around line 175-185) to:

  return {
    jobs,
    loading,
    error,
    createJob,
    pauseJob,
    resumeJob,
    cancelJob,
    archiveJob,
    unarchiveJob,
    retryJob,
    refresh: fetchJobs,
  };
