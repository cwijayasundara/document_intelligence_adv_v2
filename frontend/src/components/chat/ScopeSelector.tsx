/** Scope selector for RAG queries: This Document, All Documents, By Category. */

import type { Category } from "../../types/config";
import type { QueryScope } from "../../types/rag";

interface ScopeSelectorProps {
  scope: QueryScope;
  scopeId: string | undefined;
  onScopeChange: (scope: QueryScope) => void;
  onScopeIdChange: (id: string) => void;
  documentId: string;
  categories: Category[];
}

export default function ScopeSelector({
  scope,
  scopeId,
  onScopeChange,
  onScopeIdChange,
  documentId,
  categories,
}: ScopeSelectorProps) {
  return (
    <div className="flex items-center gap-3" data-testid="scope-selector">
      <label className="text-sm font-medium text-gray-700">Scope:</label>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onScopeChange("single_document")}
          className={`px-3 py-1 text-xs rounded-full border ${
            scope === "single_document"
              ? "bg-blue-100 text-blue-800 border-blue-200"
              : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
          }`}
          data-testid="scope-single"
        >
          This Document
        </button>
        <button
          onClick={() => onScopeChange("all")}
          className={`px-3 py-1 text-xs rounded-full border ${
            scope === "all"
              ? "bg-blue-100 text-blue-800 border-blue-200"
              : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
          }`}
          data-testid="scope-all"
        >
          All Documents
        </button>
        <button
          onClick={() => onScopeChange("by_category")}
          className={`px-3 py-1 text-xs rounded-full border ${
            scope === "by_category"
              ? "bg-blue-100 text-blue-800 border-blue-200"
              : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
          }`}
          data-testid="scope-category"
        >
          By Category
        </button>
      </div>

      {scope === "by_category" && (
        <select
          value={scopeId ?? ""}
          onChange={(e) => onScopeIdChange(e.target.value)}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
          data-testid="category-scope-select"
        >
          <option value="" disabled>
            Select category
          </option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
