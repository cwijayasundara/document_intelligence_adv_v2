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
  onReparse?: (id: string) => void;
  isReparsing?: boolean;
  onClassify?: (id: string) => void;
  isClassifying?: boolean;
  onExtract?: (id: string) => void;
  isExtracting?: boolean;
  onSummarize?: (id: string) => void;
  isSummarizing?: boolean;
  onIngest?: (id: string) => void;
  isIngesting?: boolean;
  onSelect?: (id: string) => void;
  isSelected?: boolean;
}

export default function DocumentRow({
  document,
  onReparse,
  isReparsing,
  onClassify,
  isClassifying,
  onExtract,
  isExtracting,
  onSummarize,
  isSummarizing,
  onIngest,
  isIngesting,
  onSelect,
  isSelected,
}: DocumentRowProps) {
  const actionRoute = getNextActionRoute(document.id, document.status);
  const hasParsed = document.status !== "uploaded";
  const confidence = document.parseConfidencePct;

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      <td className="px-6 py-4 whitespace-nowrap">
        {hasParsed && onSelect ? (
          <button
            onClick={() => onSelect(document.id)}
            className="text-sm font-medium text-primary-600 hover:text-primary-800 hover:underline text-left"
          >
            {document.fileName}
          </button>
        ) : (
          <Link
            to={actionRoute}
            className="text-sm font-medium text-primary-600 hover:text-primary-800"
          >
            {document.fileName}
          </Link>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <DocumentStatusBadge status={document.status} />
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {hasParsed && confidence != null ? (
          <div className="flex items-center gap-2">
            <ConfidencePill value={confidence} />
            {onReparse && (
              <button
                onClick={() => onReparse(document.id)}
                disabled={isReparsing}
                className="text-xs text-gray-500 hover:text-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Force re-parse via Reducto"
              >
                {isReparsing ? "Reparsing..." : "Re-parse"}
              </button>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {document.categoryName ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
            {document.categoryName}
          </span>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
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
        <div className="flex items-center justify-end gap-1">
          {hasParsed && onClassify && (
            <button
              onClick={() => onClassify(document.id)}
              disabled={isClassifying}
              className="p-1.5 rounded-md text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isClassifying ? "Classifying..." : "Classify"}
            >
              {isClassifying ? <SpinnerIcon /> : <TagIcon />}
            </button>
          )}
          {document.documentCategoryId && onExtract && (
            <button
              onClick={() => onExtract(document.id)}
              disabled={isExtracting}
              className="p-1.5 rounded-md text-amber-600 hover:bg-amber-50 hover:text-amber-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isExtracting ? "Extracting..." : "Extract"}
            >
              {isExtracting ? <SpinnerIcon /> : <ExtractIcon />}
            </button>
          )}
          {hasParsed && document.status !== "summarized" && document.status !== "ingested" && onSummarize && (
            <button
              onClick={() => onSummarize(document.id)}
              disabled={isSummarizing}
              className="p-1.5 rounded-md text-purple-600 hover:bg-purple-50 hover:text-purple-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isSummarizing ? "Summarizing..." : "Summarize"}
            >
              {isSummarizing ? <SpinnerIcon /> : <SummarizeIcon />}
            </button>
          )}
          {(document.status === "summarized" || document.status === "ingested") && (
            <span className="p-1.5 text-green-600" title="Summarized">
              <CheckCircleIcon />
            </span>
          )}
          {hasParsed && onIngest && (
            <button
              onClick={() => onIngest(document.id)}
              disabled={isIngesting}
              className="p-1.5 rounded-md text-teal-600 hover:bg-teal-50 hover:text-teal-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isIngesting ? "Ingesting..." : "Ingest"}
            >
              {isIngesting ? <SpinnerIcon /> : <IngestIcon />}
            </button>
          )}
          <Link
            to={actionRoute}
            className="p-1.5 rounded-md text-primary-600 hover:bg-primary-50 hover:text-primary-800 transition-colors"
            title="Continue"
          >
            <ArrowRightIcon />
          </Link>
        </div>
      </td>
    </tr>
  );
}

/** Tag icon — represents categorization / classification. */
function TagIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z" />
    </svg>
  );
}

/** Document/lines icon — represents summarization. */
function SummarizeIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h10M4 18h14" />
    </svg>
  );
}

/** Table/grid icon — represents data extraction. */
function ExtractIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h11M3 6h7m0 8h4m-4 4h7m4-12v16m0 0l-3-3m3 3l3-3" />
    </svg>
  );
}

/** Right arrow icon — represents continue / next step. */
function ArrowRightIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
    </svg>
  );
}

/** Check circle icon — represents completed state. */
function CheckCircleIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

/** Database upload icon — represents ingestion to vector DB. */
function IngestIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 3.6 3 8 3s8-1 8-3V7M4 7c0 2 3.6 3 8 3s8-1 8-3M4 7c0-2 3.6-3 8-3s8 1 8 3" />
    </svg>
  );
}

/** Database with check — represents ingested state. */
function DatabaseCheckIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 3.6 3 8 3s8-1 8-3V7M4 7c0 2 3.6 3 8 3s8-1 8-3M4 7c0-2 3.6-3 8-3s8 1 8 3M9 12l2 2 4-4" />
    </svg>
  );
}

/** Spinner icon for loading states. */
function SpinnerIcon() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function ConfidencePill({ value }: { value: number }) {
  const isHigh = value >= 90;
  const isMedium = value >= 70 && value < 90;

  let colorClasses: string;
  if (isHigh) {
    colorClasses = "bg-green-100 text-green-800";
  } else if (isMedium) {
    colorClasses = "bg-amber-100 text-amber-800";
  } else {
    colorClasses = "bg-red-100 text-red-800";
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorClasses}`}
    >
      {value.toFixed(1)}%
    </span>
  );
}
