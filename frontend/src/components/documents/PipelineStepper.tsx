/** Horizontal stepper showing pipeline node progress. */

import {
  PIPELINE_NODES,
  NODE_LABELS,
  type NodeStatus,
  type PipelineNodeName,
} from "../../types/pipeline";

interface PipelineStepperProps {
  nodeStatuses: Record<string, NodeStatus> | null;
  onRetry?: (nodeName: string) => void;
  onReview?: (nodeName: string) => void;
  compact?: boolean;
}

const defaultNodeStatus: NodeStatus = {
  status: "not_started",
  startedAt: null,
  completedAt: null,
  error: null,
};

function CheckIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
      <path
        fillRule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function SkipIcon() {
  return (
    <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798L4.555 5.168z" />
    </svg>
  );
}

function getStepStyles(status: NodeStatus["status"]) {
  switch (status) {
    case "completed":
      return {
        circle: "bg-green-500 text-white",
        connector: "bg-green-500",
        dot: "bg-green-500",
      };
    case "running":
      return {
        circle: "bg-blue-500 text-white animate-pulse",
        connector: "bg-blue-500",
        dot: "bg-blue-500 animate-pulse",
      };
    case "failed":
      return {
        circle: "bg-red-500 text-white",
        connector: "bg-red-300",
        dot: "bg-red-500",
      };
    case "awaiting_review":
      return {
        circle: "bg-amber-400 text-white",
        connector: "bg-amber-400",
        dot: "bg-amber-400",
      };
    case "skipped":
      return {
        circle: "bg-gray-300 text-gray-500",
        connector: "bg-gray-300",
        dot: "bg-gray-300",
      };
    default:
      return {
        circle: "bg-gray-200 text-gray-400",
        connector: "bg-gray-200",
        dot: "bg-gray-200",
      };
  }
}

function StepIcon({ status }: { status: NodeStatus["status"] }) {
  switch (status) {
    case "completed":
      return <CheckIcon />;
    case "running":
      return (
        <span className="block w-2 h-2 bg-white rounded-full animate-spin" />
      );
    case "failed":
      return <XIcon />;
    case "awaiting_review":
      return <PauseIcon />;
    case "skipped":
      return <SkipIcon />;
    default:
      return <span className="block w-2 h-2 bg-gray-400 rounded-full" />;
  }
}

export default function PipelineStepper({
  nodeStatuses,
  onRetry,
  onReview,
  compact = false,
}: PipelineStepperProps) {
  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {PIPELINE_NODES.map((node) => {
          const ns = nodeStatuses?.[node] ?? defaultNodeStatus;
          const styles = getStepStyles(ns.status);
          return (
            <span
              key={node}
              className={`block w-2.5 h-2.5 rounded-full ${styles.dot}`}
              title={`${NODE_LABELS[node]}: ${ns.status}`}
            />
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex items-start w-full" data-testid="pipeline-stepper">
      {PIPELINE_NODES.map((node, idx) => {
        const ns = nodeStatuses?.[node] ?? defaultNodeStatus;
        const styles = getStepStyles(ns.status);
        const isLast = idx === PIPELINE_NODES.length - 1;

        return (
          <div key={node} className="flex items-start flex-1 min-w-0">
            {/* Step circle + label + action */}
            <div className="flex flex-col items-center">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full ${styles.circle}`}
              >
                <StepIcon status={ns.status} />
              </div>
              <span className="mt-1 text-xs font-medium text-gray-700 truncate">
                {NODE_LABELS[node as PipelineNodeName]}
              </span>
              {ns.status === "failed" && onRetry && (
                <button
                  onClick={() => onRetry(node)}
                  className="mt-1 text-xs text-red-600 hover:text-red-800 font-medium"
                  type="button"
                >
                  Retry
                </button>
              )}
              {ns.status === "awaiting_review" && onReview && (
                <button
                  onClick={() => onReview(node)}
                  className="mt-1 text-xs text-amber-600 hover:text-amber-800 font-medium"
                  type="button"
                >
                  Review
                </button>
              )}
            </div>
            {/* Connector line */}
            {!isLast && (
              <div className="flex-1 flex items-center pt-4 px-1">
                <div className={`h-0.5 w-full ${styles.connector}`} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
