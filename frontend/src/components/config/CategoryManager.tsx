/** Category card list with CRUD actions. */

import { useState } from "react";
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from "../../hooks/useCategories";
import type { Category, CategoryCreateRequest } from "../../types/config";
import CategoryFormModal from "./CategoryFormModal";

export default function CategoryManager() {
  const { data, isLoading } = useCategories();
  const createMutation = useCreateCategory();
  const updateMutation = useUpdateCategory();
  const deleteMutation = useDeleteCategory();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);

  const categories = data?.categories ?? [];

  const handleCreate = (formData: CategoryCreateRequest) => {
    createMutation.mutate(formData);
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setIsModalOpen(true);
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
    }
  };

  if (isLoading) {
    return <div className="text-gray-500">Loading categories...</div>;
  }

  return (
    <div>
      <div className="flex justify-end mb-4">
        <button
          onClick={() => {
            setEditingCategory(null);
            setIsModalOpen(true);
          }}
          className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-500"
          type="button"
        >
          Add Category
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {categories.map((cat) => (
          <div
            key={cat.id}
            className="border rounded-lg p-4 bg-white shadow-sm"
            data-testid="category-card"
          >
            <h3 className="text-lg font-semibold text-gray-900">{cat.name}</h3>
            {cat.description && (
              <p className="mt-1 text-sm text-gray-500">{cat.description}</p>
            )}
            <div className="mt-4 flex gap-2">
              <button
                onClick={() => handleEdit(cat)}
                className="text-sm text-primary-600 hover:text-primary-800"
                type="button"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(cat.id)}
                className="text-sm text-red-600 hover:text-red-800"
                type="button"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      <CategoryFormModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setEditingCategory(null);
        }}
        onSubmit={editingCategory ? handleUpdate : handleCreate}
        category={editingCategory}
      />
    </div>
  );
}
