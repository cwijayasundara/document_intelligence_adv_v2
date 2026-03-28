/** TypeScript types for categories and extraction fields. */

export interface Category {
  id: string;
  name: string;
  description: string | null;
  classificationCriteria: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CategoryListResponse {
  categories: Category[];
}

export interface CategoryCreateRequest {
  name: string;
  description?: string;
  classificationCriteria?: string;
}

export interface ExtractionField {
  id: string;
  fieldName: string;
  displayName: string;
  description: string | null;
  examples: string | null;
  dataType: string;
  required: boolean;
  sortOrder: number;
}

export interface FieldsListResponse {
  categoryId: string;
  categoryName: string;
  schemaVersion: number;
  fields: ExtractionField[];
}

export interface FieldCreateRequest {
  fieldName: string;
  displayName: string;
  description?: string;
  examples?: string;
  dataType: string;
  required: boolean;
  sortOrder: number;
}
