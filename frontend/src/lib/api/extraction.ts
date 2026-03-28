/** API functions for extraction endpoints. */

import type {
  ExtractionResponse,
  ExtractionResultsResponse,
  UpdateFieldRequest,
  UpdateResultsResponse,
} from "../../types/extraction";
import apiClient from "./client";

/** Trigger field extraction for a document. */
export async function triggerExtract(
  id: string,
): Promise<ExtractionResponse> {
  const response = await apiClient.post(`/extract/${id}`);
  return response.data;
}

/** Get extraction results for a document. */
export async function getExtractionResults(
  id: string,
): Promise<ExtractionResultsResponse> {
  const response = await apiClient.get(`/extract/${id}/results`);
  return response.data;
}

/** Update extracted values (review/edit). */
export async function updateExtractionResults(
  id: string,
  updates: UpdateFieldRequest[],
): Promise<UpdateResultsResponse> {
  const response = await apiClient.put(`/extract/${id}/results`, { updates });
  return response.data;
}
