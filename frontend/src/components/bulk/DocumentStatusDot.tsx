/** Status indicator dot for bulk document processing states. */

import type { BulkDocumentStatus } from "../../types/bulk";

const STATUS_COLORS: Record<BulkDocumentStatus, string> = {
  pending: "bg-gray-400",
  processing: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
};

const STATUS_LABELS: Record<BulkDocumentStatus, string> = {
  pending: "Pending",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
};

interface DocumentStatusDotProps {
  status: BulkDocumentStatus;
}

export default function DocumentStatusDot({ status }: DocumentStatusDotProps) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        data-testid={`status-dot-${status}`}
        className={`inline-block h-2.5 w-2.5 rounded-full ${STATUS_COLORS[status]}`}
        aria-label={STATUS_LABELS[status]}
      />
      <span className="text-sm text-gray-600">{STATUS_LABELS[status]}</span>
    </span>
  );
}
