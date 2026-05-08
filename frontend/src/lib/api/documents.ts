/** API functions for document endpoints. */

import type { Document, DocumentListResponse } from "../../types/document";
import { API_BASE_URL } from "../config";
import apiClient from "./client";

/** Absolute URL for streaming the original uploaded file. */
export function documentFileUrl(id: string): string {
  return `${API_BASE_URL}/documents/${id}/file`;
}

export async function fetchDocuments(params?: {
  status?: string;
  categoryId?: string;
  sortBy?: string;
  sortOrder?: string;
}): Promise<DocumentListResponse> {
  const response = await apiClient.get("/documents", { params });
  return response.data;
}

export async function fetchDocument(id: string): Promise<Document> {
  const response = await apiClient.get(`/documents/${id}`);
  return response.data;
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/documents/${id}`);
}
