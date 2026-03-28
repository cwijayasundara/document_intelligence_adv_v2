/** 3-column extraction results table with confidence badges and inline editing. */

import type { ExtractionResult } from "../../types/extraction";
import ConfidenceBadge from "./ConfidenceBadge";
import InlineEdit from "./InlineEdit";

interface ExtractionTableProps {
  results: ExtractionResult[];
  onFieldUpdate: (fieldId: string, newValue: string) => void;
}

export default function ExtractionTable({
  results,
  onFieldUpdate,
}: ExtractionTableProps) {
  if (results.length === 0) {
    return (
      <div className="p-6 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500">
          No extraction results yet. Click "Extract" to begin field extraction.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200" data-testid="extraction-table">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Field Name
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Extracted Value
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Source Text
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {results.map((result) => {
            const needsReview = result.requiresReview && !result.reviewed;
            return (
              <tr
                key={result.id}
                className={needsReview ? "bg-amber-50" : ""}
                data-testid={`extraction-row-${result.fieldName}`}
              >
                <td className="px-4 py-3 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900">
                      {result.displayName}
                    </span>
                    <ConfidenceBadge
                      confidence={result.confidence}
                      reasoning={result.confidenceReasoning}
                    />
                    {needsReview && (
                      <span
                        className="text-xs font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded"
                        data-testid="requires-review-label"
                      >
                        Requires Review
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <InlineEdit
                    value={result.extractedValue}
                    onSave={(newValue) => onFieldUpdate(result.id, newValue)}
                  />
                </td>
                <td className="px-4 py-3">
                  <p className="text-sm text-gray-600 max-w-md truncate" title={result.sourceText}>
                    {result.sourceText}
                  </p>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
