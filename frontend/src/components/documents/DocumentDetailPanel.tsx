/** Inline detail panel showing classification, summary, and extraction results. */

import { useState } from "react";
import MarkdownPreview from "../parse/MarkdownPreview";
import { useParseContent } from "../../hooks/useParse";
import { useSummary } from "../../hooks/useSummary";
import { useExtractionResults } from "../../hooks/useExtraction";
import type { DocumentListItem } from "../../types/document";
import type { ConfidenceLevel, ExtractionResult } from "../../types/extraction";
import DocumentStatusBadge from "./DocumentStatusBadge";

interface DocumentDetailPanelProps {
  document: DocumentListItem;
  onClose: () => void;
}

export default function DocumentDetailPanel({
  document,
  onClose,
}: DocumentDetailPanelProps) {
  const { data: parseData, isLoading: parseLoading } = useParseContent(
    document.id,
  );
  const { data: summaryData } = useSummary(document.id);
  const { data: extractionData } = useExtractionResults(document.id);

  const hasParsedContent = !!parseData?.content;
  const hasSummary = !!summaryData?.summary;
  const hasExtraction = !!extractionData?.results?.length;

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-gray-900">
            {document.fileName}
          </h3>
          <DocumentStatusBadge status={document.status} />
          {document.categoryName && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              {document.categoryName}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          title="Close"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content: extraction table spanning full width, then summary + parsed below */}
      <div className="divide-y divide-gray-200">
        {/* Extraction results — full width table */}
        {hasExtraction && (
          <div className="px-6 py-4">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Extracted Fields
            </h4>
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-44">
                      Field
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Extracted Value
                    </th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Source Text
                    </th>
                    <th className="px-4 py-2.5 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                      Confidence
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {extractionData.results.map((r) => (
                    <ExtractionRow key={r.id} result={r} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!hasExtraction && (
          <div className="px-6 py-4">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
              Extracted Fields
            </h4>
            <p className="text-sm text-gray-400">No extraction results yet.</p>
          </div>
        )}

        {/* Summary + Parsed content side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-200">
          {/* Summary */}
          <div className="px-6 py-4">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Summary
            </h4>
            {hasSummary ? (
              <div>
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line line-clamp-[10]">
                  {summaryData.summary}
                </p>
                {summaryData.keyTopics.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {summaryData.keyTopics.map((topic) => (
                      <span
                        key={topic}
                        className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No summary available.</p>
            )}
          </div>

          {/* Parsed content preview */}
          <div className="px-6 py-4">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
              Parsed Content
            </h4>
            {parseLoading && (
              <p className="text-sm text-gray-400">Loading...</p>
            )}
            {!parseLoading && hasParsedContent && (
              <div className="max-h-64 overflow-y-auto text-sm prose prose-sm prose-gray">
                <MarkdownPreview content={parseData.content} />
              </div>
            )}
            {!parseLoading && !hasParsedContent && (
              <p className="text-sm text-gray-400">No parsed content.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ExtractionRow({ result }: { result: ExtractionResult }) {
  const [expanded, setExpanded] = useState(false);
  const hasSource = !!result.sourceText;

  return (
    <tr
      className={`hover:bg-gray-50 ${hasSource ? "cursor-pointer" : ""}`}
      onClick={() => hasSource && setExpanded(!expanded)}
    >
      <td className="px-4 py-2.5 align-top">
        <div className="text-sm font-medium text-gray-900">
          {result.displayName}
        </div>
        {result.requiresReview && (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700 mt-1">
            Needs review
          </span>
        )}
      </td>
      <td className="px-4 py-2.5 align-top">
        <div className="text-sm text-gray-900">
          {result.extractedValue || (
            <span className="text-gray-400 italic">Not found</span>
          )}
        </div>
      </td>
      <td className="px-4 py-2.5 align-top">
        {hasSource ? (
          <div>
            <p
              className={`text-xs text-gray-500 italic leading-relaxed ${
                expanded ? "" : "line-clamp-2"
              }`}
            >
              &ldquo;{result.sourceText}&rdquo;
            </p>
            {result.sourceText.length > 120 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(!expanded);
                }}
                className="text-xs text-primary-600 hover:text-primary-800 mt-1"
              >
                {expanded ? "Show less" : "Show more"}
              </button>
            )}
          </div>
        ) : (
          <span className="text-xs text-gray-400 italic">No source</span>
        )}
      </td>
      <td className="px-4 py-2.5 align-top text-center">
        <ConfidenceBadge level={result.confidence} />
      </td>
    </tr>
  );
}

function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const styles: Record<ConfidenceLevel, string> = {
    high: "bg-green-100 text-green-800",
    medium: "bg-amber-100 text-amber-800",
    low: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${styles[level]}`}
    >
      {level}
    </span>
  );
}
