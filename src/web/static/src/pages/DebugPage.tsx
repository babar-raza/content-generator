import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { Play, Pause, SkipForward, Trash2, Plus, RefreshCw } from 'lucide-react';

interface DebugSession {
  id: string;
  job_id?: string;
  workflow_id?: string;
  status: string;
  breakpoints?: any[];
  trace?: any[];
  created_at?: string;
}

const DebugPage: React.FC = () => {
  const [sessions, setSessions] = useState<DebugSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<DebugSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newSessionConfig, setNewSessionConfig] = useState({
    job_id: '',
    workflow_id: '',
    breakpoints: []
  });

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await apiClient.getDebugSessions();
      setSessions(data.sessions || []);
    } catch (error) {
      console.error('Failed to load debug sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadSessionDetails = async (session: DebugSession) => {
    try {
      const details = await apiClient.getDebugSession(session.id);
      const trace = await apiClient.getDebugTrace(session.id).catch(() => ({ trace: [] }));
      setSelectedSession({
        ...details,
        trace: trace.trace || []
      });
    } catch (error) {
      console.error('Failed to load session details:', error);
      setSelectedSession(session);
    }
  };

  const createSession = async () => {
    try {
      const session = await apiClient.createDebugSession(newSessionConfig);
      await loadSessions();
      setShowCreateDialog(false);
      setNewSessionConfig({ job_id: '', workflow_id: '', breakpoints: [] });
      setSelectedSession(session);
    } catch (error) {
      console.error('Failed to create session:', error);
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await apiClient.deleteDebugSession(sessionId);
      if (selectedSession?.id === sessionId) {
        setSelectedSession(null);
      }
      await loadSessions();
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const stepDebug = async () => {
    if (!selectedSession) return;
    try {
      const result = await apiClient.stepDebug(selectedSession.id);
      await loadSessionDetails(selectedSession);
    } catch (error) {
      console.error('Failed to step:', error);
    }
  };

  const continueDebug = async () => {
    if (!selectedSession) return;
    try {
      const result = await apiClient.continueDebug(selectedSession.id);
      await loadSessionDetails(selectedSession);
    } catch (error) {
      console.error('Failed to continue:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
          <p className="text-gray-600">Loading debug sessions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Debug Console</h1>
          <p className="text-gray-600">Interactive workflow debugging</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCreateDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Session
          </button>
          <button
            onClick={loadSessions}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {showCreateDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">Create Debug Session</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Job ID</label>
                <input
                  type="text"
                  value={newSessionConfig.job_id}
                  onChange={e => setNewSessionConfig({ ...newSessionConfig, job_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="Optional"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Workflow ID</label>
                <input
                  type="text"
                  value={newSessionConfig.workflow_id}
                  onChange={e => setNewSessionConfig({ ...newSessionConfig, workflow_id: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg"
                  placeholder="Optional"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={createSession}
                  className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  Create
                </button>
                <button
                  onClick={() => setShowCreateDialog(false)}
                  className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="text-lg font-semibold">Debug Sessions ({sessions.length})</h2>
            </div>
            <div className="divide-y max-h-[600px] overflow-y-auto">
              {sessions.length === 0 ? (
                <div className="p-8 text-center text-gray-500">
                  <p>No debug sessions</p>
                  <p className="text-sm mt-2">Create one to get started</p>
                </div>
              ) : (
                sessions.map(session => (
                  <div
                    key={session.id}
                    className={`p-4 hover:bg-gray-50 transition-colors ${
                      selectedSession?.id === session.id ? 'bg-blue-50' : ''
                    }`}
                  >
                    <button
                      onClick={() => loadSessionDetails(session)}
                      className="w-full text-left"
                    >
                      <div className="font-medium">{session.id}</div>
                      <div className="text-sm text-gray-500">
                        Status: {session.status}
                      </div>
                      {session.job_id && (
                        <div className="text-sm text-gray-500">Job: {session.job_id}</div>
                      )}
                    </button>
                    <button
                      onClick={() => deleteSession(session.id)}
                      className="mt-2 text-red-600 hover:text-red-700 text-sm flex items-center gap-1"
                    >
                      <Trash2 className="w-3 h-3" />
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          {selectedSession ? (
            <div className="space-y-6">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-2xl font-bold mb-4">Session: {selectedSession.id}</h2>
                
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600 mb-1">Status</div>
                    <div className="text-lg font-semibold">{selectedSession.status}</div>
                  </div>
                  {selectedSession.job_id && (
                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="text-sm text-gray-600 mb-1">Job ID</div>
                      <div className="text-lg font-semibold">{selectedSession.job_id}</div>
                    </div>
                  )}
                </div>

                <div className="flex gap-3 mb-6">
                  <button
                    onClick={stepDebug}
                    className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600"
                  >
                    <SkipForward className="w-4 h-4" />
                    Step
                  </button>
                  <button
                    onClick={continueDebug}
                    className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
                  >
                    <Play className="w-4 h-4" />
                    Continue
                  </button>
                </div>

                {selectedSession.breakpoints && selectedSession.breakpoints.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold mb-3">Breakpoints</h3>
                    <div className="space-y-2">
                      {selectedSession.breakpoints.map((bp: any, idx: number) => (
                        <div key={idx} className="bg-gray-50 p-3 rounded-lg">
                          {JSON.stringify(bp)}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {selectedSession.trace && selectedSession.trace.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold mb-4">Execution Trace</h3>
                  <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm max-h-96 overflow-y-auto">
                    {selectedSession.trace.map((entry: any, idx: number) => (
                      <div key={idx} className="mb-2">
                        <span className="text-gray-500">[{idx}]</span>{' '}
                        <span className="text-gray-300">{JSON.stringify(entry)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow p-12">
              <div className="text-center text-gray-500">
                <Play className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg">Select a debug session to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DebugPage;
