/** SSE hook that listens for real-time backend events and invalidates queries. */

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

const SSE_URL = "http://localhost:8000/api/v1/events/stream";

/** Map event types to query keys that should be invalidated. */
const EVENT_INVALIDATION_MAP: Record<string, string[][]> = {
  "document.uploaded": [["documents"]],
  "document.parsed": [["documents"]],
  "document.classified": [["documents"]],
  "document.extracted": [["documents"], ["extract"]],
  "document.summarized": [["documents"], ["summarize"]],
  "document.ingested": [["documents"]],
  "document.deleted": [["documents"]],
  "bulk.job_created": [["documents"], ["bulk-jobs"]],
  "bulk.job_completed": [["documents"], ["bulk-jobs"]],
  "bulk.job_failed": [["bulk-jobs"]],
  "rag.query": [["audit-trail"]],
};

/**
 * Connect to the backend SSE stream and auto-refresh UI when events arrive.
 * Call this once at the app root level.
 */
export function useEventStream() {
  const queryClient = useQueryClient();

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    function connect() {
      eventSource = new EventSource(SSE_URL);

      eventSource.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          const eventType: string = data.event_type || "";
          const keys = EVENT_INVALIDATION_MAP[eventType];
          if (keys) {
            for (const key of keys) {
              queryClient.invalidateQueries({ queryKey: key });
            }
          }
          // Always refresh audit trail for insights page
          queryClient.invalidateQueries({ queryKey: ["audit-trail"] });
        } catch {
          // Ignore parse errors from keepalive comments
        }
      };

      eventSource.onerror = () => {
        eventSource?.close();
        // Reconnect after 5 seconds
        reconnectTimer = setTimeout(connect, 5000);
      };
    }

    connect();

    return () => {
      eventSource?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [queryClient]);
}
