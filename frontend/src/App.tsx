import { Route, Routes } from "react-router-dom";
import Layout from "./components/ui/Layout";
import { useEventStream } from "./hooks/useEventStream";
import AnalyticsPage from "./pages/AnalyticsPage";
import BulkPage from "./pages/BulkPage";
import InsightsPage from "./pages/InsightsPage";
import CategoriesPage from "./pages/CategoriesPage";
import ChatPage from "./pages/ChatPage";
import ClassifyPage from "./pages/ClassifyPage";
import DashboardPage from "./pages/DashboardPage";
import EvalRunDetailPage from "./pages/EvalRunDetailPage";
import EvalTrendsPage from "./pages/EvalTrendsPage";
import EvalsPage from "./pages/EvalsPage";
import ExtractionFieldsPage from "./pages/ExtractionFieldsPage";
import ExtractionPage from "./pages/ExtractionPage";
import ParsePage from "./pages/ParsePage";
import SummaryPage from "./pages/SummaryPage";
import UploadPage from "./pages/UploadPage";

export default function App() {
  useEventStream();

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="documents/:id/parse" element={<ParsePage />} />
        <Route path="documents/:id/classify" element={<ClassifyPage />} />
        <Route path="documents/:id/extract" element={<ExtractionPage />} />
        <Route path="documents/:id/summary" element={<SummaryPage />} />
        <Route path="documents/:id/chat" element={<ChatPage />} />
        <Route path="config/categories" element={<CategoriesPage />} />
        <Route
          path="config/extraction-fields"
          element={<ExtractionFieldsPage />}
        />
        <Route path="bulk" element={<BulkPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="evals" element={<EvalsPage />} />
        <Route path="evals/trends" element={<EvalTrendsPage />} />
        <Route path="evals/runs/:id" element={<EvalRunDetailPage />} />
      </Route>
    </Routes>
  );
}
