/** TanStack Query hooks for document operations. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteDocument,
  fetchDocument,
  fetchDocuments,
  uploadDocument,
} from "../lib/api/documents";
import type { Document, DocumentListResponse } from "../types/document";

const DOCUMENTS_KEY = ["documents"] as const;

/** Fetch all documents. Refreshes automatically after mutations. */
export function useDocuments(params?: {
  status?: string;
  categoryId?: string;
  sortBy?: string;
  sortOrder?: string;
}) {
  return useQuery<DocumentListResponse>({
    queryKey: [...DOCUMENTS_KEY, params],
    queryFn: () => fetchDocuments(params),
  });
}

/** Fetch a single document by ID. */
export function useDocument(id: string) {
  return useQuery<Document>({
    queryKey: [...DOCUMENTS_KEY, id],
    queryFn: () => fetchDocument(id),
    enabled: !!id,
  });
}

/** Upload a document file. */
export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}

/** Delete a document. */
export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY });
    },
  });
}
