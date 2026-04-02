/** TanStack Query hooks for document parsing operations. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getParseContent,
  saveParseContent,
  triggerParse,
} from "../lib/api/parse";
import type { ParseContentResponse } from "../types/parse";

const PARSE_KEY = ["parse"] as const;

/** Fetch parsed content for a document. */
export function useParseContent(id: string) {
  return useQuery<ParseContentResponse>({
    queryKey: [...PARSE_KEY, id, "content"],
    queryFn: () => getParseContent(id),
    enabled: !!id,
    retry: false,
  });
}

/** Trigger document parsing. */
export function useTriggerParse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, force = false }: { id: string; force?: boolean }) =>
      triggerParse(id, force),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: [...PARSE_KEY, id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

/** Save edited content. */
export function useSaveEdits() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      saveParseContent(id, content),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: [...PARSE_KEY, id] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
