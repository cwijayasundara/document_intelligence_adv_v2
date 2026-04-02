/** Split-view markdown editor with raw text editing and live preview. */

import { useCallback, useEffect, useState } from "react";
import MarkdownPreview from "./MarkdownPreview";

type ViewMode = "edit" | "split" | "preview";

interface MarkdownEditorProps {
  content: string;
  onChange: (content: string) => void;
  readOnly?: boolean;
}

export default function MarkdownEditor({
  content,
  onChange,
  readOnly = false,
}: MarkdownEditorProps) {
  const [localContent, setLocalContent] = useState(content);
  const [viewMode, setViewMode] = useState<ViewMode>(
    readOnly ? "preview" : "split",
  );

  useEffect(() => {
    setLocalContent(content);
  }, [content]);

  useEffect(() => {
    if (readOnly) setViewMode("preview");
  }, [readOnly]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      setLocalContent(value);
      onChange(value);
    },
    [onChange],
  );

  const showEditor = viewMode === "edit" || viewMode === "split";
  const showPreview = viewMode === "preview" || viewMode === "split";

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-700">
          Parsed Content
        </h3>
        <div className="flex items-center gap-1">
          {!readOnly && (
            <div className="flex rounded border border-gray-200 overflow-hidden">
              <button
                onClick={() => setViewMode("edit")}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  viewMode === "edit"
                    ? "bg-primary-600 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                Edit
              </button>
              <button
                onClick={() => setViewMode("split")}
                className={`px-3 py-1 text-xs font-medium border-l border-gray-200 transition-colors ${
                  viewMode === "split"
                    ? "bg-primary-600 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                Split
              </button>
              <button
                onClick={() => setViewMode("preview")}
                className={`px-3 py-1 text-xs font-medium border-l border-gray-200 transition-colors ${
                  viewMode === "preview"
                    ? "bg-primary-600 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50"
                }`}
              >
                Preview
              </button>
            </div>
          )}
          {readOnly && (
            <span className="text-xs text-gray-400">Read Only</span>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 flex min-h-0">
        {showEditor && (
          <div className={showPreview ? "w-1/2 border-r border-gray-200" : "w-full"}>
            <textarea
              className="w-full h-full p-4 font-mono text-sm text-gray-900 bg-white resize-none focus:outline-none"
              value={localContent}
              onChange={handleChange}
              readOnly={readOnly}
              placeholder="Parsed content will appear here..."
              data-testid="markdown-editor"
            />
          </div>
        )}
        {showPreview && (
          <div className={showEditor ? "w-1/2" : "w-full"}>
            <div className="h-full overflow-y-auto p-4">
              {localContent ? (
                <MarkdownPreview content={localContent} />
              ) : (
                <p className="text-gray-400 text-sm">No content to preview</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
