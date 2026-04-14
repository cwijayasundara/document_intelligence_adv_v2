/** TanStack Query hooks for pipeline operations. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchPipelineStatus,
  startPipeline,
  resumePipeline,
  retryPipelineNode,
} from "../lib/api/pipeline";
import type { PipelineStatus } from "../types/pipeline";

const PIPELINE_KEY = ["pipeline"] as const;

/** Fetch pipeline status for a document. */
export function usePipelineStatus(docId: string) {
  const { data, isLoading, refetch } = useQuery<PipelineStatus>({
    queryKey: [...PIPELINE_KEY, docId, "status"],
    queryFn: () => fetchPipelineStatus(docId),
    enabled: !!docId,
    refetchInterval: (query) => {
      const status = query.state.data?.overallStatus;
      // Poll while pipeline is actively running
      return status === "running" ? 3000 : false;
    },
  });

  return { status: data ?? null, isLoading, refetch };
}

/** Start a full pipeline run for a document. */
export function useStartPipeline() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({
      docId,
      skipNodes,
    }: {
      docId: string;
      skipNodes?: string[];
    }) => startPipeline(docId, { skipNodes }),
    onSuccess: (_data, { docId }) => {
      queryClient.invalidateQueries({ queryKey: [...PIPELINE_KEY, docId] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return { startPipeline: mutation.mutate, isLoading: mutation.isPending };
}

/** Resume pipeline after a human review checkpoint. */
export function useResumePipeline() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({
      docId,
      nodeName,
      approved,
    }: {
      docId: string;
      nodeName: string;
      approved: boolean;
    }) => resumePipeline(docId, nodeName, approved),
    onSuccess: (_data, { docId }) => {
      queryClient.invalidateQueries({ queryKey: [...PIPELINE_KEY, docId] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return { resumePipeline: mutation.mutate, isLoading: mutation.isPending };
}

/** Retry a failed pipeline node. */
export function useRetryNode() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ docId, nodeName }: { docId: string; nodeName: string }) =>
      retryPipelineNode(docId, nodeName),
    onSuccess: (_data, { docId }) => {
      queryClient.invalidateQueries({ queryKey: [...PIPELINE_KEY, docId] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  return { retryNode: mutation.mutate, isLoading: mutation.isPending };
}
