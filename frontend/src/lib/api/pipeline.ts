/** API functions for pipeline endpoints. */

import type { PipelineStatus } from "../../types/pipeline";
import apiClient from "./client";

export async function fetchPipelineStatus(docId: string): Promise<PipelineStatus> {
  const response = await apiClient.get(`/pipeline/${docId}/status`);
  return response.data;
}

export async function startPipeline(
  docId: string,
  options?: { skipNodes?: string[] },
): Promise<PipelineStatus> {
  const response = await apiClient.post(`/pipeline/${docId}/start`, options ?? {});
  return response.data;
}

export async function resumePipeline(
  docId: string,
  nodeName: string,
  approved: boolean,
): Promise<PipelineStatus> {
  const response = await apiClient.post(`/pipeline/${docId}/resume`, {
    nodeName,
    approved,
  });
  return response.data;
}

export async function retryPipelineNode(
  docId: string,
  nodeName: string,
): Promise<PipelineStatus> {
  const response = await apiClient.post(`/pipeline/${docId}/retry/${nodeName}`);
  return response.data;
}
