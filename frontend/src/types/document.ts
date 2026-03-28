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
  fileType: string;
  fileSize: number;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
  total: number;
}

/** Map a document status to its next action route. */
export function getNextActionRoute(
  docId: string,
  status: DocumentStatus,
): string {
  const routes: Record<DocumentStatus, string> = {
    uploaded: `/documents/${docId}/parse`,
    parsed: `/documents/${docId}/classify`,
    edited: `/documents/${docId}/classify`,
    classified: `/documents/${docId}/extract`,
    extracted: `/documents/${docId}/summary`,
    summarized: `/documents/${docId}/summary`,
    ingested: `/documents/${docId}/chat`,
  };
  return routes[status] || `/documents/${docId}/parse`;
}
