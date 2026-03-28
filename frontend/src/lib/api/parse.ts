/** API functions for parse endpoints. */

import type {
  ParseContentResponse,
  ParseTriggerResponse,
  SaveEditsResponse,
} from "../../types/parse";
import apiClient from "./client";

/** Trigger document parsing. */
export async function triggerParse(id: string): Promise<ParseTriggerResponse> {
  const response = await apiClient.post(`/parse/${id}`);
  return response.data;
}

/** Get parsed markdown content. */
export async function getParseContent(
  id: string,
): Promise<ParseContentResponse> {
  const response = await apiClient.get(`/parse/${id}/content`);
  return response.data;
}

/** Save edited content. */
export async function saveParseContent(
  id: string,
  content: string,
): Promise<SaveEditsResponse> {
  const response = await apiClient.put(`/parse/${id}/content`, { content });
  return response.data;
}
