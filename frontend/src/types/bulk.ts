/** Bulk processing TypeScript types. */

export type BulkJobStatus = "pending" | "processing" | "completed" | "failed";

export type BulkDocumentStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface BulkJobDocument {
  documentId: string;
  fileName: string;
  status: BulkDocumentStatus;
  errorMessage: string | null;
  processingTimeMs: number | null;
}

export interface BulkJob {
  id: string;
  status: BulkJobStatus;
  totalDocuments: number;
  processedCount: number;
  failedCount: number;
  createdAt: string;
  completedAt: string | null;
}

export interface BulkJobDetail extends BulkJob {
  documents: BulkJobDocument[];
}

export interface BulkJobListResponse {
  jobs: BulkJob[];
}

export interface BulkUploadResponse {
  jobId: string;
  status: BulkJobStatus;
  totalDocuments: number;
  documents: Array<{
    documentId: string;
    fileName: string;
    status: BulkDocumentStatus;
  }>;
  createdAt: string;
}
