import React, { useState } from 'react';
import { useJobs } from '../hooks/useAPI';
import JobFilters from '../components/jobs/JobFilters';
import JobList from '../components/jobs/JobList';
import JobDetail from '../components/jobs/JobDetail';
import CreateJobDialog from '../components/jobs/CreateJobDialog';
import GenerateContentDialog from '../components/jobs/GenerateContentDialog';
import { Plus } from 'lucide-react';

const JobsPage: React.FC = () => {
  const { jobs, loading, createJob, pauseJob, resumeJob, cancelJob, refresh } = useJobs();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [filters, setFilters] = useState({
    search: '',
    status: 'all',
    dateFrom: '',
    dateTo: '',
  });

  const filteredJobs = jobs.filter(job => {
    if (filters.search && !job.job_id.includes(filters.search)) return false;
    if (filters.status !== 'all' && job.status !== filters.status) return false;
    return true;
  });

  const selectedJob = jobs.find(j => j.job_id === selectedJobId);

  const handleBatchPause = async () => {
    for (const jobId of selectedJobs) {
      await pauseJob(jobId);
    }
  };

  const handleBatchResume = async () => {
    for (const jobId of selectedJobs) {
      await resumeJob(jobId);
    }
  };

  const handleBatchCancel = async () => {
    if (confirm(`Cancel ${selectedJobs.size} jobs?`)) {
      for (const jobId of selectedJobs) {
        await cancelJob(jobId);
      }
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Jobs Management</h1>
          <div className="flex gap-2">
            <button
              onClick={() => setShowGenerateDialog(true)}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Generate Content
            </button>
            <button
              onClick={() => setShowCreateDialog(true)}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center gap-2"
            >
              <Plus size={16} />
              Create Job
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white border-b px-6 py-3">
        <JobFilters filters={filters} onChange={setFilters} onRefresh={refresh} />
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className={selectedJobId ? 'w-1/2 border-r' : 'w-full'}>
          <JobList
            jobs={filteredJobs}
            selectedJobs={selectedJobs}
            onSelectJobs={setSelectedJobs}
            onSelectJob={setSelectedJobId}
            onPauseJob={pauseJob}
            onResumeJob={resumeJob}
            onCancelJob={cancelJob}
          />
          
          {selectedJobs.size > 0 && (
            <div className="border-t p-4 bg-gray-50 flex items-center justify-between">
              <span className="text-sm text-gray-600">
                {selectedJobs.size} selected
              </span>
              <div className="flex gap-2">
                <button
                  onClick={handleBatchPause}
                  className="px-3 py-1 text-sm bg-yellow-500 text-white rounded hover:bg-yellow-600"
                >
                  Pause All
                </button>
                <button
                  onClick={handleBatchResume}
                  className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
                >
                  Resume All
                </button>
                <button
                  onClick={handleBatchCancel}
                  className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                >
                  Cancel All
                </button>
              </div>
            </div>
          )}
        </div>

        {selectedJob && (
          <div className="w-1/2 overflow-auto">
            <JobDetail
              job={selectedJob}
              onClose={() => setSelectedJobId(null)}
              onPause={() => pauseJob(selectedJob.job_id)}
              onResume={() => resumeJob(selectedJob.job_id)}
              onCancel={() => cancelJob(selectedJob.job_id)}
            />
          </div>
        )}
      </div>

      {showCreateDialog && (
        <CreateJobDialog
          onClose={() => setShowCreateDialog(false)}
          onCreate={createJob}
        />
      )}

      {showGenerateDialog && (
        <GenerateContentDialog
          onClose={() => setShowGenerateDialog(false)}
          onCreate={createJob}
        />
      )}
    </div>
  );
};

export default JobsPage;
