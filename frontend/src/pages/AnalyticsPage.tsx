/** Analytics page — natural language queries over application data. */

import { useState } from "react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { submitAnalyticsQuery } from "../lib/api/analytics";
import type { AnalyticsQueryResponse, AnalyticsData, ChartConfig } from "../types/analytics";

const COLORS = ["#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#ec4899", "#64748b"];

const SUGGESTED_QUERIES = [
  { label: "Document Pipeline", query: "How many documents are in each status?" },
  { label: "Category Breakdown", query: "Show document distribution by category" },
  { label: "Activity Timeline", query: "Show system activity over time" },
  { label: "Extraction Quality", query: "What is the extraction confidence distribution?" },
  { label: "Recent RAG Queries", query: "Show recent RAG queries and answers" },
  { label: "Bulk Jobs", query: "Which bulk jobs processed the most documents?" },
];

function toChartData(data: AnalyticsData): Record<string, unknown>[] {
  return data.rows.map((row) => {
    const obj: Record<string, unknown> = {};
    data.columns.forEach((col, i) => { obj[col] = row[i]; });
    return obj;
  });
}

export default function AnalyticsPage() {
  const [question, setQuestion] = useState("");
  const [activeQuestion, setActiveQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AnalyticsQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleQuery = async (q?: string) => {
    const queryText = q || question;
    if (!queryText.trim()) return;
    setActiveQuestion(queryText.trim());
    setIsLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await submitAnalyticsQuery(queryText.trim());
      setResult(res);
      if (res.error) setError(res.error);
    } catch {
      setError("Failed to execute analytics query.");
    } finally {
      setIsLoading(false);
    }
  };

  const showLanding = !result && !isLoading && !error;

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header bar */}
      <div className="bg-white border-b border-gray-200 px-8 py-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-50 rounded-lg">
            <svg className="w-5 h-5 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Analytics</h1>
            <p className="text-xs text-gray-500">Ask questions about your data in natural language</p>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        {/* Landing state — centered search */}
        {showLanding && (
          <div className="flex flex-col items-center justify-center min-h-[500px] px-8">
            <div className="text-center mb-8">
              <div className="inline-flex p-4 bg-primary-50 rounded-2xl mb-4">
                <svg className="w-10 h-10 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-800 mb-1">What would you like to know?</h2>
              <p className="text-sm text-gray-500">Ask a question and get instant charts and insights from your data</p>
            </div>

            {/* Search bar */}
            <div className="w-full max-w-2xl mb-6">
              <SearchBar
                value={question}
                onChange={setQuestion}
                onSubmit={() => handleQuery()}
                isLoading={isLoading}
              />
            </div>

            {/* Suggested queries */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-w-2xl">
              {SUGGESTED_QUERIES.map((sq) => (
                <button
                  key={sq.label}
                  onClick={() => { setQuestion(sq.query); handleQuery(sq.query); }}
                  className="flex items-center gap-2 px-4 py-3 text-left text-sm text-gray-600 bg-white border border-gray-200 rounded-xl hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700 transition-all shadow-sm"
                >
                  <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <span>{sq.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Active state — search bar at top + results */}
        {!showLanding && (
          <div className="px-8 py-6 space-y-5">
            {/* Compact search bar */}
            <SearchBar
              value={question}
              onChange={setQuestion}
              onSubmit={() => handleQuery()}
              isLoading={isLoading}
            />

            {/* Loading */}
            {isLoading && (
              <div className="flex items-center justify-center py-16">
                <div className="flex flex-col items-center gap-3">
                  <div className="w-8 h-8 border-3 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
                  <p className="text-sm text-gray-500">Analyzing your data...</p>
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="flex items-start gap-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-4">
                <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>{error}</div>
              </div>
            )}

            {/* Results */}
            {result && !error && (
              <div className="space-y-5">
                {/* Question badge */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-primary-600 bg-primary-50 px-3 py-1 rounded-full">
                    Q: {activeQuestion}
                  </span>
                  <span className="text-xs text-gray-400">
                    {result.data.rows.length} rows
                  </span>
                </div>

                {/* Explanation card */}
                <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
                  <div className="flex items-start gap-3">
                    <div className="p-1.5 bg-green-50 rounded-lg mt-0.5">
                      <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">{result.explanation}</p>
                  </div>
                </div>

                {/* Chart card */}
                {result.data.rows.length > 0 && (
                  <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100">
                      <h3 className="text-sm font-semibold text-gray-900">{result.chart.title}</h3>
                    </div>
                    <div className="p-6">
                      <ChartRenderer data={result.data} chart={result.chart} />
                    </div>
                  </div>
                )}

                {/* SQL collapse */}
                <details className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                  <summary className="px-5 py-3 text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-50 transition-colors select-none">
                    View generated SQL
                  </summary>
                  <div className="border-t border-gray-100">
                    <pre className="px-5 py-4 text-xs text-gray-300 bg-gray-900 overflow-x-auto font-mono leading-relaxed">
                      {result.sql}
                    </pre>
                  </div>
                </details>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SearchBar({
  value, onChange, onSubmit, isLoading,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}) {
  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
        <svg className="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        placeholder="Ask about your data..."
        className="w-full py-3.5 pl-12 pr-28 text-base rounded-xl border border-gray-300 bg-white shadow-sm hover:shadow-md focus:shadow-md focus:border-primary-400 focus:ring-1 focus:ring-primary-400 transition-all"
      />
      <div className="absolute inset-y-0 right-0 pr-2 flex items-center">
        <button
          onClick={onSubmit}
          disabled={isLoading || !value.trim()}
          className="px-5 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing
            </span>
          ) : "Ask"}
        </button>
      </div>
    </div>
  );
}

function ChartRenderer({ data, chart }: { data: AnalyticsData; chart: ChartConfig }) {
  const chartData = toChartData(data);

  if (chart.chartType === "table" || chartData.length === 0) {
    return <DataTable data={data} />;
  }

  if (chart.chartType === "bar") {
    const xKey = chart.xKey || data.columns[0];
    const yKey = chart.yKey || data.columns[1];
    return (
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} />
          <Tooltip
            contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)" }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey={yKey} fill="#6366f1" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (chart.chartType === "line") {
    const xKey = chart.xKey || data.columns[0];
    const yKey = chart.yKey || data.columns[1];
    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey={xKey} tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} />
          <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={{ stroke: "#e2e8f0" }} />
          <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line type="monotone" dataKey={yKey} stroke="#6366f1" strokeWidth={2.5} dot={{ r: 5, fill: "#6366f1" }} activeDot={{ r: 7 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chart.chartType === "pie") {
    const nameKey = chart.nameKey || data.columns[0];
    const valueKey = chart.valueKey || data.columns[1];
    return (
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            outerRadius={140}
            innerRadius={60}
            paddingAngle={2}
            label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
            labelLine={{ stroke: "#94a3b8", strokeWidth: 1 }}
          >
            {chartData.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return <DataTable data={data} />;
}

function DataTable({ data }: { data: AnalyticsData }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full text-sm divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {data.columns.map((col) => (
              <th key={col} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {col.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {data.rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="px-5 py-3 text-gray-700">
                  {cell != null ? String(cell) : <span className="text-gray-300">-</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
