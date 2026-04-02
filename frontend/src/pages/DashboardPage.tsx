/** Dashboard page showing document list with status badges. */

import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import DocumentCardGrid from "../components/documents/DocumentCardGrid";
import DocumentDetailPanel from "../components/documents/DocumentDetailPanel";
import DocumentList from "../components/documents/DocumentList";
import EmptyState from "../components/ui/EmptyState";
import PageHeader from "../components/ui/PageHeader";
import { useTriggerClassify } from "../hooks/useClassify";
import { useDocuments } from "../hooks/useDocuments";
import { useTriggerExtract } from "../hooks/useExtraction";
import { useTriggerParse } from "../hooks/useParse";
import { useGenerateSummary } from "../hooks/useSummary";

type ViewMode = "table" | "cards";

export default function DashboardPage() {
  const { data, isLoading, error } = useDocuments();
  const triggerParse = useTriggerParse();
  const triggerClassify = useTriggerClassify();
  const triggerExtract = useTriggerExtract();
  const generateSummary = useGenerateSummary();
  const [reparsingId, setReparsingId] = useState<string>();
  const [classifyingId, setClassifyingId] = useState<string>();
  const [extractingId, setExtractingId] = useState<string>();
  const [summarizingId, setSummarizingId] = useState<string>();
  const [viewMode, setViewMode] = useState<ViewMode>("cards");
  const [selectedId, setSelectedId] = useState<string>();

  const documents = data?.documents ?? [];
  const total = data?.total ?? 0;

  const selectedDoc = useMemo(
    () => documents.find((d) => d.id === selectedId),
    [documents, selectedId],
  );

  const handleReparse = useCallback(
    (id: string) => {
      setReparsingId(id);
      triggerParse.mutate(
        { id, force: true },
        { onSettled: () => setReparsingId(undefined) },
      );
    },
    [triggerParse],
  );

  const handleClassify = useCallback(
    (id: string) => {
      setClassifyingId(id);
      triggerClassify.mutate(id, {
        onSuccess: () => setSelectedId(id),
        onSettled: () => setClassifyingId(undefined),
      });
    },
    [triggerClassify],
  );

  const handleExtract = useCallback(
    (id: string) => {
      setExtractingId(id);
      triggerExtract.mutate(id, {
        onSuccess: () => setSelectedId(id),
        onSettled: () => setExtractingId(undefined),
      });
    },
    [triggerExtract],
  );

  const handleSummarize = useCallback(
    (id: string) => {
      setSummarizingId(id);
      generateSummary.mutate(id, {
        onSuccess: () => setSelectedId(id),
        onSettled: () => setSummarizingId(undefined),
      });
    },
    [generateSummary],
  );

  const handleSelect = useCallback(
    (id: string) => {
      // Toggle: clicking the same doc closes the panel
      setSelectedId((prev) => (prev === id ? undefined : id));
    },
    [],
  );

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={total > 0 ? `${total} documents` : undefined}
        actions={
          <div className="flex items-center gap-3">
            {documents.length > 0 && (
              <div className="flex rounded-md border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setViewMode("table")}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    viewMode === "table"
                      ? "bg-primary-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                  title="Table view"
                >
                  <TableIcon />
                </button>
                <button
                  onClick={() => setViewMode("cards")}
                  className={`px-3 py-1.5 text-xs font-medium border-l border-gray-200 transition-colors ${
                    viewMode === "cards"
                      ? "bg-primary-600 text-white"
                      : "bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                  title="Card view"
                >
                  <GridIcon />
                </button>
              </div>
            )}
            <Link
              to="/upload"
              className="inline-flex items-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500"
            >
              Upload Document
            </Link>
          </div>
        }
      />
      <div className="p-8">
        {isLoading && (
          <div className="text-center py-8 text-gray-500">
            Loading documents...
          </div>
        )}
        {error && (
          <div className="text-center py-8 text-red-500">
            Failed to load documents. Please try again.
          </div>
        )}
        {!isLoading && !error && documents.length === 0 && (
          <EmptyState
            title="No documents yet"
            description="Upload your first document to get started with analysis."
            actionLabel="Upload Document"
            actionTo="/upload"
          />
        )}
        {!isLoading && !error && documents.length > 0 && (
          <>
            {viewMode === "table" ? (
              <DocumentList
                documents={documents}
                onReparse={handleReparse}
                reparsingId={reparsingId}
                onClassify={handleClassify}
                classifyingId={classifyingId}
                onExtract={handleExtract}
                extractingId={extractingId}
                onSummarize={handleSummarize}
                summarizingId={summarizingId}
                onSelect={handleSelect}
                selectedId={selectedId}
              />
            ) : (
              <DocumentCardGrid
                documents={documents}
                onReparse={handleReparse}
                reparsingId={reparsingId}
                onClassify={handleClassify}
                classifyingId={classifyingId}
                onExtract={handleExtract}
                extractingId={extractingId}
                onSummarize={handleSummarize}
                summarizingId={summarizingId}
                onSelect={handleSelect}
                selectedId={selectedId}
              />
            )}

            {/* Inline detail panel below the list */}
            {selectedDoc && (
              <div className="mt-6">
                <DocumentDetailPanel
                  document={selectedDoc}
                  onClose={() => setSelectedId(undefined)}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function TableIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 14h18M3 6h18M3 18h18" />
    </svg>
  );
}

function GridIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
    </svg>
  );
}
