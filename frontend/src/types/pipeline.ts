/** Types for the unified pipeline workflow. */

export type PipelineNodeName = "parse" | "summarize" | "classify" | "extract" | "ingest";

export type NodeStatusValue = "not_started" | "running" | "completed" | "failed" | "awaiting_review" | "skipped";

export interface NodeStatus {
  status: NodeStatusValue;
  startedAt: string | null;
  completedAt: string | null;
  error: string | null;
}

export interface PipelineStatus {
  documentId: string;
  overallStatus: string;
  nodeStatuses: Record<PipelineNodeName, NodeStatus>;
  nodeTimings: Record<string, number>;
  nextNodes: string[];
}

export const PIPELINE_NODES: PipelineNodeName[] = ["parse", "summarize", "classify", "extract", "ingest"];

export const NODE_LABELS: Record<PipelineNodeName, string> = {
  parse: "Parse",
  summarize: "Summarize",
  classify: "Classify",
  extract: "Extract",
  ingest: "Ingest",
};
