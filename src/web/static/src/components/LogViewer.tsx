import { useEffect, useRef, useState } from 'react';
import { useWorkflowStore } from '@/store/workflowStore';
import { LogEntry } from '@/types';

function LogViewer() {
  const { logs, clearLogs } = useWorkflowStore();
  const [filter, setFilter] = useState<string>('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter((log) => {
    if (filter === 'all') return true;
    return log.level === filter;
  });

  useEffect(() => {
    if (autoScroll) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return 'text-red-600 bg-red-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      case 'info':
        return 'text-blue-600 bg-blue-50';
      case 'debug':
        return 'text-gray-600 bg-gray-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      case 'info':
        return 'ℹ️';
      case 'debug':
        return '🐛';
      default:
        return '📝';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-gray-900">Logs</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-2 py-1 text-xs font-medium rounded ${
                filter === 'all'
                  ? 'bg-primary-100 text-primary-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All ({logs.length})
            </button>
            <button
              onClick={() => setFilter('error')}
              className={`px-2 py-1 text-xs font-medium rounded ${
                filter === 'error'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Errors ({logs.filter((l) => l.level === 'error').length})
            </button>
            <button
              onClick={() => setFilter('warning')}
              className={`px-2 py-1 text-xs font-medium rounded ${
                filter === 'warning'
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Warnings ({logs.filter((l) => l.level === 'warning').length})
            </button>
            <button
              onClick={() => setFilter('info')}
              className={`px-2 py-1 text-xs font-medium rounded ${
                filter === 'info'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Info ({logs.filter((l) => l.level === 'info').length})
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1 text-xs text-gray-600">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            Auto-scroll
          </label>
          <button
            onClick={clearLogs}
            className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Log Entries */}
      <div className="flex-1 overflow-y-auto bg-gray-900 p-2 font-mono text-xs">
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            No logs to display
          </div>
        ) : (
          <div className="space-y-1">
            {filteredLogs.map((log, index) => (
              <div
                key={index}
                className={`p-2 rounded ${getLevelColor(log.level)} border border-gray-700`}
              >
                <div className="flex items-start gap-2">
                  <span className="flex-shrink-0">{getLevelIcon(log.level)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-gray-500">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                      {log.agent && (
                        <span className="px-1.5 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">
                          {log.agent}
                        </span>
                      )}
                      <span className={`px-1.5 py-0.5 rounded text-xs uppercase font-semibold ${getLevelColor(log.level)}`}>
                        {log.level}
                      </span>
                    </div>
                    <div className="text-gray-200 break-words">{log.message}</div>
                  </div>
                </div>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}
      </div>
    </div>
  );
}

export default LogViewer;
