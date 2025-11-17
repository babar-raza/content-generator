import React, { useState } from 'react';
import { useCheckpoints } from '../hooks/useCheckpoints';
import JobSelector from '../components/checkpoints/JobSelector';
import CheckpointList from '../components/checkpoints/CheckpointList';
import CheckpointDetail from '../components/checkpoints/CheckpointDetail';
import CleanupDialog from '../components/checkpoints/CleanupDialog';
import { Trash2, RefreshCw } from 'lucide-react';

const CheckpointsPage: React.FC = () => {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<string | null>(null);
  const [showCleanupDialog, setShowCleanupDialog] = useState(false);

  const { 
    checkpoints, 
    loading, 
    restore, 
    deleteCheckpoint, 
    cleanup, 
    refresh 
  } = useCheckpoints(selectedJobId);

  const selectedCheckpoint = checkpoints.find(c => c.checkpoint_id === selectedCheckpointId);

  const handleRestore = async (checkpointId: string, resume: boolean) => {
    try {
      const result = await restore(checkpointId, resume);
      alert(`Checkpoint restored! Job status: ${result.job_status}`);
      if (resume) {
        window.location.href = '/jobs';
      }
    } catch (error: any) {
      alert(`Failed to restore: ${error.message}`);
    }
  };

  const handleDelete = async (checkpointId: string) => {
    if (confirm('Delete this checkpoint?')) {
      try {
        await deleteCheckpoint(checkpointId);
        setSelectedCheckpointId(null);
        alert('Checkpoint deleted');
      } catch (error: any) {
        alert(`Failed to delete: ${error.message}`);
      }
    }
  };

  const handleCleanup = async (keepLast: number) => {
    try {
      const result = await cleanup(selectedJobId!, keepLast);
      alert(`Cleanup complete: ${result.deleted_count} deleted, ${result.kept_count} kept`);
      setShowCleanupDialog(false);
      refresh();
    } catch (error: any) {
      alert(`Cleanup failed: ${error.message}`);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Checkpoint Management</h1>
          <div className="flex gap-2">
            <button
              onClick={refresh}
              disabled={!selectedJobId}
              className="px-4 py-2 border rounded hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
            <button
              onClick={() => setShowCleanupDialog(true)}
              disabled={!selectedJobId || checkpoints.length === 0}
              className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 flex items-center gap-2 disabled:opacity-50"
            >
              <Trash2 size={16} />
              Cleanup Old
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white border-b px-6 py-3">
        <JobSelector
          selectedJobId={selectedJobId}
          onSelectJob={setSelectedJobId}
        />
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className={selectedCheckpointId ? 'w-1/2 border-r' : 'w-full'}>
          {!selectedJobId ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              Select a job to view checkpoints
            </div>
          ) : loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : checkpoints.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              No checkpoints found for this job
            </div>
          ) : (
            <CheckpointList
              checkpoints={checkpoints}
              selectedId={selectedCheckpointId}
              onSelect={setSelectedCheckpointId}
              onRestore={handleRestore}
              onDelete={handleDelete}
            />
          )}
        </div>

        {selectedCheckpoint && (
          <div className="w-1/2 overflow-auto">
            <CheckpointDetail
              checkpoint={selectedCheckpoint as any}
              onClose={() => setSelectedCheckpointId(null)}
              onRestore={handleRestore}
              onDelete={handleDelete}
            />
          </div>
        )}
      </div>

      {showCleanupDialog && selectedJobId && (
        <CleanupDialog
          jobId={selectedJobId}
          totalCheckpoints={checkpoints.length}
          onClose={() => setShowCleanupDialog(false)}
          onCleanup={handleCleanup}
        />
      )}
    </div>
  );
};

export default CheckpointsPage;
