/** Types for the evaluation framework API. Mirrors backend/src/api/routers/evals.py. */

export interface EvalRunItem {
  id: string;
  stage: string;
  datasetName: string;
  datasetVersion?: string | null;
  model: string;
  judgeModel?: string | null;
  gitSha?: string | null;
  totalExamples: number;
  durationSeconds?: number | null;
  status: "running" | "completed" | "failed";
  summaryScores: Record<string, number>;
  langsmithExperimentUrl?: string | null;
  tags: string[];
  createdAt: string;
}

export interface EvalResultItem {
  exampleId: string;
  evaluatorKey: string;
  score: number | null;
  passed?: boolean | null;
  comment?: string | null;
  prediction?: Record<string, unknown> | null;
  expected?: Record<string, unknown> | null;
  criteriaBreakdown?: Record<string, unknown> | null;
}

export interface EvalRunDetail {
  run: EvalRunItem;
  results: EvalResultItem[];
}

export interface OverviewItem {
  stage: string;
  run?: EvalRunItem | null;
  primaryScore?: number | null;
  primaryMetricKey?: string | null;
  deltaVsPrevious?: number | null;
}

export interface TrendPoint {
  runId: string;
  createdAt: string;
  score: number | null;
}

export interface TrendResponse {
  stage: string;
  evaluatorKey: string;
  points: TrendPoint[];
}

export interface TriggerRunRequest {
  stage: string;
  subset?: number | null;
  tags?: string[];
  model?: string | null;
}

export const EVAL_STAGES = [
  "classification",
  "extraction",
  "summary",
  "rag",
  "sql",
  "agentic_rag",
  "pipeline",
] as const;

export type EvalStage = (typeof EVAL_STAGES)[number];
