/** Document-related TypeScript types. */

import type { DocumentStatus } from "./common";

export interface Document {
  id: string;
  fileName: string;
  originalPath: string;
  parsedPath: string | null;
  fileHash: string;
  status: DocumentStatus;
  documentCategoryId: string | null;
  fileType: string;
  fileSize: number;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentListItem {
  id: string;
  fileName: string;
  status: DocumentStatus;
  documentCategoryId: string | null;
  categoryName: string | null;
  fileType: string;
  fileSize: number;
  parseConfidencePct: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
}

/** Map a document status to its next action route.
 *
 * Workflow order: Parse → Summarize → Classify → Extract → Ingest → Chat.
 */
export function getNextActionRoute(
  docId: string,
  status: DocumentStatus,
): string {
  const routes: Record<DocumentStatus, string> = {
    uploaded: `/documents/${docId}/parse`,
    processing: `/documents/${docId}/parse`,
    parsed: `/documents/${docId}/summary`,
    edited: `/documents/${docId}/summary`,
    awaiting_parse_review: `/documents/${docId}/parse`,
    summarized: `/documents/${docId}/classify`,
    classified: `/documents/${docId}/extract`,
    extracted: `/documents/${docId}/extract`,
    awaiting_extraction_review: `/documents/${docId}/extract`,
    ingested: `/documents/${docId}/chat`,
  };
  return routes[status] || `/documents/${docId}/parse`;
}
