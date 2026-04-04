/** Generate a persistent session ID per browser tab. */

import { useMemo } from "react";

let _tabSessionId: string | null = null;

function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

/** Returns a stable session ID that persists for the lifetime of the tab. */
export function useSessionId(): string {
  return useMemo(() => {
    if (!_tabSessionId) {
      _tabSessionId = generateSessionId();
    }
    return _tabSessionId;
  }, []);
}
