/** API functions for classification endpoints. */

import type { ClassifyResponse } from "../../types/classify";
import apiClient from "./client";

/** Trigger document classification. */
export async function triggerClassify(id: string): Promise<ClassifyResponse> {
  const response = await apiClient.post(`/classify/${id}`);
  return response.data;
}

/** Override document category. */
export async function overrideCategory(
  documentId: string,
  categoryId: string,
): Promise<void> {
  await apiClient.put(`/documents/${documentId}`, {
    documentCategoryId: categoryId,
  });
}
