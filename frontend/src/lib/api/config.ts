/** API functions for config (categories and extraction fields). */

import type {
  Category,
  CategoryCreateRequest,
  CategoryListResponse,
  FieldCreateRequest,
  FieldsListResponse,
} from "../../types/config";
import apiClient from "./client";

export async function fetchCategories(): Promise<CategoryListResponse> {
  const response = await apiClient.get("/config/categories");
  return response.data;
}

export async function createCategory(
  data: CategoryCreateRequest,
): Promise<Category> {
  const response = await apiClient.post("/config/categories", data);
  return response.data;
}

export async function updateCategory(
  id: string,
  data: Partial<CategoryCreateRequest>,
): Promise<Category> {
  const response = await apiClient.put(`/config/categories/${id}`, data);
  return response.data;
}

export async function deleteCategory(id: string): Promise<void> {
  await apiClient.delete(`/config/categories/${id}`);
}

export async function fetchFields(
  categoryId: string,
): Promise<FieldsListResponse> {
  const response = await apiClient.get(
    `/config/categories/${categoryId}/fields`,
  );
  return response.data;
}

export async function createFields(
  categoryId: string,
  fields: FieldCreateRequest[],
): Promise<void> {
  await apiClient.post(`/config/categories/${categoryId}/fields`, { fields });
}
