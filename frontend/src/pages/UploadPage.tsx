/** Upload page with drag-drop zone and progress indicator. */

import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import UploadDropzone from "../components/upload/UploadDropzone";
import UploadProgress from "../components/upload/UploadProgress";
import PageHeader from "../components/ui/PageHeader";
import { useUpload } from "../hooks/useUpload";

export default function UploadPage() {
  const navigate = useNavigate();
  const { upload, uploadState, isUploading } = useUpload();

  const handleFilesAccepted = useCallback(
    async (files: File[]) => {
      const file = files[0];
      if (!file) return;

      const result = await upload(file);
      if (result) {
        // Navigate to parse page after short delay for UX
        setTimeout(() => {
          navigate(`/documents/${result.id}/parse`);
        }, 1000);
      }
    },
    [upload, navigate],
  );

  return (
    <div>
      <PageHeader
        title="Upload Document"
        description="Upload a document to begin the analysis pipeline."
      />
      <div className="p-8 max-w-2xl mx-auto">
        <UploadDropzone
          onFilesAccepted={handleFilesAccepted}
          disabled={isUploading}
        />
        {uploadState && (
          <div className="mt-6">
            <UploadProgress
              fileName={uploadState.fileName}
              progress={uploadState.progress}
              status={uploadState.status}
              errorMessage={uploadState.errorMessage}
            />
          </div>
        )}
      </div>
    </div>
  );
}
