/** Multi-file drag-drop upload zone for bulk processing. */

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

const ACCEPTED_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
    ".docx",
  ],
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
    ".xlsx",
  ],
  "image/png": [".png"],
  "image/jpeg": [".jpg"],
  "image/tiff": [".tiff"],
};

interface BulkUploadZoneProps {
  onFilesAccepted: (files: File[]) => void;
  disabled?: boolean;
}

export default function BulkUploadZone({
  onFilesAccepted,
  disabled = false,
}: BulkUploadZoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        onFilesAccepted(acceptedFiles);
      }
    },
    [onFilesAccepted],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    disabled,
    multiple: true,
  });

  return (
    <div
      {...getRootProps()}
      data-testid="bulk-upload-dropzone"
      className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
        isDragActive
          ? "border-primary-500 bg-primary-50"
          : "border-gray-300 hover:border-gray-400"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} data-testid="bulk-upload-input" />
      <div className="space-y-2">
        <p className="text-lg font-medium text-gray-700">
          {isDragActive
            ? "Drop your files here..."
            : "Drag and drop multiple documents, or click to browse"}
        </p>
        <p className="text-sm text-gray-500">
          Supports PDF, DOCX, XLSX, PNG, JPG, TIFF
        </p>
      </div>
    </div>
  );
}
