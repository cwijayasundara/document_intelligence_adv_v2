/** Types for extraction results and review. */

export type ConfidenceLevel = "high" | "medium" | "low";

/**
 * Bounding-box pointer back into the source document.
 * left/top/width/height are page-normalized (0-1) for PDFs and images.
 */
export interface ExtractionCitation {
  page: number;
  left: number;
  top: number;
  width: number;
  height: number;
  content: string | null;
  confidence: ConfidenceLevel;
}

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
  citations: ExtractionCitation[];
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
