/** Scorecard for one pipeline stage — score, delta, last run metadata. */

import { Link } from "react-router-dom";
import type { OverviewItem } from "../../types/evals";

interface Props {
  item: OverviewItem;
  onRun?: (stage: string) => void;
  running?: boolean;
}

const STAGE_LABELS: Record<string, string> = {
  classification: "Classification",
  extraction: "Extraction",
  summary: "Summary",
  rag: "RAG (basic)",
  sql: "Text-to-SQL",
  agentic_rag: "Agentic RAG",
  pipeline: "Pipeline (E2E)",
};

function pct(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(0)}%`;
}

function deltaBadge(delta: number | null | undefined) {
  if (delta == null) return null;
  const pctDelta = delta * 100;
  const sign = pctDelta >= 0 ? "+" : "";
  const color =
    pctDelta > 0
      ? "text-green-700 bg-green-50"
      : pctDelta < 0
        ? "text-red-700 bg-red-50"
        : "text-gray-700 bg-gray-50";
  return (
    <span className={`text-xs font-medium rounded-full px-2 py-0.5 ${color}`}>
      {sign}
      {pctDelta.toFixed(1)} pp
    </span>
  );
}

export default function ScoreCard({ item, onRun, running }: Props) {
  const label = STAGE_LABELS[item.stage] ?? item.stage;
  const score = item.primaryScore;
  const scoreColor =
    score == null
      ? "text-gray-400"
      : score >= 0.9
        ? "text-green-700"
        : score >= 0.7
          ? "text-amber-700"
          : "text-red-700";

  return (
    <div className="border border-gray-200 rounded-xl p-5 bg-white hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">{label}</h3>
        {item.run?.status === "running" && (
          <span className="text-xs text-blue-600 bg-blue-50 rounded-full px-2 py-0.5">
            running
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-3 mb-2">
        <span className={`text-3xl font-semibold tabular-nums ${scoreColor}`}>{pct(score)}</span>
        {deltaBadge(item.deltaVsPrevious)}
      </div>
      <p className="text-xs text-gray-500 mb-4">
        {item.primaryMetricKey ?? "—"}
        {item.run?.totalExamples ? ` · ${item.run.totalExamples} examples` : ""}
      </p>

      <div className="flex items-center justify-between">
        {item.run?.id ? (
          <Link
            to={`/evals/runs/${item.run.id}`}
            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
          >
            View latest run →
          </Link>
        ) : (
          <span className="text-xs text-gray-400">no runs yet</span>
        )}
        {onRun && (
          <button
            type="button"
            onClick={() => onRun(item.stage)}
            disabled={running}
            className="text-xs px-3 py-1 rounded-md border border-gray-200 hover:bg-gray-50 disabled:opacity-50"
          >
            {running ? "…" : "Run now"}
          </button>
        )}
      </div>
    </div>
  );
}
