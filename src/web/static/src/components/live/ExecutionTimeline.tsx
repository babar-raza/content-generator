import React from 'react';
import { Clock, CheckCircle, AlertCircle, Circle } from 'lucide-react';

export interface TimelineStep {
  agentId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime?: string;
  endTime?: string;
  duration?: number;
}

interface ExecutionTimelineProps {
  steps: TimelineStep[];
  currentAgent?: string;
}

export const ExecutionTimeline: React.FC<ExecutionTimelineProps> = ({
  steps,
  currentAgent
}) => {
  const getStepIcon = (step: TimelineStep) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'running':
        return <Clock className="w-4 h-4 text-blue-500 animate-pulse" />;
      default:
        return <Circle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStepColor = (step: TimelineStep) => {
    switch (step.status) {
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'running':
        return 'bg-blue-500';
      default:
        return 'bg-gray-300';
    }
  };

  const formatTime = (duration?: number) => {
    if (!duration) return '';
    return `${duration.toFixed(2)}s`;
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-5 h-5 text-gray-600" />
        <h3 className="text-lg font-semibold">Execution Timeline</h3>
      </div>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={index} className="flex items-start gap-3">
            {/* Icon */}
            <div className="flex-shrink-0 mt-1">
              {getStepIcon(step)}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className={`text-sm font-medium ${
                  step.agentId === currentAgent ? 'text-blue-600' : 'text-gray-900'
                }`}>
                  {step.agentId}
                </span>
                {step.duration !== undefined && (
                  <span className="text-xs text-gray-500">
                    {formatTime(step.duration)}
                  </span>
                )}
              </div>

              {/* Status text */}
              <div className="text-xs text-gray-600 mt-1">
                {step.status === 'running' && 'In progress...'}
                {step.status === 'completed' && 'Completed'}
                {step.status === 'failed' && 'Failed'}
                {step.status === 'pending' && 'Waiting...'}
              </div>

              {/* Progress bar */}
              {index < steps.length - 1 && (
                <div className="mt-2 ml-2 w-0.5 h-4 bg-gray-200">
                  <div
                    className={`w-full transition-all duration-300 ${
                      step.status === 'completed' || step.status === 'failed'
                        ? 'h-full'
                        : 'h-0'
                    } ${getStepColor(step)}`}
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {steps.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p className="text-sm">No execution steps yet</p>
        </div>
      )}
    </div>
  );
};
