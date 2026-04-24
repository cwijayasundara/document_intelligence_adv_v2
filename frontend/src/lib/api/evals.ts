/** Evaluation framework API client. */

import apiClient from "./client";
import type {
  EvalRunDetail,
  EvalRunItem,
  OverviewItem,
  TrendResponse,
  TriggerRunRequest,
} from "../../types/evals";

export async function fetchOverview(): Promise<OverviewItem[]> {
  const { data } = await apiClient.get<OverviewItem[]>("/evals/overview");
  return data;
}

export async function fetchRuns(params: {
  stage?: string;
  limit?: number;
  offset?: number;
}): Promise<EvalRunItem[]> {
  const { data } = await apiClient.get<EvalRunItem[]>("/evals/runs", { params });
  return data;
}

export async function fetchRun(runId: string): Promise<EvalRunDetail> {
  const { data } = await apiClient.get<EvalRunDetail>(`/evals/runs/${runId}`);
  return data;
}

export async function triggerRun(body: TriggerRunRequest): Promise<{ status: string }> {
  const { data } = await apiClient.post("/evals/runs", body);
  return data;
}

export async function fetchTrend(params: {
  stage: string;
  evaluatorKey: string;
  limit?: number;
}): Promise<TrendResponse> {
  const { data } = await apiClient.get<TrendResponse>("/evals/trends", { params });
  return data;
}
