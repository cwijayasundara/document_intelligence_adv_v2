import { Route, Routes } from "react-router-dom";
import Layout from "./components/ui/Layout";

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
        <Route index element={<PlaceholderPage title="Dashboard" />} />
        <Route
          path="upload"
          element={<PlaceholderPage title="Upload Documents" />}
        />
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
        <Route
          path="config/categories"
          element={<PlaceholderPage title="Categories" />}
        />
        <Route
          path="config/extraction-fields"
          element={<PlaceholderPage title="Extraction Fields" />}
        />
        <Route
          path="bulk"
          element={<PlaceholderPage title="Bulk Processing" />}
        />
      </Route>
    </Routes>
  );
}
