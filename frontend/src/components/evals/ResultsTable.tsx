/** Per-example × per-evaluator results table with expandable diff view. */

import { useMemo, useState } from "react";
import type { EvalResultItem } from "../../types/evals";

interface Props {
  results: EvalResultItem[];
}

function scoreBadge(score: number | null) {
  if (score == null) return <span className="text-gray-400">n/a</span>;
  const pct = `${(score * 100).toFixed(0)}%`;
  const color =
    score >= 0.9
      ? "text-green-700 bg-green-50"
      : score >= 0.7
        ? "text-amber-700 bg-amber-50"
        : "text-red-700 bg-red-50";
  return (
    <span className={`text-xs font-medium rounded-full px-2 py-0.5 ${color}`}>{pct}</span>
  );
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  if (!value) return null;
  return (
    <div className="text-xs">
      <div className="text-gray-500 mb-1 font-medium uppercase tracking-wide">{label}</div>
      <pre className="bg-gray-50 rounded p-2 overflow-x-auto max-h-64">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

export default function ResultsTable({ results }: Props) {
  const [openRow, setOpenRow] = useState<string | null>(null);

  const byExample = useMemo(() => {
    const map = new Map<string, EvalResultItem[]>();
    for (const r of results) {
      const list = map.get(r.exampleId) ?? [];
      list.push(r);
      map.set(r.exampleId, list);
    }
    return Array.from(map.entries());
  }, [results]);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-600 text-xs uppercase tracking-wide">
          <tr>
            <th className="text-left px-4 py-3 font-medium">Example</th>
            <th className="text-left px-4 py-3 font-medium">Evaluator scores</th>
            <th className="w-16 px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {byExample.map(([exampleId, rows]) => {
            const isOpen = openRow === exampleId;
            return (
              <>
                <tr
                  key={exampleId}
                  className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setOpenRow(isOpen ? null : exampleId)}
                >
                  <td className="px-4 py-3 font-mono text-xs text-gray-700">{exampleId}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {rows.map((r) => (
                        <span
                          key={r.evaluatorKey}
                          className="inline-flex items-center gap-1.5 text-xs"
                        >
                          <span className="text-gray-500">{r.evaluatorKey}</span>
                          {scoreBadge(r.score)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-400">{isOpen ? "▾" : "▸"}</td>
                </tr>
                {isOpen && (
                  <tr key={`${exampleId}-detail`} className="bg-gray-50">
                    <td colSpan={3} className="px-4 py-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <JsonBlock label="prediction" value={rows[0]?.prediction} />
                        <JsonBlock label="expected" value={rows[0]?.expected} />
                      </div>
                      <div className="mt-4 space-y-2">
                        {rows.map((r) => (
                          <div
                            key={`${r.evaluatorKey}-comment`}
                            className="text-xs border-l-2 border-gray-200 pl-3"
                          >
                            <div className="font-medium text-gray-700">
                              {r.evaluatorKey} · {scoreBadge(r.score)}
                            </div>
                            {r.comment && (
                              <div className="text-gray-600 mt-0.5">{r.comment}</div>
                            )}
                            {r.criteriaBreakdown && (
                              <JsonBlock label="criteria" value={r.criteriaBreakdown} />
                            )}
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
