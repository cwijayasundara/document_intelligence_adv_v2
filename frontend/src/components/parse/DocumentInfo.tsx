/** Left panel showing document metadata on the parse page. */

import type { Document } from "../../types/document";
import DocumentStatusBadge from "../documents/DocumentStatusBadge";

interface DocumentInfoProps {
  document: Document | undefined;
  isLoading: boolean;
}

export default function DocumentInfo({ document, isLoading }: DocumentInfoProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4 p-6">
        <div className="h-6 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
        <div className="h-4 bg-gray-200 rounded w-2/3" />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="p-6 text-gray-500">Document not found.</div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Document Info</h2>

      <div className="space-y-3">
        <InfoRow label="File Name" value={document.fileName} />
        <InfoRow label="File Type" value={document.fileType.toUpperCase()} />
        <InfoRow
          label="File Size"
          value={formatFileSize(document.fileSize)}
        />
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Status</span>
          <DocumentStatusBadge status={document.status} />
        </div>
        <InfoRow
          label="Created"
          value={new Date(document.createdAt).toLocaleDateString()}
        />
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value}</span>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
