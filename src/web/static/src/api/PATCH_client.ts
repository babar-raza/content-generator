// Add these three methods to src/web/static/src/api/client.ts
// Insert after the cancelJob method (around line 213)

  async archiveJob(jobId: string): Promise<void> {
    await this.apiClient.post(`/jobs/${jobId}/archive`);
  }

  async unarchiveJob(jobId: string): Promise<void> {
    await this.apiClient.post(`/jobs/${jobId}/unarchive`);
  }

  async retryJob(jobId: string): Promise<void> {
    await this.apiClient.post(`/jobs/${jobId}/retry`);
  }
