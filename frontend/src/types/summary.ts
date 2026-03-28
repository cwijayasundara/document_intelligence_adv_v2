/** Types for document summarization. */

export interface SummarizeResponse {
  documentId: string;
  summary: string;
  keyTopics: string[];
  status: string;
  cached: boolean;
}

export interface SummaryGetResponse {
  documentId: string;
  summary: string;
  keyTopics: string[];
  contentHash: string;
  createdAt?: string;
}

export interface IngestResponse {
  documentId: string;
  status: string;
  chunksCreated: number;
  collection: string;
}
