/** Summary-scores breakdown table for a single run. */

interface Props {
  scores: Record<string, number>;
  primaryKey?: string | null;
}

function pct(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function bar(value: number | null | undefined) {
  if (value == null) return null;
  const clamped = Math.max(0, Math.min(1, value));
  const color =
    clamped >= 0.9
      ? "bg-green-500"
      : clamped >= 0.7
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <div className="w-32 h-1.5 bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full ${color}`} style={{ width: `${clamped * 100}%` }} />
    </div>
  );
}

export default function MetricBreakdown({ scores, primaryKey }: Props) {
  const entries = Object.entries(scores).sort(([a], [b]) => a.localeCompare(b));
  if (entries.length === 0) {
    return <p className="text-sm text-gray-500">No metric scores recorded.</p>;
  }
  return (
    <table className="w-full text-sm">
      <tbody>
        {entries.map(([key, value]) => (
          <tr
            key={key}
            className={`border-b border-gray-100 ${key === primaryKey ? "font-medium" : ""}`}
          >
            <td className="py-2 pr-4 text-gray-700">{key}</td>
            <td className="py-2 pr-4 tabular-nums text-gray-900 w-20">{pct(value)}</td>
            <td className="py-2">{bar(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
