/** Bulk processing page with upload zone, job list, and expandable details. */

import { useCallback } from "react";
import PageHeader from "../components/ui/PageHeader";
import BulkUploadZone from "../components/bulk/BulkUploadZone";
import BulkJobList from "../components/bulk/BulkJobList";
import { useBulkJobs, useUploadBulk } from "../hooks/useBulk";

export default function BulkPage() {
  const { data, isLoading } = useBulkJobs();
  const uploadMutation = useUploadBulk();

  const handleFilesAccepted = useCallback(
    (files: File[]) => {
      uploadMutation.mutate(files);
    },
    [uploadMutation],
  );

  return (
    <div>
      <PageHeader
        title="Bulk Processing"
        description="Upload multiple documents for batch processing through the full pipeline."
      />
      <div className="p-8 max-w-4xl mx-auto space-y-8">
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            New Bulk Job
          </h2>
          <BulkUploadZone
            onFilesAccepted={handleFilesAccepted}
            disabled={uploadMutation.isPending}
          />
          {uploadMutation.isPending && (
            <p className="mt-3 text-sm text-gray-500">Uploading files...</p>
          )}
          {uploadMutation.isError && (
            <p className="mt-3 text-sm text-red-600">
              Upload failed:{" "}
              {uploadMutation.error instanceof Error
                ? uploadMutation.error.message
                : "Unknown error"}
            </p>
          )}
          {uploadMutation.isSuccess && (
            <p className="mt-3 text-sm text-green-600">
              Bulk job created with {uploadMutation.data.totalDocuments}{" "}
              documents.
            </p>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Bulk Jobs
          </h2>
          {isLoading ? (
            <p className="text-sm text-gray-500">Loading jobs...</p>
          ) : (
            <BulkJobList jobs={data?.jobs ?? []} />
          )}
        </section>
      </div>
    </div>
  );
}
