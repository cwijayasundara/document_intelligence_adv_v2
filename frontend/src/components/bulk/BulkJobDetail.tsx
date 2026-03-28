/** Expandable per-document status view for a bulk job. */

import type { BulkJobDocument } from "../../types/bulk";
import DocumentStatusDot from "./DocumentStatusDot";

interface BulkJobDetailProps {
  documents: BulkJobDocument[];
}

export default function BulkJobDetail({ documents }: BulkJobDetailProps) {
  return (
    <div
      className="border-t border-gray-200 bg-gray-50 px-6 py-4"
      data-testid="bulk-job-detail"
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500">
            <th className="pb-2 font-medium">File</th>
            <th className="pb-2 font-medium">Status</th>
            <th className="pb-2 font-medium">Time</th>
            <th className="pb-2 font-medium">Error</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {documents.map((doc) => (
            <tr key={doc.documentId} data-testid="bulk-document-row">
              <td className="py-2 text-gray-900">{doc.fileName}</td>
              <td className="py-2">
                <DocumentStatusDot status={doc.status} />
              </td>
              <td className="py-2 text-gray-600">
                {doc.processingTimeMs != null
                  ? `${(doc.processingTimeMs / 1000).toFixed(1)}s`
                  : "-"}
              </td>
              <td className="py-2">
                {doc.errorMessage ? (
                  <span className="text-red-600 font-medium">
                    {doc.errorMessage}
                  </span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
