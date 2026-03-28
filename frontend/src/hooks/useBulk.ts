/** TanStack Query hooks for bulk processing operations. */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getBulkJobDetail,
  listBulkJobs,
  uploadBulkFiles,
} from "../lib/api/bulk";
import type { BulkJobDetail, BulkJobListResponse } from "../types/bulk";

const BULK_JOBS_KEY = ["bulk-jobs"] as const;

/** Fetch all bulk jobs with auto-refresh while any job is processing. */
export function useBulkJobs() {
  return useQuery<BulkJobListResponse>({
    queryKey: [...BULK_JOBS_KEY],
    queryFn: () => listBulkJobs(),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const hasProcessing = data.jobs.some(
        (job) => job.status === "processing" || job.status === "pending",
      );
      return hasProcessing ? 5000 : false;
    },
  });
}

/** Fetch a single bulk job with per-document details. */
export function useBulkJobDetail(jobId: string | null) {
  return useQuery<BulkJobDetail>({
    queryKey: [...BULK_JOBS_KEY, jobId],
    queryFn: () => getBulkJobDetail(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const isActive =
        data.status === "processing" || data.status === "pending";
      return isActive ? 5000 : false;
    },
  });
}

/** Upload multiple files as a bulk job. */
export function useUploadBulk() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (files: File[]) => uploadBulkFiles(files),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BULK_JOBS_KEY });
    },
  });
}
