/** Upload progress indicator per file. */

import FileTypeIcon from "./FileTypeIcon";

interface UploadProgressProps {
  fileName: string;
  progress: number;
  status: "pending" | "uploading" | "success" | "error";
  errorMessage?: string;
}

export default function UploadProgress({
  fileName,
  progress,
  status,
  errorMessage,
}: UploadProgressProps) {
  return (
    <div className="flex items-center gap-3 p-3 border rounded-lg" data-testid="upload-progress">
      <FileTypeIcon fileName={fileName} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {fileName}
        </p>
        {status === "uploading" && (
          <div className="mt-1 w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-primary-600 h-1.5 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
        {status === "success" && (
          <p className="text-xs text-green-600 mt-1">Upload complete</p>
        )}
        {status === "error" && (
          <p className="text-xs text-red-600 mt-1">
            {errorMessage ?? "Upload failed"}
          </p>
        )}
      </div>
      {status === "uploading" && (
        <span className="text-xs text-gray-500">{progress}%</span>
      )}
    </div>
  );
}
