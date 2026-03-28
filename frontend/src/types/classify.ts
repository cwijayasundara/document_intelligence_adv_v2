/** Types for document classification. */

export interface ClassifyResponse {
  documentId: string;
  categoryId: string;
  categoryName: string;
  reasoning: string;
  status: string;
}

export interface CategoryOption {
  id: string;
  name: string;
}
