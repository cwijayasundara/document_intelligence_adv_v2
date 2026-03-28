/** Hook for file upload with progress tracking. */

import { useState } from "react";
import { useUploadDocument } from "./useDocuments";

interface UploadState {
  fileName: string;
  progress: number;
  status: "pending" | "uploading" | "success" | "error";
  errorMessage?: string;
  documentId?: string;
}

export function useUpload() {
  const [uploadState, setUploadState] = useState<UploadState | null>(null);
  const mutation = useUploadDocument();

  const upload = async (file: File) => {
    setUploadState({
      fileName: file.name,
      progress: 0,
      status: "uploading",
    });

    try {
      setUploadState((prev) =>
        prev ? { ...prev, progress: 50, status: "uploading" } : null,
      );

      const result = await mutation.mutateAsync(file);

      setUploadState({
        fileName: file.name,
        progress: 100,
        status: "success",
        documentId: result.id,
      });

      return result;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Upload failed";
      setUploadState({
        fileName: file.name,
        progress: 0,
        status: "error",
        errorMessage: message,
      });
      return null;
    }
  };

  const reset = () => {
    setUploadState(null);
  };

  return {
    upload,
    reset,
    uploadState,
    isUploading: uploadState?.status === "uploading",
  };
}
