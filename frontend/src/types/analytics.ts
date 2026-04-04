/** Types for data analytics agent. */

export interface ChartConfig {
  chartType: "bar" | "line" | "pie" | "table";
  title: string;
  xKey: string;
  yKey: string;
  nameKey: string;
  valueKey: string;
}

export interface AnalyticsData {
  columns: string[];
  rows: (string | number | null)[][];
}

export interface AnalyticsQueryResponse {
  sql: string;
  data: AnalyticsData;
  chart: ChartConfig;
  explanation: string;
  error: string | null;
}
