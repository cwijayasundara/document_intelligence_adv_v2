/** Expandable citation card showing chunk text, document name, and relevance score. */

import { useState } from "react";
import type { Citation } from "../../types/rag";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export default function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  const scorePercent = Math.round(citation.relevanceScore * 100);

  return (
    <div
      className="border border-gray-200 rounded-lg overflow-hidden"
      data-testid={`citation-card-${index}`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 text-left"
        data-testid={`citation-toggle-${index}`}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-blue-600">
            [{index + 1}]
          </span>
          <span className="text-sm text-gray-700 truncate max-w-xs">
            {citation.documentName}
          </span>
        </div>
        <span className="text-xs text-gray-500">
          {scorePercent}% relevance
        </span>
      </button>

      {expanded && (
        <div className="px-3 py-2 text-sm text-gray-600 border-t border-gray-100" data-testid={`citation-content-${index}`}>
          <p className="whitespace-pre-wrap">{citation.chunkText}</p>
        </div>
      )}
    </div>
  );
}
