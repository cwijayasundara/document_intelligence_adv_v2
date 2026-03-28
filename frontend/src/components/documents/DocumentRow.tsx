/** A single row in the document table. */

import { Link } from "react-router-dom";
import type { DocumentListItem } from "../../types/document";
import { getNextActionRoute } from "../../types/document";
import DocumentStatusBadge from "./DocumentStatusBadge";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface DocumentRowProps {
  document: DocumentListItem;
}

export default function DocumentRow({ document }: DocumentRowProps) {
  const actionRoute = getNextActionRoute(document.id, document.status);

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap">
        <Link
          to={actionRoute}
          className="text-sm font-medium text-primary-600 hover:text-primary-800"
        >
          {document.fileName}
        </Link>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <DocumentStatusBadge status={document.status} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {document.fileType.toUpperCase()}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatFileSize(document.fileSize)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatDate(document.createdAt)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right">
        <Link
          to={actionRoute}
          className="text-sm text-primary-600 hover:text-primary-800 font-medium"
        >
          Continue
        </Link>
      </td>
    </tr>
  );
}
