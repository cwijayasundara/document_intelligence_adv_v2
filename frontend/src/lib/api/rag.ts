/** API functions for RAG query endpoints. */

import type { RagQueryRequest, RagQueryResponse } from "../../types/rag";
import apiClient from "./client";

/** Submit a RAG query. */
export async function submitRagQuery(
  request: RagQueryRequest,
): Promise<RagQueryResponse> {
  const response = await apiClient.post("/rag/query", request);
  return response.data;
}
