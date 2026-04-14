/** Classification page: detect category, override, and accept. */

import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import CategoryOverride from "../components/classify/CategoryOverride";
import ClassificationResult from "../components/classify/ClassificationResult";
import WorkflowStepper from "../components/documents/WorkflowStepper";
import PageHeader from "../components/ui/PageHeader";
import type { DocumentStatus } from "../types/common";
import { useCategories } from "../hooks/useCategories";
import { useTriggerClassify } from "../hooks/useClassify";
import { useDocument } from "../hooks/useDocuments";

export default function ClassifyPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const documentId = id ?? "";

  const { data: document, isLoading: docLoading } = useDocument(documentId);
  const { data: categoriesData } = useCategories();
  const triggerClassify = useTriggerClassify();

  const [categoryName, setCategoryName] = useState<string | null>(null);
  const [reasoning, setReasoning] = useState<string | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );

  const categories =
    categoriesData?.categories?.map((c) => ({ id: c.id, name: c.name })) ?? [];

  // Guard: only accessible after parse/edit/summarize
  const canAccess =
    document?.status === "parsed" ||
    document?.status === "edited" ||
    document?.status === "summarized" ||
    document?.status === "classified";

  const handleClassify = useCallback(() => {
    triggerClassify.mutate(documentId, {
      onSuccess: (data) => {
        setCategoryName(data.categoryName);
        setReasoning(data.reasoning);
        setSelectedCategoryId(data.categoryId);
      },
    });
  }, [documentId, triggerClassify]);

  const handleCategoryChange = useCallback((categoryId: string) => {
    setSelectedCategoryId(categoryId);
    const cat = categories.find((c) => c.id === categoryId);
    if (cat) {
      setCategoryName(cat.name);
    }
  }, [categories]);

  const handleAcceptProceed = useCallback(() => {
    navigate(`/documents/${documentId}/extract`);
  }, [documentId, navigate]);

  if (docLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Loading...
      </div>
    );
  }

  if (!canAccess && document) {
    return (
      <div className="flex flex-col h-full">
        <PageHeader title="Classify Document" />
        <WorkflowStepper
          documentId={documentId}
          documentStatus={document.status as DocumentStatus}
          currentStep="classify"
        />
        <div className="p-6">
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-800" data-testid="status-guard-message">
              Document must be parsed and summarized before classification.
              Current status: {document.status}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Classify Document" />

      <WorkflowStepper
        documentId={documentId}
        documentStatus={document?.status as DocumentStatus | undefined}
        currentStep="classify"
      />

      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-200">
        <button
          onClick={handleClassify}
          disabled={triggerClassify.isPending}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="classify-button"
        >
          {triggerClassify.isPending ? "Classifying..." : "Classify"}
        </button>

        {categoryName && (
          <button
            onClick={handleAcceptProceed}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700"
            data-testid="accept-proceed-button"
          >
            Accept &amp; Proceed
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <ClassificationResult
          categoryName={categoryName}
          reasoning={reasoning}
        />

        {categoryName && (
          <CategoryOverride
            categories={categories}
            selectedCategoryId={selectedCategoryId}
            onCategoryChange={handleCategoryChange}
          />
        )}
      </div>
    </div>
  );
}
