/** Run-detail page — per-example results, metric breakdown, trajectory viewer. */

import { Link, useParams } from "react-router-dom";
import PageHeader from "../components/ui/PageHeader";
import MetricBreakdown from "../components/evals/MetricBreakdown";
import ResultsTable from "../components/evals/ResultsTable";
import TrajectoryViewer from "../components/evals/TrajectoryViewer";
import { useEvalRun } from "../hooks/useEvals";
import type { EvalResultItem } from "../types/evals";

function extractTrajectory(results: EvalResultItem[]): { name: string }[] | undefined {
  for (const r of results) {
    const p = r.prediction as Record<string, unknown> | null | undefined;
    if (!p) continue;
    const traj = p.trajectory as unknown;
    if (Array.isArray(traj) && traj.length > 0) {
      return traj.map((t) => ({
        name: (t as { name?: string }).name ?? "?",
        args: (t as { args?: Record<string, unknown> }).args,
      })) as { name: string }[];
    }
  }
  return undefined;
}

export default function EvalRunDetailPage() {
  const { id } = useParams();
  const { data, isLoading, error } = useEvalRun(id);

  if (isLoading) return <p className="p-8 text-sm text-gray-500">Loading…</p>;
  if (error || !data) {
    return <p className="p-8 text-sm text-red-600">Failed to load run.</p>;
  }

  const { run, results } = data;
  const trajectory = extractTrajectory(results);

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <Link to="/evals" className="text-sm text-primary-600 hover:underline mb-2 inline-block">
        ← Back to overview
      </Link>
      <PageHeader
        title={`${run.stage} · ${run.id.slice(0, 8)}`}
        subtitle={`${run.totalExamples} examples · ${run.durationSeconds?.toFixed(1) ?? "—"}s · model ${run.model}`}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="border border-gray-200 rounded-xl p-5 bg-white md:col-span-2">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Summary scores</h2>
          <MetricBreakdown scores={run.summaryScores} />
        </div>
        <div className="border border-gray-200 rounded-xl p-5 bg-white space-y-2 text-sm">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Run metadata</h2>
          <Meta label="Status" value={run.status} />
          <Meta label="Dataset" value={run.datasetName} />
          <Meta label="Git SHA" value={run.gitSha ?? "—"} mono />
          <Meta label="Judge model" value={run.judgeModel ?? "—"} />
          {run.langsmithExperimentUrl && (
            <div className="pt-2">
              <a
                href={run.langsmithExperimentUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-primary-600 hover:underline"
              >
                Open in LangSmith →
              </a>
            </div>
          )}
        </div>
      </div>

      {trajectory && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Tool-call trajectory</h2>
          <TrajectoryViewer trajectory={trajectory} />
        </section>
      )}

      <section>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Per-example results</h2>
        <ResultsTable results={results} />
      </section>
    </div>
  );
}

function Meta({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-gray-500">{label}</span>
      <span className={`text-gray-900 ${mono ? "font-mono text-xs" : ""}`}>{value}</span>
    </div>
  );
}
