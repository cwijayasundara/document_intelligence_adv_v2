/** Expandable per-document status view for a bulk job. */

import type { BulkDocumentStatus, BulkJobDocument } from "../../types/bulk";

const STATUS_STYLES: Record<BulkDocumentStatus, { bg: string; text: string; label: string }> = {
  pending: { bg: "bg-gray-100", text: "text-gray-700", label: "Pending" },
  processing: { bg: "bg-blue-100", text: "text-blue-700", label: "Processing" },
  completed: { bg: "bg-green-100", text: "text-green-700", label: "Completed" },
  failed: { bg: "bg-red-100", text: "text-red-700", label: "Failed" },
};

interface BulkJobDetailProps {
  documents: BulkJobDocument[];
}

export default function BulkJobDetail({ documents }: BulkJobDetailProps) {
  return (
    <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
      <div className="overflow-hidden border border-gray-200 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr className="text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              <th className="px-4 py-2.5">File</th>
              <th className="px-4 py-2.5 w-28">Status</th>
              <th className="px-4 py-2.5 w-24">Time</th>
              <th className="px-4 py-2.5">Error</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {documents.map((doc) => {
              const style = STATUS_STYLES[doc.status] || STATUS_STYLES.pending;
              return (
                <tr key={doc.documentId} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-gray-900 truncate" title={doc.fileName}>
                        {doc.fileName}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
                      {doc.status === "processing" && (
                        <svg className="w-3 h-3 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                      )}
                      {style.label}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-500">
                    {doc.processingTimeMs != null
                      ? `${(doc.processingTimeMs / 1000).toFixed(1)}s`
                      : doc.status === "processing"
                        ? "..."
                        : "-"}
                  </td>
                  <td className="px-4 py-2.5">
                    {doc.errorMessage ? (
                      <span className="text-xs text-red-600" title={doc.errorMessage}>
                        {doc.errorMessage.length > 80
                          ? `${doc.errorMessage.slice(0, 80)}...`
                          : doc.errorMessage}
                      </span>
                    ) : (
                      <span className="text-gray-300">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
