/** Renders markdown content with proper table styling using react-markdown. */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import type { Options as RehypeSanitizeOptions } from "rehype-sanitize";

const tableSchema: RehypeSanitizeOptions = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "colgroup",
    "col",
  ],
  attributes: {
    ...defaultSchema.attributes,
    table: ["className", "border", "cellPadding", "cellSpacing", "style"],
    th: ["className", "colSpan", "rowSpan", "scope", "style"],
    td: ["className", "colSpan", "rowSpan", "style"],
    tr: ["className", "style"],
    thead: ["className", "style"],
    tbody: ["className", "style"],
    tfoot: ["className", "style"],
  },
};

interface MarkdownPreviewProps {
  content: string;
  className?: string;
}

export default function MarkdownPreview({
  content,
  className = "",
}: MarkdownPreviewProps) {
  return (
    <div className={`prose prose-sm max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, [rehypeSanitize, tableSchema]]}
        components={{
          table: ({ ...props }) => (
            <table
              className="min-w-full border-collapse border border-gray-300 my-4"
              {...props}
            />
          ),
          thead: ({ ...props }) => (
            <thead className="bg-gray-100" {...props} />
          ),
          th: ({ ...props }) => (
            <th
              className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-900"
              {...props}
            />
          ),
          td: ({ ...props }) => (
            <td
              className="border border-gray-300 px-4 py-2 text-gray-700"
              {...props}
            />
          ),
          tr: ({ ...props }) => (
            <tr className="hover:bg-gray-50" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
