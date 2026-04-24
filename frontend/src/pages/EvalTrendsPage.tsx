/** Trend charts — score per stage/metric over time. */

import { useState } from "react";
import PageHeader from "../components/ui/PageHeader";
import { useEvalTrend } from "../hooks/useEvals";
import { EVAL_STAGES } from "../types/evals";

const METRICS_BY_STAGE: Record<string, string[]> = {
  classification: ["classification_accuracy", "classification_confidence_in_range"],
  extraction: [
    "extraction_exact_match",
    "extraction_numeric_tolerance",
    "extraction_source_substring",
  ],
  summary: ["summary_pe_checklist_coverage", "summary_faithfulness"],
  rag: ["rag_answer_contains", "retrieval_recall_at_5", "retrieval_mrr", "ragas_triad"],
  sql: ["sql_validity", "sql_safety", "sql_intent_match"],
  agentic_rag: ["trajectory_subset", "trajectory_order", "no_unnecessary_calls"],
  pipeline: ["pipeline_stages_subset", "pipeline_gate_correctness"],
};

function Sparkline({ points }: { points: (number | null)[] }) {
  if (points.length === 0) return <p className="text-sm text-gray-500">No data.</p>;
  const width = 600;
  const height = 120;
  const validPoints = points.map((p) => (p ?? 0) * 100);
  const max = Math.max(100, ...validPoints);
  const min = Math.min(0, ...validPoints);
  const range = max - min || 1;
  const step = points.length > 1 ? width / (points.length - 1) : 0;

  const d = validPoints
    .map((v, i) => `${i === 0 ? "M" : "L"} ${i * step} ${height - ((v - min) / range) * height}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-32">
      <path d={d} stroke="currentColor" fill="none" strokeWidth="2" className="text-primary-600" />
      {validPoints.map((v, i) => (
        <circle
          key={i}
          cx={i * step}
          cy={height - ((v - min) / range) * height}
          r={3}
          className="fill-primary-600"
        />
      ))}
    </svg>
  );
}

export default function EvalTrendsPage() {
  const [stage, setStage] = useState<string>(EVAL_STAGES[0]);
  const [metric, setMetric] = useState<string>(METRICS_BY_STAGE[EVAL_STAGES[0]][0]);
  const { data, isLoading } = useEvalTrend(stage, metric);
  const metrics = METRICS_BY_STAGE[stage] ?? [];

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <PageHeader title="Trends" subtitle="Metric trajectories over time — filter by stage." />

      <div className="flex items-center gap-4 mb-6">
        <label className="text-sm text-gray-600">
          Stage
          <select
            value={stage}
            onChange={(e) => {
              const s = e.target.value;
              setStage(s);
              setMetric(METRICS_BY_STAGE[s]?.[0] ?? "");
            }}
            className="ml-2 border border-gray-200 rounded-md px-2 py-1 text-sm"
          >
            {EVAL_STAGES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-gray-600">
          Metric
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
            className="ml-2 border border-gray-200 rounded-md px-2 py-1 text-sm"
          >
            {metrics.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="border border-gray-200 rounded-xl p-6 bg-white">
        {isLoading && <p className="text-sm text-gray-500">Loading…</p>}
        {data && <Sparkline points={data.points.map((p) => p.score)} />}
        {data && data.points.length > 0 && (
          <p className="text-xs text-gray-500 mt-3">
            {data.points.length} runs · latest {data.points[data.points.length - 1]?.createdAt}
          </p>
        )}
      </div>
    </div>
  );
}
