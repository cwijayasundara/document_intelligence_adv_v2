/** Color-coded status badge for document statuses. */

import type { DocumentStatus } from "../../types/common";

const statusConfig: Record<
  DocumentStatus,
  { label: string; className: string }
> = {
  uploaded: {
    label: "Uploaded",
    className: "bg-gray-100 text-gray-700",
  },
  parsed: {
    label: "Parsed",
    className: "bg-blue-100 text-blue-700",
  },
  edited: {
    label: "Edited",
    className: "bg-blue-100 text-blue-700",
  },
  classified: {
    label: "Classified",
    className: "bg-yellow-100 text-yellow-700",
  },
  extracted: {
    label: "Extracted",
    className: "bg-orange-100 text-orange-700",
  },
  summarized: {
    label: "Summarized",
    className: "bg-purple-100 text-purple-700",
  },
  ingested: {
    label: "Ingested",
    className: "bg-green-100 text-green-700",
  },
  processing: {
    label: "Processing",
    className: "bg-blue-100 text-blue-700",
  },
  awaiting_parse_review: {
    label: "Awaiting Parse Review",
    className: "bg-amber-100 text-amber-700",
  },
  awaiting_extraction_review: {
    label: "Awaiting Extraction Review",
    className: "bg-amber-100 text-amber-700",
  },
};

interface DocumentStatusBadgeProps {
  status: DocumentStatus;
}

export default function DocumentStatusBadge({
  status,
}: DocumentStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.uploaded;
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.className}`}
      data-testid="status-badge"
    >
      {config.label}
    </span>
  );
}
