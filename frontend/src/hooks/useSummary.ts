/** TanStack Query hooks for summarization and ingestion. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generateSummary,
  getSummary,
  ingestDocument,
} from "../lib/api/summary";
import type { SummaryGetResponse } from "../types/summary";

const SUMMARY_KEY = ["summary"] as const;

/** Fetch existing summary for a document. */
export function useSummary(id: string) {
  return useQuery<SummaryGetResponse>({
    queryKey: [...SUMMARY_KEY, id],
    queryFn: () => getSummary(id),
    enabled: !!id,
    retry: false,
  });
}

/** Generate or regenerate a summary. */
export function useGenerateSummary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => generateSummary(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: [...SUMMARY_KEY, id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/** Ingest a document into Weaviate. */
export function useIngestDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => ingestDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
