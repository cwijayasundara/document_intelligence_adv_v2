/** TanStack Query hooks for RAG chat operations. */

import { useMutation } from "@tanstack/react-query";
import { submitRagQuery } from "../lib/api/rag";
import type { RagQueryRequest, RagQueryResponse } from "../types/rag";

/** Submit a RAG query. */
export function useRagQuery() {
  return useMutation<RagQueryResponse, Error, RagQueryRequest>({
    mutationFn: (request) => submitRagQuery(request),
  });
}
