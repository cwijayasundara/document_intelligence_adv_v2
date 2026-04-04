/** API functions for audit trail endpoints. */

import type { AuditTrailResponse } from "../../types/audit";
import apiClient from "./client";

export async function fetchAuditTrail(params?: {
  eventType?: string;
  entityType?: string;
  documentId?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditTrailResponse> {
  const response = await apiClient.get("/audit/trail", { params });
  return response.data;
}
