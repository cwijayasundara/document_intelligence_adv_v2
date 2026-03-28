/** Inline editor for extraction field values. */

import { useCallback, useState } from "react";

interface InlineEditProps {
  value: string;
  onSave: (newValue: string) => void;
  disabled?: boolean;
}

export default function InlineEdit({
  value,
  onSave,
  disabled = false,
}: InlineEditProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);

  const handleEdit = useCallback(() => {
    setEditValue(value);
    setIsEditing(true);
  }, [value]);

  const handleSave = useCallback(() => {
    onSave(editValue);
    setIsEditing(false);
  }, [editValue, onSave]);

  const handleCancel = useCallback(() => {
    setEditValue(value);
    setIsEditing(false);
  }, [value]);

  if (isEditing) {
    return (
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          data-testid="inline-edit-input"
          autoFocus
        />
        <button
          onClick={handleSave}
          className="px-2 py-1 text-xs font-medium text-white bg-green-600 rounded hover:bg-green-700"
          data-testid="inline-edit-save"
        >
          Save
        </button>
        <button
          onClick={handleCancel}
          className="px-2 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
          data-testid="inline-edit-cancel"
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-900" data-testid="field-value">
        {value}
      </span>
      <button
        onClick={handleEdit}
        disabled={disabled}
        className="px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-800 disabled:opacity-50"
        data-testid="inline-edit-button"
      >
        Edit
      </button>
    </div>
  );
}
