/** API functions for summarize and ingest endpoints. */

import type {
  IngestResponse,
  SummarizeResponse,
  SummaryGetResponse,
} from "../../types/summary";
import apiClient from "./client";

/** Generate or regenerate a document summary. */
export async function generateSummary(
  id: string,
): Promise<SummarizeResponse> {
  const response = await apiClient.post(`/summarize/${id}`);
  return response.data;
}

/** Get existing summary for a document. */
export async function getSummary(id: string): Promise<SummaryGetResponse> {
  const response = await apiClient.get(`/summarize/${id}`);
  return response.data;
}

/** Ingest a document into Weaviate for RAG. */
export async function ingestDocument(id: string): Promise<IngestResponse> {
  const response = await apiClient.post(`/ingest/${id}`);
  return response.data;
}
