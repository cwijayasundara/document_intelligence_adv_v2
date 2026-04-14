/** Shared TypeScript types for the application. */

export interface ErrorResponse {
  detail: string;
  errorCode?: string;
  context?: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export type DocumentStatus =
  | "uploaded"
  | "parsed"
  | "edited"
  | "classified"
  | "extracted"
  | "summarized"
  | "ingested"
  | "processing"
  | "awaiting_parse_review"
  | "awaiting_extraction_review";
