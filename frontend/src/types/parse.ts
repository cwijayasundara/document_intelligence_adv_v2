/** Types for document parsing and editing. */

export interface ParseContentResponse {
  documentId: string;
  content: string;
  status: string;
  confidencePct: number;
}

export interface ParseTriggerResponse {
  documentId: string;
  status: string;
  content: string;
  confidencePct: number;
  skipped: boolean;
  message?: string;
}

export interface SaveEditsResponse {
  documentId: string;
  status: string;
  contentLength: number;
}
