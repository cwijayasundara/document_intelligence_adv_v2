/** Evals overview — scorecards per pipeline stage with run-now buttons. */

import { useState } from "react";
import PageHeader from "../components/ui/PageHeader";
import ScoreCard from "../components/evals/ScoreCard";
import { useEvalOverview, useTriggerEvalRun } from "../hooks/useEvals";

export default function EvalsPage() {
  const { data, isLoading, error } = useEvalOverview();
  const trigger = useTriggerEvalRun();
  const [pending, setPending] = useState<string | null>(null);

  const onRun = async (stage: string) => {
    setPending(stage);
    try {
      await trigger.mutateAsync({ stage });
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <PageHeader
        title="Evaluations"
        subtitle="Quality metrics for every LLM touchpoint — updated on each run."
      />

      {isLoading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && (
        <p className="text-sm text-red-600">
          Failed to load overview. Is the backend running?
        </p>
      )}

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((item) => (
            <ScoreCard
              key={item.stage}
              item={item}
              onRun={onRun}
              running={pending === item.stage || item.run?.status === "running"}
            />
          ))}
        </div>
      )}

      <section className="mt-10">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">About these metrics</h2>
        <ul className="text-sm text-gray-600 space-y-1 list-disc pl-5">
          <li>
            <span className="font-medium">Metric-based</span> — deterministic (exact match, numeric
            tolerance, Recall@K, nDCG, SQL execution-match).
          </li>
          <li>
            <span className="font-medium">LLM-as-judge</span> — RAGAS triad, summary faithfulness,
            judge-meta calibration.
          </li>
          <li>
            <span className="font-medium">Rubric-based</span> — YAML-defined multi-criterion scores
            (verbatim quote, format, coverage).
          </li>
          <li>
            <span className="font-medium">Trajectory</span> — tool-call subset / order / no
            unnecessary calls, for the agentic RAG.
          </li>
        </ul>
      </section>
    </div>
  );
}
