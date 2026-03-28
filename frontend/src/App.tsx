import { Route, Routes } from "react-router-dom";
import Layout from "./components/ui/Layout";
import CategoriesPage from "./pages/CategoriesPage";
import DashboardPage from "./pages/DashboardPage";
import ExtractionFieldsPage from "./pages/ExtractionFieldsPage";
import UploadPage from "./pages/UploadPage";

/** Placeholder page component for routes not yet implemented. */
function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-heading font-semibold text-gray-900">
        {title}
      </h1>
      <p className="mt-2 text-gray-500">This page is coming soon.</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route
          path="documents/:id/parse"
          element={<PlaceholderPage title="Parse Document" />}
        />
        <Route
          path="documents/:id/classify"
          element={<PlaceholderPage title="Classify Document" />}
        />
        <Route
          path="documents/:id/extract"
          element={<PlaceholderPage title="Extract Fields" />}
        />
        <Route
          path="documents/:id/summary"
          element={<PlaceholderPage title="Document Summary" />}
        />
        <Route
          path="documents/:id/chat"
          element={<PlaceholderPage title="Chat with Document" />}
        />
        <Route path="config/categories" element={<CategoriesPage />} />
        <Route
          path="config/extraction-fields"
          element={<ExtractionFieldsPage />}
        />
        <Route
          path="bulk"
          element={<PlaceholderPage title="Bulk Processing" />}
        />
      </Route>
    </Routes>
  );
}
