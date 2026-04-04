/** Document tree with checkboxes for selecting documents for RAG queries. */

import { useState } from "react";
import type { DocumentListItem } from "../../types/document";
import type { RagQueryResponse, Citation, SearchMode } from "../../types/rag";
import { submitRagQuery } from "../../lib/api/rag";
import { useSessionId } from "../../hooks/useSession";
import DocumentStatusBadge from "./DocumentStatusBadge";

interface DocumentTreePanelProps {
  documents: DocumentListItem[];
}

export default function DocumentTreePanel({ documents }: DocumentTreePanelProps) {
  const sessionId = useSessionId();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const searchMode: SearchMode = "hybrid";
  const [isQuerying, setIsQuerying] = useState(false);
  const [result, setResult] = useState<RagQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ingestedDocs = documents.filter((d) => d.status === "ingested");
  const otherDocs = documents.filter((d) => d.status !== "ingested");

  const toggleDoc = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedIds.size === ingestedDocs.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(ingestedDocs.map((d) => d.id)));
    }
  };

  const handleQuery = async () => {
    if (!query.trim() || selectedIds.size === 0) return;

    setIsQuerying(true);
    setError(null);
    setResult(null);

    try {
      const ids = Array.from(selectedIds);
      if (ids.length === 1) {
        const res = await submitRagQuery({
          query: query.trim(),
          scope: "single_document",
          scopeId: ids[0],
          searchMode,
          sessionId,
        });
        setResult(res);
      } else {
        const responses = await Promise.all(
          ids.map((id) =>
            submitRagQuery({
              query: query.trim(),
              scope: "single_document",
              scopeId: id,
              searchMode,
              sessionId,
            }),
          ),
        );
        const allCitations: Citation[] = responses.flatMap((r) => r.citations);
        allCitations.sort((a, b) => b.relevanceScore - a.relevanceScore);
        const mergedAnswer = responses.map((r) => r.answer).join("\n\n---\n\n");
        setResult({
          answer: mergedAnswer,
          citations: allCitations.slice(0, 10),
          searchMode,
          chunksRetrieved: allCitations.length,
        });
      }
    } catch {
      setError("Failed to run query. Ensure documents are ingested.");
    } finally {
      setIsQuerying(false);
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg bg-white shadow-sm overflow-hidden">
      <div className="px-5 py-3 bg-gray-50 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900">
          Document Search (RAG)
        </h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Select documents and ask questions about their content
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 divide-y lg:divide-y-0 lg:divide-x divide-gray-200">
        {/* Document tree */}
        <div className="p-4 lg:col-span-1">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Documents
            </h4>
            {ingestedDocs.length > 0 && (
              <button
                onClick={toggleAll}
                className="text-xs text-primary-600 hover:text-primary-800"
              >
                {selectedIds.size === ingestedDocs.length
                  ? "Deselect all"
                  : "Select all"}
              </button>
            )}
          </div>

          <div className="space-y-1 max-h-64 overflow-y-auto">
            {/* Ingested documents — selectable */}
            {ingestedDocs.length > 0 && (
              <div>
                <div className="text-xs font-medium text-green-700 mb-1 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 3.6 3 8 3s8-1 8-3V7M4 7c0 2 3.6 3 8 3s8-1 8-3M4 7c0-2 3.6-3 8-3s8 1 8 3" />
                  </svg>
                  Ingested ({ingestedDocs.length})
                </div>
                {ingestedDocs.map((doc) => (
                  <label
                    key={doc.id}
                    className={`flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer transition-colors ${
                      selectedIds.has(doc.id)
                        ? "bg-primary-50 text-primary-800"
                        : "hover:bg-gray-50 text-gray-700"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(doc.id)}
                      onChange={() => toggleDoc(doc.id)}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-xs truncate flex-1" title={doc.fileName}>
                      {doc.fileName}
                    </span>
                  </label>
                ))}
              </div>
            )}

            {/* Other documents — not selectable */}
            {otherDocs.length > 0 && (
              <div className="mt-2">
                <div className="text-xs font-medium text-gray-400 mb-1">
                  Not ingested ({otherDocs.length})
                </div>
                {otherDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-2 px-2 py-1.5 text-gray-400"
                  >
                    <input
                      type="checkbox"
                      disabled
                      className="rounded border-gray-200"
                    />
                    <span className="text-xs truncate flex-1" title={doc.fileName}>
                      {doc.fileName}
                    </span>
                    <DocumentStatusBadge status={doc.status} />
                  </div>
                ))}
              </div>
            )}

            {documents.length === 0 && (
              <p className="text-xs text-gray-400 py-2">No documents uploaded.</p>
            )}
          </div>
        </div>

        {/* Query + Results */}
        <div className="p-4 lg:col-span-3 flex flex-col">
          {/* Centered search bar */}
          <div className={`flex flex-col items-center ${result || error ? "" : "justify-center flex-1 min-h-[200px]"}`}>
            <div className="w-full">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                  placeholder={
                    selectedIds.size === 0
                      ? "Select documents first..."
                      : `Ask about ${selectedIds.size} document${selectedIds.size > 1 ? "s" : ""}...`
                  }
                  disabled={selectedIds.size === 0}
                  className="w-full py-3.5 pl-12 pr-28 text-base rounded-full border border-gray-300 shadow-sm hover:shadow-md focus:shadow-md focus:border-primary-400 focus:ring-1 focus:ring-primary-400 disabled:bg-gray-50 disabled:text-gray-400 transition-shadow"
                />
                <div className="absolute inset-y-0 right-0 pr-2 flex items-center">
                  <button
                    onClick={handleQuery}
                    disabled={isQuerying || selectedIds.size === 0 || !query.trim()}
                    className="px-5 py-2 text-sm font-medium text-white bg-primary-600 rounded-full hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isQuerying ? "Searching..." : "Search"}
                  </button>
                </div>
              </div>
              {!result && !error && !isQuerying && (
                <p className="text-center text-xs text-gray-400 mt-3">
                  {selectedIds.size === 0
                    ? "Select one or more ingested documents to start searching."
                    : "Ask a question about the selected documents."}
                </p>
              )}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-red-600 mt-4 text-center">{error}</div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4 mt-6 max-w-3xl mx-auto w-full">
              {/* Answer */}
              <div>
                <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                  Answer
                </h4>
                <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-line bg-gray-50 rounded-lg p-4">
                  {result.answer}
                </p>
              </div>

              {/* Citations */}
              {result.citations.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Sources ({result.chunksRetrieved} chunks)
                  </h4>
                  <div className="space-y-2">
                    {result.citations.map((c, i) => (
                      <div
                        key={i}
                        className="border border-gray-200 rounded-lg p-3 bg-white hover:shadow-sm transition-shadow"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="min-w-0">
                            <span className="text-xs font-medium text-gray-700">
                              {c.documentName}
                            </span>
                            {c.section && (
                              <span className="text-xs text-gray-400 ml-1.5">
                                {c.section}
                              </span>
                            )}
                          </div>
                          <span className="text-xs text-gray-400 whitespace-nowrap ml-2">
                            {(c.relevanceScore * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-600 leading-relaxed line-clamp-4 mt-1">
                          {c.chunkText}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
