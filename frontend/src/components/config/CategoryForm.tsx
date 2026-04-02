/** Inline form for creating/editing a category. */

import { useEffect, useState } from "react";
import type { Category, CategoryCreateRequest } from "../../types/config";

interface CategoryFormProps {
  category?: Category | null;
  onSubmit: (data: CategoryCreateRequest) => void;
  onCancel: () => void;
}

export default function CategoryForm({
  category,
  onSubmit,
  onCancel,
}: CategoryFormProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState("");

  useEffect(() => {
    if (category) {
      setName(category.name);
      setDescription(category.description ?? "");
      setCriteria(category.classificationCriteria ?? "");
    } else {
      setName("");
      setDescription("");
      setCriteria("");
    }
  }, [category]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name,
      description: description || undefined,
      classificationCriteria: criteria || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Name *
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Classification Criteria
        </label>
        <textarea
          value={criteria}
          onChange={(e) => setCriteria(e.target.value)}
          rows={5}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-500"
        >
          {category ? "Update" : "Create"}
        </button>
      </div>
    </form>
  );
}
