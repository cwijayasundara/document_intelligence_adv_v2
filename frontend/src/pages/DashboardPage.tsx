/** Dashboard page showing document list with status badges. */

import { Link } from "react-router-dom";
import DocumentList from "../components/documents/DocumentList";
import EmptyState from "../components/ui/EmptyState";
import PageHeader from "../components/ui/PageHeader";
import { useDocuments } from "../hooks/useDocuments";

export default function DashboardPage() {
  const { data, isLoading, error } = useDocuments();

  const documents = data?.documents ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={total > 0 ? `${total} documents` : undefined}
        actions={
          <Link
            to="/upload"
            className="inline-flex items-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500"
          >
            Upload Document
          </Link>
        }
      />
      <div className="p-8">
        {isLoading && (
          <div className="text-center py-8 text-gray-500">
            Loading documents...
          </div>
        )}
        {error && (
          <div className="text-center py-8 text-red-500">
            Failed to load documents. Please try again.
          </div>
        )}
        {!isLoading && !error && documents.length === 0 && (
          <EmptyState
            title="No documents yet"
            description="Upload your first document to get started with analysis."
            actionLabel="Upload Document"
            actionTo="/upload"
          />
        )}
        {!isLoading && !error && documents.length > 0 && (
          <DocumentList documents={documents} />
        )}
      </div>
    </div>
  );
}
