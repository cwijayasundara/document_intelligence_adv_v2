/** Extraction fields management page grouped by category. */

import ExtractionFieldEditor from "../components/config/ExtractionFieldEditor";
import PageHeader from "../components/ui/PageHeader";
import { useCategories } from "../hooks/useCategories";

export default function ExtractionFieldsPage() {
  const { data, isLoading } = useCategories();
  const categories = data?.categories ?? [];

  return (
    <div>
      <PageHeader
        title="Extraction Fields"
        description="Define extraction fields for each document category."
      />
      <div className="p-8 space-y-8">
        {isLoading && (
          <div className="text-gray-500">Loading categories...</div>
        )}
        {!isLoading && categories.length === 0 && (
          <div className="text-gray-500">
            No categories found. Create categories first.
          </div>
        )}
        {categories.map((cat) => (
          <div key={cat.id} className="border rounded-lg p-6 bg-white">
            <ExtractionFieldEditor
              categoryId={cat.id}
              categoryName={cat.name}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
