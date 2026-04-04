/** Types for audit trail and insights. */

export interface AuditLogItem {
  id: string;
  eventType: string;
  entityType: string;
  entityId: string | null;
  documentId: string | null;
  fileName: string | null;
  details: Record<string, unknown> | null;
  error: string | null;
  createdAt: string;
}

export interface AuditTrailResponse {
  events: AuditLogItem[];
  total: number;
}
