/** TanStack Query hooks for extraction operations. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getExtractionResults,
  triggerExtract,
  updateExtractionResults,
} from "../lib/api/extraction";
import type {
  ExtractionResponse,
  ExtractionResultsResponse,
  UpdateFieldRequest,
  UpdateResultsResponse,
} from "../types/extraction";

const EXTRACT_KEY = ["extract"] as const;

/** Fetch extraction results for a document. */
export function useExtractionResults(id: string) {
  return useQuery<ExtractionResultsResponse>({
    queryKey: [...EXTRACT_KEY, id, "results"],
    queryFn: () => getExtractionResults(id),
    enabled: !!id,
    retry: false,
  });
}

/** Trigger field extraction. */
export function useTriggerExtract() {
  const queryClient = useQueryClient();
  return useMutation<ExtractionResponse, Error, string>({
    mutationFn: (id: string) => triggerExtract(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: [...EXTRACT_KEY, id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/** Update extraction results (review/edit). */
export function useUpdateExtractionResults() {
  const queryClient = useQueryClient();
  return useMutation<
    UpdateResultsResponse,
    Error,
    { id: string; updates: UpdateFieldRequest[] }
  >({
    mutationFn: ({ id, updates }) => updateExtractionResults(id, updates),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: [...EXTRACT_KEY, id] });
    },
  });
}
