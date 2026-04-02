/** Parse/Edit page with split view: document info + markdown editor.
 *
 * Shows confidence banner from Reducto parse. When confidence >= 90%,
 * the editor defaults to preview-only (no edit button). When confidence
 * is lower, edit mode is enabled by default so users can fix OCR errors
 * or handwritten content.
 */

import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ConfidenceBanner, {
  CONFIDENCE_THRESHOLD,
} from "../components/parse/ConfidenceBanner";
import DocumentInfo from "../components/parse/DocumentInfo";
import MarkdownEditor from "../components/parse/MarkdownEditor";
import PageHeader from "../components/ui/PageHeader";
import { useDocument } from "../hooks/useDocuments";
import { useParseContent, useSaveEdits, useTriggerParse } from "../hooks/useParse";

export default function ParsePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const documentId = id ?? "";

  const { data: document, isLoading: docLoading } = useDocument(documentId);
  const { data: parseData, isLoading: contentLoading } = useParseContent(documentId);
  const triggerParse = useTriggerParse();
  const saveEdits = useSaveEdits();

  const [editorContent, setEditorContent] = useState("");
  const [hasEdits, setHasEdits] = useState(false);

  const handleContentChange = useCallback((content: string) => {
    setEditorContent(content);
    setHasEdits(true);
  }, []);

  const handleParse = useCallback(() => {
    triggerParse.mutate({ id: documentId });
  }, [documentId, triggerParse]);

  const handleSave = useCallback(() => {
    saveEdits.mutate({ id: documentId, content: editorContent });
    setHasEdits(false);
  }, [documentId, editorContent, saveEdits]);

  const handleProceed = useCallback(() => {
    navigate(`/documents/${documentId}/classify`);
  }, [documentId, navigate]);

  const isParsed = document?.status === "parsed" || document?.status === "edited";
  const canParse = document?.status === "uploaded";
  const content = parseData?.content ?? "";
  const confidencePct = parseData?.confidencePct ?? 100;
  const isHighConfidence = confidencePct >= CONFIDENCE_THRESHOLD;

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Parse & Edit Document" />

      {/* Confidence banner — shown when document is parsed */}
      {isParsed && <ConfidenceBanner confidencePct={confidencePct} />}

      <div className="flex items-center gap-3 px-6 py-3 border-b border-gray-200">
        <button
          onClick={handleParse}
          disabled={!canParse || triggerParse.isPending}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="parse-button"
        >
          {triggerParse.isPending ? "Parsing..." : "Parse Document"}
        </button>

        {/* Save button — only show when editing is needed (low confidence) */}
        {!isHighConfidence && (
          <button
            onClick={handleSave}
            disabled={!hasEdits || saveEdits.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="save-button"
          >
            {saveEdits.isPending ? "Saving..." : "Save Edits"}
          </button>
        )}

        {isParsed && (
          <button
            onClick={handleProceed}
            className="px-4 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700"
            data-testid="proceed-button"
          >
            Proceed to Classify
          </button>
        )}
      </div>

      <div className="flex-1 flex min-h-0">
        <div className="w-1/3 border-r border-gray-200 overflow-y-auto">
          <DocumentInfo document={document} isLoading={docLoading} />
        </div>

        <div className="w-2/3 overflow-hidden">
          {contentLoading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              Loading content...
            </div>
          ) : (
            <MarkdownEditor
              content={content}
              onChange={handleContentChange}
              readOnly={!isParsed || isHighConfidence}
            />
          )}
        </div>
      </div>
    </div>
  );
}
