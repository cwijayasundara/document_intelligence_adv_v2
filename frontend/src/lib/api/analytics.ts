/** API functions for data analytics agent. */

import type { AnalyticsQueryResponse } from "../../types/analytics";
import apiClient from "./client";

export async function submitAnalyticsQuery(
  question: string,
  sessionId?: string,
): Promise<AnalyticsQueryResponse> {
  const response = await apiClient.post("/analytics/query", {
    question,
    sessionId,
  });
  return response.data;
}
