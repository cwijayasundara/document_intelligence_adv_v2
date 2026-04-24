/** TanStack Query hooks for the eval dashboard. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchOverview,
  fetchRun,
  fetchRuns,
  fetchTrend,
  triggerRun,
} from "../lib/api/evals";
import type { TriggerRunRequest } from "../types/evals";

const OVERVIEW_KEY = ["evals", "overview"] as const;
const RUNS_KEY = ["evals", "runs"] as const;
const RUN_KEY = ["evals", "run"] as const;
const TREND_KEY = ["evals", "trend"] as const;

export function useEvalOverview() {
  return useQuery({
    queryKey: OVERVIEW_KEY,
    queryFn: fetchOverview,
    refetchInterval: 15_000,
  });
}

export function useEvalRuns(stage?: string, limit = 50) {
  return useQuery({
    queryKey: [...RUNS_KEY, stage ?? "all", limit] as const,
    queryFn: () => fetchRuns({ stage, limit }),
    refetchInterval: 15_000,
  });
}

export function useEvalRun(runId: string | undefined) {
  return useQuery({
    queryKey: [...RUN_KEY, runId ?? ""] as const,
    queryFn: () => fetchRun(runId as string),
    enabled: Boolean(runId),
  });
}

export function useEvalTrend(stage: string | undefined, evaluatorKey: string | undefined) {
  return useQuery({
    queryKey: [...TREND_KEY, stage ?? "", evaluatorKey ?? ""] as const,
    queryFn: () =>
      fetchTrend({
        stage: stage as string,
        evaluatorKey: evaluatorKey as string,
        limit: 50,
      }),
    enabled: Boolean(stage && evaluatorKey),
  });
}

export function useTriggerEvalRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TriggerRunRequest) => triggerRun(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: OVERVIEW_KEY });
      qc.invalidateQueries({ queryKey: RUNS_KEY });
    },
  });
}
