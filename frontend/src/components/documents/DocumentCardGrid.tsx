/** Card grid view for documents on the dashboard. */

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
  });
}

interface DocumentCardGridProps {
  documents: DocumentListItem[];
  onReparse?: (id: string) => void;
  reparsingId?: string;
  onClassify?: (id: string) => void;
  classifyingId?: string;
  onExtract?: (id: string) => void;
  extractingId?: string;
  onSummarize?: (id: string) => void;
  summarizingId?: string;
  onIngest?: (id: string) => void;
  ingestingId?: string;
  onSelect?: (id: string) => void;
  selectedId?: string;
}

export default function DocumentCardGrid({
  documents,
  onReparse,
  reparsingId,
  onClassify,
  classifyingId,
  onExtract,
  extractingId,
  onSummarize,
  summarizingId,
  onIngest,
  ingestingId,
  onSelect,
  selectedId,
}: DocumentCardGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {documents.map((doc) => (
        <DocumentCard
          key={doc.id}
          document={doc}
          onReparse={onReparse}
          isReparsing={reparsingId === doc.id}
          onClassify={onClassify}
          isClassifying={classifyingId === doc.id}
          onExtract={onExtract}
          isExtracting={extractingId === doc.id}
          onSummarize={onSummarize}
          isSummarizing={summarizingId === doc.id}
          onIngest={onIngest}
          isIngesting={ingestingId === doc.id}
          onSelect={onSelect}
          isSelected={selectedId === doc.id}
        />
      ))}
    </div>
  );
}

function DocumentCard({
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
}: {
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
}) {
  const actionRoute = getNextActionRoute(document.id, document.status);
  const hasParsed = document.status !== "uploaded";
  const confidence = document.parseConfidencePct;

  // Gate buttons by workflow order: Parse → Summarize → Classify → Extract → Ingest
  const canSummarize = hasParsed;
  const hasSummary =
    document.status === "summarized" ||
    document.status === "classified" ||
    document.status === "extracted" ||
    document.status === "ingested";
  const canClassify = hasSummary || document.status === "classified";
  const hasClassified =
    document.status === "classified" ||
    document.status === "extracted" ||
    document.status === "ingested";
  const canExtract = hasClassified;
  const hasExtracted =
    document.status === "extracted" || document.status === "ingested";
  const canIngest = hasExtracted;
  const hasIngested = document.status === "ingested";

  return (
    <div
      className={`bg-white rounded-lg border shadow-sm hover:shadow-md transition-shadow ${isSelected ? "border-primary-400 ring-2 ring-primary-100" : "border-gray-200"}`}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-gray-100">
        <div className="flex items-start justify-between gap-2">
          {hasParsed && onSelect ? (
            <button
              onClick={() => onSelect(document.id)}
              className="text-sm font-semibold text-gray-900 hover:text-primary-600 truncate text-left"
              title={document.fileName}
            >
              {document.fileName}
            </button>
          ) : (
            <Link
              to={actionRoute}
              className="text-sm font-semibold text-gray-900 hover:text-primary-600 truncate"
              title={document.fileName}
            >
              {document.fileName}
            </Link>
          )}
          <DocumentStatusBadge status={document.status} />
        </div>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{document.fileType.toUpperCase()}</span>
          <span>{formatFileSize(document.fileSize)}</span>
        </div>

        {/* Category badge */}
        {document.categoryName && (
          <div className="flex items-center gap-1.5">
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              {document.categoryName}
            </span>
          </div>
        )}

        {/* Confidence bar */}
        {hasParsed && confidence != null && (
          <div>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-gray-500">Parse Confidence</span>
              <span
                className={`font-medium ${
                  confidence >= 90
                    ? "text-green-700"
                    : confidence >= 70
                      ? "text-amber-700"
                      : "text-red-700"
                }`}
              >
                {confidence.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full transition-all ${
                  confidence >= 90
                    ? "bg-green-500"
                    : confidence >= 70
                      ? "bg-amber-500"
                      : "bg-red-500"
                }`}
                style={{ width: `${Math.min(confidence, 100)}%` }}
              />
            </div>
          </div>
        )}

        <div className="text-xs text-gray-400">
          {formatDate(document.createdAt)}
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-1">
          {/* Step 1: Summarize */}
          {hasSummary ? (
            <span className="p-1.5 text-green-600" title="Summarized">
              <CheckCircleIcon />
            </span>
          ) : canSummarize && onSummarize ? (
            <button
              onClick={() => onSummarize(document.id)}
              disabled={isSummarizing}
              className="p-1.5 rounded-md text-purple-600 hover:bg-purple-50 hover:text-purple-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isSummarizing ? "Summarizing..." : "Summarize"}
            >
              {isSummarizing ? <SpinnerIcon /> : <SummarizeIcon />}
            </button>
          ) : null}

          {/* Step 2: Classify */}
          {hasClassified ? (
            <span className="p-1.5 text-green-600" title="Classified">
              <CheckCircleIcon />
            </span>
          ) : canClassify && onClassify ? (
            <button
              onClick={() => onClassify(document.id)}
              disabled={isClassifying}
              className="p-1.5 rounded-md text-indigo-600 hover:bg-indigo-50 hover:text-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isClassifying ? "Classifying..." : "Classify"}
            >
              {isClassifying ? <SpinnerIcon /> : <TagIcon />}
            </button>
          ) : null}

          {/* Step 3: Extract */}
          {hasExtracted ? (
            <span className="p-1.5 text-green-600" title="Extracted">
              <CheckCircleIcon />
            </span>
          ) : canExtract && onExtract ? (
            <button
              onClick={() => onExtract(document.id)}
              disabled={isExtracting}
              className="p-1.5 rounded-md text-amber-600 hover:bg-amber-50 hover:text-amber-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isExtracting ? "Extracting..." : "Extract"}
            >
              {isExtracting ? <SpinnerIcon /> : <ExtractIcon />}
            </button>
          ) : null}

          {/* Step 4: Ingest */}
          {hasIngested ? (
            <span className="p-1.5 text-green-600" title="Ingested">
              <CheckCircleIcon />
            </span>
          ) : canIngest && onIngest ? (
            <button
              onClick={() => onIngest(document.id)}
              disabled={isIngesting}
              className="p-1.5 rounded-md text-teal-600 hover:bg-teal-50 hover:text-teal-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isIngesting ? "Ingesting..." : "Ingest"}
            >
              {isIngesting ? <SpinnerIcon /> : <IngestIcon />}
            </button>
          ) : null}

          {/* Re-parse (always available after parse) */}
          {hasParsed && onReparse && (
            <button
              onClick={() => onReparse(document.id)}
              disabled={isReparsing}
              className="p-1.5 rounded-md text-gray-400 hover:bg-gray-50 hover:text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={isReparsing ? "Reparsing..." : "Re-parse"}
            >
              {isReparsing ? <SpinnerIcon /> : <RefreshIcon />}
            </button>
          )}
        </div>
        <Link
          to={actionRoute}
          className="p-1.5 rounded-md text-primary-600 hover:bg-primary-50 hover:text-primary-800 transition-colors"
          title="Continue"
        >
          <ArrowRightIcon />
        </Link>
      </div>
    </div>
  );
}

function TagIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z" />
    </svg>
  );
}

function SummarizeIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h10M4 18h14" />
    </svg>
  );
}

function ExtractIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h11M3 6h7m0 8h4m-4 4h7m4-12v16m0 0l-3-3m3 3l3-3" />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}

function IngestIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 3.6 3 8 3s8-1 8-3V7M4 7c0 2 3.6 3 8 3s8-1 8-3M4 7c0-2 3.6-3 8-3s8 1 8 3" />
    </svg>
  );
}

function DatabaseCheckIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 3.6 3 8 3s8-1 8-3V7M4 7c0 2 3.6 3 8 3s8-1 8-3M4 7c0-2 3.6-3 8-3s8 1 8 3M9 12l2 2 4-4" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
