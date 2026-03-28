/** List of bulk jobs with status badges, progress bars, and expandable details. */

import { useState } from "react";
import type { BulkJob, BulkJobStatus } from "../../types/bulk";
import { useBulkJobDetail } from "../../hooks/useBulk";
import BulkJobDetailView from "./BulkJobDetail";

const STATUS_BADGE_STYLES: Record<BulkJobStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function ProgressBar({
  processed,
  total,
}: {
  processed: number;
  total: number;
}) {
  const percent = total > 0 ? Math.round((processed / total) * 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary-600 rounded-full transition-all"
          style={{ width: `${percent}%` }}
          data-testid="progress-bar-fill"
        />
      </div>
      <span className="text-sm text-gray-600 whitespace-nowrap">
        {processed} / {total}
      </span>
    </div>
  );
}

function JobRow({ job }: { job: BulkJob }) {
  const [expanded, setExpanded] = useState(false);
  const { data: detail } = useBulkJobDetail(expanded ? job.id : null);

  return (
    <div
      className="border border-gray-200 rounded-lg overflow-hidden"
      data-testid="bulk-job-card"
    >
      <button
        type="button"
        className="w-full text-left px-6 py-4 hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        data-testid="bulk-job-toggle"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE_STYLES[job.status]}`}
              data-testid="bulk-job-status-badge"
            >
              {job.status}
            </span>
            <span className="text-sm text-gray-500">
              {formatDate(job.createdAt)}
            </span>
            {job.failedCount > 0 && (
              <span className="text-xs text-red-600 font-medium">
                {job.failedCount} failed
              </span>
            )}
          </div>
          <span className="text-gray-400 text-sm">
            {expanded ? "Collapse" : "Expand"}
          </span>
        </div>
        <div className="mt-3">
          <ProgressBar
            processed={job.processedCount}
            total={job.totalDocuments}
          />
        </div>
      </button>

      {expanded && detail && (
        <BulkJobDetailView documents={detail.documents} />
      )}
    </div>
  );
}

interface BulkJobListProps {
  jobs: BulkJob[];
}

export default function BulkJobList({ jobs }: BulkJobListProps) {
  if (jobs.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-6 text-center" data-testid="bulk-job-empty">
        No bulk jobs yet. Upload files above to get started.
      </p>
    );
  }

  return (
    <div className="space-y-4" data-testid="bulk-job-list">
      {jobs.map((job) => (
        <JobRow key={job.id} job={job} />
      ))}
    </div>
  );
}
