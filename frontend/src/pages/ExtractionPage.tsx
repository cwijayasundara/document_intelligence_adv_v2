/** Extraction results page with 3-column table, confidence badges, and review gate. */

import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ExtractionTable from "../components/extraction/ExtractionTable";
import WorkflowStepper from "../components/documents/WorkflowStepper";
import PageHeader from "../components/ui/PageHeader";
import type { DocumentStatus } from "../types/common";
import { useDocument } from "../hooks/useDocuments";
import {
  useExtractionResults,
  useTriggerExtract,
  useUpdateExtractionResults,
} from "../hooks/useExtraction";
import { useIngestDocument } from "../hooks/useSummary";
import type { ExtractionResult } from "../types/extraction";

export default function ExtractionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const documentId = id ?? "";

  const { data: document, isLoading: docLoading } = useDocument(documentId);
  const { data: extractionData, isLoading: resultsLoading } =
    useExtractionResults(documentId);
  const triggerExtract = useTriggerExtract();
  const updateResults = useUpdateExtractionResults();
  const ingestDocument = useIngestDocument();

  const [localResults, setLocalResults] = useState<ExtractionResult[]>([]);

  // Sync from query data
  useEffect(() => {
    if (extractionData?.results) {
      setLocalResults(extractionData.results);
    }
  }, [extractionData]);

  // Also populate from trigger mutation response
  useEffect(() => {
    if (triggerExtract.data?.results) {
      setLocalResults(triggerExtract.data.results);
    }
  }, [triggerExtract.data]);

  const unreviewedCount = localResults.filter(
    (r) => r.requiresReview && !r.reviewed,
  ).length;

  const canProceed = unreviewedCount === 0 && localResults.length > 0;

  const handleExtract = useCallback(() => {
    triggerExtract.mutate(documentId);
  }, [documentId, triggerExtract]);

  const handleFieldUpdate = useCallback(
    (fieldId: string, newValue: string) => {
      // Update local state optimistically
      setLocalResults((prev) =>
        prev.map((r) =>
          r.id === fieldId
            ? { ...r, extractedValue: newValue, reviewed: true }
            : r,
        ),
      );

      // Send update to server
      updateResults.mutate({
        id: documentId,
        updates: [{ fieldId, extractedValue: newValue, reviewed: true }],
      });
    },
    [documentId, updateResults],
  );

  const handleProceed = useCallback(() => {
    ingestDocument.mutate(documentId, {
      onSuccess: () => {
        navigate(`/documents/${documentId}/chat`);
      },
    });
  }, [documentId, ingestDocument, navigate]);

  const canExtract = document?.status === "classified";

  if (docLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Extract Fields" />

      <WorkflowStepper
        documentId={documentId}
        documentStatus={document?.status as DocumentStatus | undefined}
        currentStep="extract"
      />

      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-200">
        <button
          onClick={handleExtract}
          disabled={!canExtract || triggerExtract.isPending}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="extract-button"
        >
          {triggerExtract.isPending ? "Extracting..." : "Extract"}
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={handleProceed}
            disabled={!canProceed || ingestDocument.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="proceed-button"
          >
            {ingestDocument.isPending ? "Ingesting..." : "Ingest & Proceed to Chat"}
          </button>
          {!canProceed && localResults.length > 0 && (
            <span
              className="text-sm text-amber-700"
              data-testid="review-gate-message"
            >
              Review all flagged fields first ({unreviewedCount} remaining)
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {resultsLoading ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            Loading results...
          </div>
        ) : (
          <ExtractionTable
            results={localResults}
            onFieldUpdate={handleFieldUpdate}
          />
        )}
      </div>
    </div>
  );
}
