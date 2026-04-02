/** Extraction field editor with inline editable table. */

import { useCallback, useEffect, useState } from "react";
import {
  useCreateFields,
  useExtractionFields,
} from "../../hooks/useExtractionFields";
import type { FieldCreateRequest } from "../../types/config";

const DATA_TYPES = ["string", "number", "date", "currency", "percentage"];

interface EditableRow {
  key: string;
  fieldName: string;
  displayName: string;
  description: string;
  examples: string;
  dataType: string;
  required: boolean;
  sortOrder: number;
}

function toSnakeCase(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "");
}

interface ExtractionFieldEditorProps {
  categoryId: string;
  categoryName: string;
}

export default function ExtractionFieldEditor({
  categoryId,
  categoryName,
}: ExtractionFieldEditorProps) {
  const { data, isLoading } = useExtractionFields(categoryId);
  const createMutation = useCreateFields();
  const [rows, setRows] = useState<EditableRow[]>([]);
  const [dirty, setDirty] = useState(false);

  // Sync rows from server data
  useEffect(() => {
    if (data?.fields) {
      setRows(
        data.fields.map((f, i) => ({
          key: f.id,
          fieldName: f.fieldName,
          displayName: f.displayName,
          description: f.description ?? "",
          examples: f.examples ?? "",
          dataType: f.dataType,
          required: f.required,
          sortOrder: f.sortOrder ?? i + 1,
        })),
      );
      setDirty(false);
    }
  }, [data]);

  const updateRow = useCallback(
    (key: string, field: keyof EditableRow, value: string | boolean) => {
      setRows((prev) =>
        prev.map((r) => {
          if (r.key !== key) return r;
          const updated = { ...r, [field]: value };
          // Auto-generate fieldName from displayName
          if (field === "displayName" && typeof value === "string") {
            updated.fieldName = toSnakeCase(value);
          }
          return updated;
        }),
      );
      setDirty(true);
    },
    [],
  );

  const addRow = useCallback(() => {
    const nextOrder = rows.length + 1;
    setRows((prev) => [
      ...prev,
      {
        key: `new-${Date.now()}`,
        fieldName: "",
        displayName: "",
        description: "",
        examples: "",
        dataType: "string",
        required: false,
        sortOrder: nextOrder,
      },
    ]);
    setDirty(true);
  }, [rows.length]);

  const removeRow = useCallback((key: string) => {
    setRows((prev) => prev.filter((r) => r.key !== key));
    setDirty(true);
  }, []);

  const handleSave = useCallback(() => {
    const fields: FieldCreateRequest[] = rows
      .filter((r) => r.displayName.trim() !== "")
      .map((r, i) => ({
        fieldName: r.fieldName || toSnakeCase(r.displayName),
        displayName: r.displayName,
        description: r.description || undefined,
        examples: r.examples || undefined,
        dataType: r.dataType,
        required: r.required,
        sortOrder: i + 1,
      }));
    createMutation.mutate(
      { categoryId, fields },
      { onSuccess: () => setDirty(false) },
    );
  }, [rows, categoryId, createMutation]);

  if (isLoading) {
    return <div className="text-gray-500">Loading fields...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-md font-semibold text-gray-700">{categoryName}</h3>
        <div className="flex items-center gap-3">
          {dirty && (
            <button
              onClick={handleSave}
              disabled={createMutation.isPending}
              className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-500 disabled:opacity-50"
              type="button"
            >
              {createMutation.isPending ? "Saving..." : "Save Changes"}
            </button>
          )}
          <button
            onClick={addRow}
            className="px-3 py-1.5 text-sm font-medium text-primary-600 border border-primary-300 rounded-md hover:bg-primary-50"
            type="button"
          >
            + Add Field
          </button>
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-gray-400">
          No fields defined yet. Click &quot;+ Add Field&quot; to get started.
        </p>
      ) : (
        <div className="overflow-hidden border border-gray-200 rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">
                  Field Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Examples
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">
                  Type
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                  Req
                </th>
                <th className="px-4 py-3 w-12" />
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rows.map((row) => (
                <tr key={row.key} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={row.displayName}
                      onChange={(e) =>
                        updateRow(row.key, "displayName", e.target.value)
                      }
                      placeholder="Field name..."
                      className="w-full text-sm border-0 bg-transparent focus:ring-1 focus:ring-primary-400 rounded px-1 py-1 -ml-1"
                    />
                    <div className="text-xs text-gray-400 px-1">
                      {row.fieldName}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={row.description}
                      onChange={(e) =>
                        updateRow(row.key, "description", e.target.value)
                      }
                      placeholder="Description..."
                      className="w-full text-sm border-0 bg-transparent focus:ring-1 focus:ring-primary-400 rounded px-1 py-1 -ml-1"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <input
                      type="text"
                      value={row.examples}
                      onChange={(e) =>
                        updateRow(row.key, "examples", e.target.value)
                      }
                      placeholder="e.g. value1; value2"
                      className="w-full text-sm border-0 bg-transparent focus:ring-1 focus:ring-primary-400 rounded px-1 py-1 -ml-1"
                    />
                  </td>
                  <td className="px-4 py-2">
                    <select
                      value={row.dataType}
                      onChange={(e) =>
                        updateRow(row.key, "dataType", e.target.value)
                      }
                      className="w-full text-sm border-0 bg-transparent focus:ring-1 focus:ring-primary-400 rounded px-1 py-1"
                    >
                      {DATA_TYPES.map((t) => (
                        <option key={t} value={t}>
                          {t}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-2 text-center">
                    <input
                      type="checkbox"
                      checked={row.required}
                      onChange={(e) =>
                        updateRow(row.key, "required", e.target.checked)
                      }
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </td>
                  <td className="px-4 py-2 text-center">
                    <button
                      onClick={() => removeRow(row.key)}
                      className="text-gray-400 hover:text-red-600 transition-colors"
                      title="Remove field"
                      type="button"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
