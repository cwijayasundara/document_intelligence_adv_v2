/** Category card list with inline edit form below. */

import { useState } from "react";
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from "../../hooks/useCategories";
import type { Category, CategoryCreateRequest } from "../../types/config";
import CategoryForm from "./CategoryForm";

export default function CategoryManager() {
  const { data, isLoading } = useCategories();
  const createMutation = useCreateCategory();
  const updateMutation = useUpdateCategory();
  const deleteMutation = useDeleteCategory();

  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const categories = data?.categories ?? [];

  const handleCreate = (formData: CategoryCreateRequest) => {
    createMutation.mutate(formData);
    setIsCreating(false);
  };

  const handleEdit = (category: Category) => {
    setIsCreating(false);
    setEditingCategory(category);
  };

  const handleUpdate = (formData: CategoryCreateRequest) => {
    if (editingCategory) {
      updateMutation.mutate({ id: editingCategory.id, data: formData });
    }
    setEditingCategory(null);
  };

  const handleDelete = (id: string) => {
    if (window.confirm("Are you sure you want to delete this category?")) {
      deleteMutation.mutate(id);
      if (editingCategory?.id === id) {
        setEditingCategory(null);
      }
    }
  };

  const handleCancel = () => {
    setEditingCategory(null);
    setIsCreating(false);
  };

  const handleStartCreate = () => {
    setEditingCategory(null);
    setIsCreating(true);
  };

  if (isLoading) {
    return <div className="text-gray-500">Loading categories...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={handleStartCreate}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-500"
          type="button"
        >
          Add Category
        </button>
      </div>

      {/* Category cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((cat) => (
          <div
            key={cat.id}
            className={`border rounded-lg p-4 bg-white shadow-sm transition-colors cursor-pointer ${
              editingCategory?.id === cat.id
                ? "border-primary-400 ring-2 ring-primary-100"
                : "border-gray-200 hover:border-gray-300"
            }`}
            data-testid="category-card"
            onClick={() => handleEdit(cat)}
          >
            <h3 className="text-lg font-semibold text-gray-900">{cat.name}</h3>
            {cat.description && (
              <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                {cat.description}
              </p>
            )}
            {cat.classificationCriteria && (
              <p className="mt-2 text-xs text-gray-400 line-clamp-2">
                <span className="font-medium text-gray-500">Criteria:</span>{" "}
                {cat.classificationCriteria}
              </p>
            )}
            <div className="mt-4 flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleEdit(cat);
                }}
                className="text-sm text-primary-600 hover:text-primary-800"
                type="button"
              >
                Edit
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(cat.id);
                }}
                className="text-sm text-red-600 hover:text-red-800"
                type="button"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Inline edit/create form below the cards */}
      {(editingCategory || isCreating) && (
        <div className="border border-gray-200 rounded-lg bg-white shadow-sm p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">
            {editingCategory ? `Edit: ${editingCategory.name}` : "New Category"}
          </h3>
          <CategoryForm
            category={editingCategory}
            onSubmit={editingCategory ? handleUpdate : handleCreate}
            onCancel={handleCancel}
          />
        </div>
      )}
    </div>
  );
}
