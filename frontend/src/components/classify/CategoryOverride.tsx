/** Dropdown to override the detected document category. */

import type { CategoryOption } from "../../types/classify";

interface CategoryOverrideProps {
  categories: CategoryOption[];
  selectedCategoryId: string | null;
  onCategoryChange: (categoryId: string) => void;
  disabled?: boolean;
}

export default function CategoryOverride({
  categories,
  selectedCategoryId,
  onCategoryChange,
  disabled = false,
}: CategoryOverrideProps) {
  return (
    <div className="flex items-center gap-3">
      <label
        htmlFor="category-override"
        className="text-sm font-medium text-gray-700"
      >
        Override Category:
      </label>
      <select
        id="category-override"
        value={selectedCategoryId ?? ""}
        onChange={(e) => onCategoryChange(e.target.value)}
        disabled={disabled}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
        data-testid="category-override-select"
      >
        <option value="" disabled>
          Select a category
        </option>
        {categories.map((cat) => (
          <option key={cat.id} value={cat.id}>
            {cat.name}
          </option>
        ))}
      </select>
    </div>
  );
}
