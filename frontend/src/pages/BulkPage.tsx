/** Bulk processing page: upload, select files, then process. */

import { useCallback, useState } from "react";
import PageHeader from "../components/ui/PageHeader";
import BulkUploadZone from "../components/bulk/BulkUploadZone";
import BulkJobList from "../components/bulk/BulkJobList";
import { useBulkJobs, useUploadBulk } from "../hooks/useBulk";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function BulkPage() {
  const { data, isLoading } = useBulkJobs();
  const uploadMutation = useUploadBulk();
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);
  const [selectedIndexes, setSelectedIndexes] = useState<Set<number>>(new Set());

  const handleFilesAdded = useCallback((files: File[]) => {
    setStagedFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const newFiles = files.filter((f) => !existing.has(f.name));
      const all = [...prev, ...newFiles];
      // Auto-select all
      setSelectedIndexes(new Set(all.map((_, i) => i)));
      return all;
    });
  }, []);

  const toggleFile = (index: number) => {
    setSelectedIndexes((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIndexes.size === stagedFiles.length) {
      setSelectedIndexes(new Set());
    } else {
      setSelectedIndexes(new Set(stagedFiles.map((_, i) => i)));
    }
  };

  const removeFile = (index: number) => {
    setStagedFiles((prev) => prev.filter((_, i) => i !== index));
    setSelectedIndexes((prev) => {
      const next = new Set<number>();
      for (const i of prev) {
        if (i < index) next.add(i);
        else if (i > index) next.add(i - 1);
      }
      return next;
    });
  };

  const handleProcess = () => {
    const filesToUpload = stagedFiles.filter((_, i) => selectedIndexes.has(i));
    if (filesToUpload.length === 0) return;
    uploadMutation.mutate(filesToUpload, {
      onSuccess: () => {
        setStagedFiles([]);
        setSelectedIndexes(new Set());
      },
    });
  };

  const handleClear = () => {
    setStagedFiles([]);
    setSelectedIndexes(new Set());
  };

  return (
    <div>
      <PageHeader
        title="Bulk Processing"
        description="Upload multiple documents for batch processing through the full pipeline."
      />
      <div className="p-8 max-w-4xl mx-auto space-y-8">
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Upload Documents
          </h2>
          <BulkUploadZone
            onFilesAccepted={handleFilesAdded}
            disabled={uploadMutation.isPending}
          />

          {/* Staged file list */}
          {stagedFiles.length > 0 && (
            <div className="mt-4 border border-gray-200 rounded-lg bg-white overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={selectedIndexes.size === stagedFiles.length}
                    onChange={toggleAll}
                    className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    {selectedIndexes.size} of {stagedFiles.length} selected
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleClear}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    Clear all
                  </button>
                  <button
                    onClick={handleProcess}
                    disabled={selectedIndexes.size === 0 || uploadMutation.isPending}
                    className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {uploadMutation.isPending
                      ? "Processing..."
                      : `Process ${selectedIndexes.size} file${selectedIndexes.size !== 1 ? "s" : ""}`}
                  </button>
                </div>
              </div>
              <ul className="divide-y divide-gray-100">
                {stagedFiles.map((file, i) => (
                  <li key={file.name} className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={selectedIndexes.has(i)}
                      onChange={() => toggleFile(i)}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-gray-800 truncate block">
                        {file.name}
                      </span>
                    </div>
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      {formatFileSize(file.size)}
                    </span>
                    <button
                      onClick={() => removeFile(i)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                      title="Remove"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {uploadMutation.isError && (
            <p className="mt-3 text-sm text-red-600">
              Upload failed:{" "}
              {uploadMutation.error instanceof Error
                ? uploadMutation.error.message
                : "Unknown error"}
            </p>
          )}
          {uploadMutation.isSuccess && (
            <p className="mt-3 text-sm text-green-600">
              Bulk job created with {uploadMutation.data.totalDocuments} documents. Processing started.
            </p>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Bulk Jobs
          </h2>
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading jobs...</p>
          ) : (
            <BulkJobList jobs={data?.jobs ?? []} />
          )}
        </section>
      </div>
    </div>
  );
}
