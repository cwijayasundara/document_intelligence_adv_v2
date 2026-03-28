/** Category management page. */

import CategoryManager from "../components/config/CategoryManager";
import PageHeader from "../components/ui/PageHeader";

export default function CategoriesPage() {
  return (
    <div>
      <PageHeader
        title="Categories"
        description="Manage document categories and classification criteria."
      />
      <div className="p-8">
        <CategoryManager />
      </div>
    </div>
  );
}
