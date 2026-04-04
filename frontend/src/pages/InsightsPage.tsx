/** Insights page — system activity dashboard and audit trail. */

import { useMemo, useState } from "react";
import PageHeader from "../components/ui/PageHeader";
import { useAuditTrail } from "../hooks/useAudit";
import type { AuditLogItem } from "../types/audit";

const EVENT_TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Uploads", value: "document.uploaded" },
  { label: "Parsed", value: "document.parsed" },
  { label: "Classified", value: "document.classified" },
  { label: "Extracted", value: "document.extracted" },
  { label: "Summarized", value: "document.summarized" },
  { label: "Ingested", value: "document.ingested" },
  { label: "Deleted", value: "document.deleted" },
  { label: "Bulk Jobs", value: "bulk." },
  { label: "RAG Queries", value: "rag.query" },
];

const EVENT_ICONS: Record<string, { icon: string; color: string }> = {
  "document.uploaded": { icon: "arrow-up", color: "text-blue-600 bg-blue-50" },
  "document.parsed": { icon: "doc", color: "text-cyan-600 bg-cyan-50" },
  "document.classified": { icon: "tag", color: "text-indigo-600 bg-indigo-50" },
  "document.extracted": { icon: "table", color: "text-amber-600 bg-amber-50" },
  "document.summarized": { icon: "lines", color: "text-purple-600 bg-purple-50" },
  "document.ingested": { icon: "db", color: "text-teal-600 bg-teal-50" },
  "document.deleted": { icon: "trash", color: "text-red-600 bg-red-50" },
  "bulk.job_created": { icon: "stack", color: "text-blue-600 bg-blue-50" },
  "bulk.job_completed": { icon: "check", color: "text-green-600 bg-green-50" },
  "bulk.job_failed": { icon: "x", color: "text-red-600 bg-red-50" },
  "rag.query": { icon: "search", color: "text-primary-600 bg-primary-50" },
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function getEventSummary(event: AuditLogItem): string {
  const d = event.details || {};
  switch (event.eventType) {
    case "document.uploaded":
      return `${d.file_type || ""}  ${d.file_size ? `${((d.file_size as number) / 1024).toFixed(0)} KB` : ""}${d.duplicate ? " (duplicate)" : ""}`;
    case "document.parsed":
      return `${d.confidence_pct ? `${d.confidence_pct}%` : ""} ${d.skipped ? "(cached)" : ""}`;
    case "document.classified":
      return `${d.category || ""} ${d.confidence ? `(${d.confidence}%)` : ""}`;
    case "document.extracted":
      return `${d.fields_count || 0} fields${d.review_count ? `, ${d.review_count} need review` : ""}`;
    case "document.summarized":
      return `${d.topics || 0} topics${d.cached ? " (cached)" : ""}`;
    case "document.ingested":
      return `${d.chunks_created || 0} chunks`;
    case "bulk.job_created":
      return `${d.total_documents || 0} documents`;
    case "bulk.job_completed":
    case "bulk.job_failed":
      return `${d.processed || 0} processed, ${d.failed || 0} failed`;
    case "rag.query":
      return `"${(d.query as string) || ""}"`;
    default:
      return "";
  }
}

export default function InsightsPage() {
  const [filter, setFilter] = useState("");
  const { data, isLoading } = useAuditTrail({
    eventType: filter.endsWith(".") ? undefined : filter || undefined,
    limit: 100,
  });

  const events = data?.events ?? [];

  // Filter bulk events client-side when "bulk." prefix selected
  const filtered = useMemo(() => {
    if (filter.endsWith(".")) {
      return events.filter((e) => e.eventType.startsWith(filter));
    }
    return events;
  }, [events, filter]);

  // Compute stat counts from all events
  const stats = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const e of events) {
      counts[e.eventType] = (counts[e.eventType] || 0) + 1;
    }
    return counts;
  }, [events]);

  return (
    <div>
      <PageHeader
        title="Insights"
        description="System activity and audit trail"
      />
      <div className="p-8 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard label="Uploads" count={stats["document.uploaded"] || 0} color="bg-blue-500" />
          <StatCard label="Parsed" count={stats["document.parsed"] || 0} color="bg-cyan-500" />
          <StatCard label="Classified" count={stats["document.classified"] || 0} color="bg-indigo-500" />
          <StatCard label="Extracted" count={stats["document.extracted"] || 0} color="bg-amber-500" />
          <StatCard label="Ingested" count={stats["document.ingested"] || 0} color="bg-teal-500" />
          <StatCard label="RAG Queries" count={stats["rag.query"] || 0} color="bg-primary-500" />
        </div>

        {/* Activity timeline */}
        <div className="border border-gray-200 rounded-lg bg-white shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 bg-gray-50 border-b border-gray-200">
            <h3 className="text-sm font-semibold text-gray-900">
              Activity Timeline
            </h3>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="text-xs rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              {EVENT_TYPE_FILTERS.map((f) => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
          </div>

          {isLoading && (
            <div className="px-5 py-8 text-center text-sm text-gray-400">Loading activity...</div>
          )}

          {!isLoading && filtered.length === 0 && (
            <div className="px-5 py-8 text-center text-sm text-gray-400">
              No audit events recorded yet.
            </div>
          )}

          {!isLoading && filtered.length > 0 && (
            <div className="divide-y divide-gray-100">
              {filtered.map((event) => (
                <ActivityRow key={event.id} event={event} />
              ))}
            </div>
          )}

          {data && data.total > filtered.length && (
            <div className="px-5 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 text-center">
              Showing {filtered.length} of {data.total} events
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="text-2xl font-bold text-gray-900">{count}</div>
      <div className="flex items-center gap-1.5 mt-1">
        <div className={`w-2 h-2 rounded-full ${color}`} />
        <span className="text-xs text-gray-500">{label}</span>
      </div>
    </div>
  );
}

function ActivityRow({ event }: { event: AuditLogItem }) {
  const [expanded, setExpanded] = useState(false);
  const style = EVENT_ICONS[event.eventType] || { icon: "dot", color: "text-gray-500 bg-gray-50" };
  const summary = getEventSummary(event);
  const d = event.details || {};
  const hasDetails = event.eventType === "rag.query" || Object.keys(d).length > 2;

  return (
    <div
      className={`px-5 py-3 hover:bg-gray-50 transition-colors ${hasDetails ? "cursor-pointer" : ""}`}
      onClick={() => hasDetails && setExpanded(!expanded)}
    >
      <div className="flex items-start gap-3">
        <div className={`mt-0.5 p-1.5 rounded-md ${style.color}`}>
          <EventIcon type={style.icon} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900">
              {event.eventType}
            </span>
            {event.fileName && (
              <span className="text-xs text-gray-500 truncate max-w-[200px]" title={event.fileName}>
                {event.fileName}
              </span>
            )}
            {(d.user as string) && (
              <span className="text-xs text-gray-400">by {d.user as string}</span>
            )}
          </div>
          {summary && (
            <p className="text-xs text-gray-500 mt-0.5">{summary}</p>
          )}
          {event.error && (
            <p className="text-xs text-red-500 mt-0.5 truncate" title={event.error}>
              {event.error}
            </p>
          )}
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {formatTime(event.createdAt)}
        </span>
      </div>

      {/* Expanded details */}
      {expanded && event.eventType === "rag.query" && (
        <div className="mt-2 ml-10 space-y-2 text-xs">
          {(d.answer as string) && (
            <div className="bg-gray-50 rounded-md p-3">
              <div className="font-medium text-gray-600 mb-1">Answer</div>
              <p className="text-gray-700 whitespace-pre-line leading-relaxed">
                {d.answer as string}
              </p>
            </div>
          )}
          <div className="flex gap-4 text-gray-500">
            <span>Scope: {d.scope as string}</span>
            <span>Mode: {d.search_mode as string}</span>
            <span>Chunks: {d.chunks_retrieved as number}</span>
            <span>Citations: {d.citations_count as number}</span>
          </div>
          {Array.isArray(d.cited_sections) && (d.cited_sections as Array<Record<string, unknown>>).length > 0 && (
            <div>
              <div className="font-medium text-gray-600 mb-1">Sources</div>
              <div className="space-y-1">
                {(d.cited_sections as Array<Record<string, unknown>>).map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-gray-500">
                    <span className="font-medium">{s.document as string}</span>
                    {(s.section as string) && <span className="text-gray-400">{s.section as string}</span>}
                    <span className="text-gray-300">({((s.score as number) * 100).toFixed(0)}%)</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {expanded && event.eventType !== "rag.query" && Object.keys(d).length > 0 && (
        <div className="mt-2 ml-10">
          <pre className="text-xs text-gray-500 bg-gray-50 rounded-md p-2 overflow-x-auto">
            {JSON.stringify(d, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function EventIcon({ type }: { type: string }) {
  const cls = "w-3.5 h-3.5";
  switch (type) {
    case "arrow-up":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>;
    case "doc":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>;
    case "tag":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z" /></svg>;
    case "table":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M3 10h11M3 6h7m0 8h4m-4 4h7m4-12v16m0 0l-3-3m3 3l3-3" /></svg>;
    case "lines":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h10M4 18h14" /></svg>;
    case "db":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 3.6 3 8 3s8-1 8-3V7M4 7c0 2 3.6 3 8 3s8-1 8-3M4 7c0-2 3.6-3 8-3s8 1 8 3" /></svg>;
    case "trash":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>;
    case "stack":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>;
    case "check":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
    case "x":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>;
    case "search":
      return <svg className={cls} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>;
    default:
      return <div className="w-3.5 h-3.5 rounded-full bg-current" />;
  }
}
