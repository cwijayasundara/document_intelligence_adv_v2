/** Extraction field editor with add/edit/reorder capabilities. */

import { useState } from "react";
import { useCreateFields, useExtractionFields } from "../../hooks/useExtractionFields";
import type { ExtractionField, FieldCreateRequest } from "../../types/config";
import FieldFormModal from "./FieldFormModal";

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
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingField, setEditingField] = useState<ExtractionField | null>(
    null,
  );

  const fields = data?.fields ?? [];

  const handleAddField = (fieldData: FieldCreateRequest) => {
    const allFields = [
      ...fields.map((f) => ({
        fieldName: f.fieldName,
        displayName: f.displayName,
        description: f.description ?? undefined,
        examples: f.examples ?? undefined,
        dataType: f.dataType,
        required: f.required,
        sortOrder: f.sortOrder,
      })),
      fieldData,
    ];
    createMutation.mutate({ categoryId, fields: allFields });
  };

  if (isLoading) {
    return <div className="text-gray-500">Loading fields...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-md font-semibold text-gray-700">{categoryName}</h3>
        <button
          onClick={() => {
            setEditingField(null);
            setIsModalOpen(true);
          }}
          className="text-sm text-primary-600 hover:text-primary-800 font-medium"
          type="button"
        >
          + Add Field
        </button>
      </div>
      {fields.length === 0 ? (
        <p className="text-sm text-gray-400">No fields defined yet.</p>
      ) : (
        <div className="space-y-2">
          {fields.map((field) => (
            <div
              key={field.id}
              className="flex items-center justify-between p-3 border rounded-lg bg-white"
              data-testid="field-row"
            >
              <div>
                <span className="text-sm font-medium text-gray-900">
                  {field.displayName}
                </span>
                <span className="ml-2 text-xs text-gray-400">
                  ({field.fieldName})
                </span>
                <span className="ml-2 text-xs text-gray-500">
                  {field.dataType}
                </span>
                {field.required && (
                  <span className="ml-2 text-xs text-red-500">Required</span>
                )}
              </div>
              <button
                onClick={() => {
                  setEditingField(field);
                  setIsModalOpen(true);
                }}
                className="text-sm text-primary-600 hover:text-primary-800"
                type="button"
              >
                Edit
              </button>
            </div>
          ))}
        </div>
      )}
      <FieldFormModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingField(null);
        }}
        onSubmit={handleAddField}
        field={editingField}
        nextSortOrder={fields.length + 1}
      />
    </div>
  );
}
