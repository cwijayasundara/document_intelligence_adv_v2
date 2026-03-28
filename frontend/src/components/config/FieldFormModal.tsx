/** Modal form for creating/editing extraction fields. */

import { useEffect, useState } from "react";
import type { ExtractionField, FieldCreateRequest } from "../../types/config";
import Modal from "../ui/Modal";

const DATA_TYPES = ["string", "number", "date", "currency", "percentage"];

interface FieldFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: FieldCreateRequest) => void;
  field?: ExtractionField | null;
  nextSortOrder: number;
}

export default function FieldFormModal({
  isOpen,
  onClose,
  onSubmit,
  field,
  nextSortOrder,
}: FieldFormModalProps) {
  const [fieldName, setFieldName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [description, setDescription] = useState("");
  const [examples, setExamples] = useState("");
  const [dataType, setDataType] = useState("string");
  const [required, setRequired] = useState(false);

  useEffect(() => {
    if (field) {
      setFieldName(field.fieldName);
      setDisplayName(field.displayName);
      setDescription(field.description ?? "");
      setExamples(field.examples ?? "");
      setDataType(field.dataType);
      setRequired(field.required);
    } else {
      setFieldName("");
      setDisplayName("");
      setDescription("");
      setExamples("");
      setDataType("string");
      setRequired(false);
    }
  }, [field, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      fieldName,
      displayName,
      description: description || undefined,
      examples: examples || undefined,
      dataType,
      required,
      sortOrder: field?.sortOrder ?? nextSortOrder,
    });
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={field ? "Edit Field" : "Add Field"}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Field Name *
            </label>
            <input
              type="text"
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Display Name *
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Description
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Examples
          </label>
          <textarea
            value={examples}
            onChange={(e) => setExamples(e.target.value)}
            rows={2}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Data Type
            </label>
            <select
              value={dataType}
              onChange={(e) => setDataType(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm sm:text-sm"
            >
              {DATA_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={required}
                onChange={(e) => setRequired(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Required</span>
            </label>
          </div>
        </div>
        <div className="flex justify-end gap-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-500"
          >
            {field ? "Update" : "Add"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
