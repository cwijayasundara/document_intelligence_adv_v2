/** Types for extraction results and review. */

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ExtractionResult {
  id: string;
  fieldName: string;
  displayName: string;
  extractedValue: string;
  sourceText: string;
  confidence: ConfidenceLevel;
  confidenceReasoning: string;
  requiresReview: boolean;
  reviewed: boolean;
}

export interface ExtractionResponse {
  documentId: string;
  status: string;
  results: ExtractionResult[];
  requiresReviewCount: number;
}

export interface ExtractionResultsResponse {
  documentId: string;
  results: ExtractionResult[];
  requiresReviewCount: number;
  allReviewed: boolean;
}

export interface UpdateFieldRequest {
  fieldId: string;
  extractedValue: string;
  reviewed: boolean;
}

export interface UpdateResultsResponse {
  documentId: string;
  updatedCount: number;
  requiresReviewCount: number;
  allReviewed: boolean;
  canProceed: boolean;
}
