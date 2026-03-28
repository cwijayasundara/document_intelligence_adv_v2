/** API functions for bulk processing endpoints. */

import type {
  BulkJobDetail,
  BulkJobListResponse,
  BulkUploadResponse,
} from "../../types/bulk";
import apiClient from "./client";

export async function uploadBulkFiles(
  files: File[],
): Promise<BulkUploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const response = await apiClient.post("/bulk/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function listBulkJobs(
  status?: string,
): Promise<BulkJobListResponse> {
  const response = await apiClient.get("/bulk/jobs", {
    params: status ? { status } : undefined,
  });
  return response.data;
}

export async function getBulkJobDetail(id: string): Promise<BulkJobDetail> {
  const response = await apiClient.get(`/bulk/jobs/${id}`);
  return response.data;
}
