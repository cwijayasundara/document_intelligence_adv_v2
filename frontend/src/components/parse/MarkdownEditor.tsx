/** Rich text editor for parsed markdown content.
 *
 * Uses a textarea-based editor as a lightweight alternative
 * to TipTap, avoiding heavy dependencies. When @tiptap/react
 * and @tiptap/starter-kit are installed, this can be swapped
 * for a full TipTap editor.
 */

import { useCallback, useEffect, useState } from "react";

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

  useEffect(() => {
    setLocalContent(content);
  }, [content]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value;
      setLocalContent(value);
      onChange(value);
    },
    [onChange],
  );

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-700">
          Parsed Content Editor
        </h3>
        {readOnly && (
          <span className="text-xs text-gray-400">Read Only</span>
        )}
      </div>
      <textarea
        className="flex-1 w-full p-4 font-mono text-sm text-gray-900 bg-white resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={localContent}
        onChange={handleChange}
        readOnly={readOnly}
        placeholder="Parsed content will appear here..."
        data-testid="markdown-editor"
      />
    </div>
  );
}
