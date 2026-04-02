/** Types for document classification. */

export interface ClassifyResponse {
  documentId: string;
  categoryId: string;
  categoryName: string;
  confidence: number;
  reasoning: string;
  status: string;
}

export interface CategoryOption {
  id: string;
  name: string;
}
