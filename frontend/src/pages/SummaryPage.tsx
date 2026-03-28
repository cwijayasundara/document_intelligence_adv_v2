/** Summary page with generate, regenerate, and proceed to ingest/chat. */

import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import SummaryDisplay from "../components/summary/SummaryDisplay";
import TopicTags from "../components/summary/TopicTags";
import PageHeader from "../components/ui/PageHeader";
import { useDocument } from "../hooks/useDocuments";
import {
  useGenerateSummary,
  useIngestDocument,
  useSummary,
} from "../hooks/useSummary";

export default function SummaryPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const documentId = id ?? "";

  const { data: document } = useDocument(documentId);
  const { data: summaryData, isLoading: summaryLoading } = useSummary(documentId);
  const generateSummary = useGenerateSummary();
  const ingestDocument = useIngestDocument();

  const [localSummary, setLocalSummary] = useState<string>("");
  const [localTopics, setLocalTopics] = useState<string[]>([]);

  const displaySummary = localSummary || summaryData?.summary || "";
  const displayTopics = localTopics.length > 0
    ? localTopics
    : summaryData?.keyTopics ?? [];

  const handleGenerate = useCallback(() => {
    generateSummary.mutate(documentId, {
      onSuccess: (data) => {
        setLocalSummary(data.summary);
        setLocalTopics(data.keyTopics);
      },
    });
  }, [documentId, generateSummary]);

  const handleProceed = useCallback(async () => {
    ingestDocument.mutate(documentId, {
      onSuccess: () => {
        navigate(`/documents/${documentId}/chat`);
      },
    });
  }, [documentId, ingestDocument, navigate]);

  const hasSummary = displaySummary.length > 0;
  const isGenerating = generateSummary.isPending;
  const isIngesting = ingestDocument.isPending;

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Document Summary" />

      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-200">
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="generate-button"
        >
          {isGenerating
            ? "Generating..."
            : hasSummary
              ? "Regenerate"
              : "Generate Summary"}
        </button>

        {hasSummary && (
          <button
            onClick={handleProceed}
            disabled={isIngesting}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="proceed-button"
          >
            {isIngesting ? "Ingesting..." : "Proceed to Ingest & Chat"}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        <SummaryDisplay
          summary={displaySummary}
          isLoading={summaryLoading && !localSummary}
        />
        <TopicTags topics={displayTopics} />
      </div>
    </div>
  );
}
