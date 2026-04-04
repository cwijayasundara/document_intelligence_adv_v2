/** TanStack Query hook for audit trail. */

import { useQuery } from "@tanstack/react-query";
import { fetchAuditTrail } from "../lib/api/audit";
import type { AuditTrailResponse } from "../types/audit";

export function useAuditTrail(params?: {
  eventType?: string;
  entityType?: string;
  documentId?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery<AuditTrailResponse>({
    queryKey: ["audit-trail", params],
    queryFn: () => fetchAuditTrail(params),
  });
}
