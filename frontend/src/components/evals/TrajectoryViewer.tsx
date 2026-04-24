/** Tool-call trajectory viewer for agentic RAG eval results. */

interface ToolCall {
  name: string;
  args?: Record<string, unknown>;
}

interface Props {
  trajectory?: ToolCall[];
  expected?: string[];
}

export default function TrajectoryViewer({ trajectory, expected }: Props) {
  const calls = trajectory ?? [];
  const expectedSet = new Set(expected ?? []);
  if (calls.length === 0) {
    return <p className="text-sm text-gray-500">No tool calls recorded.</p>;
  }
  return (
    <ol className="space-y-1.5">
      {calls.map((call, idx) => {
        const isExpected = expectedSet.has(call.name);
        return (
          <li
            key={idx}
            className="flex items-start gap-3 text-sm rounded-md border border-gray-200 px-3 py-2"
          >
            <span className="font-mono text-xs text-gray-400 w-6 shrink-0">#{idx + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">{call.name}</span>
                {isExpected && (
                  <span className="text-xs text-green-700 bg-green-50 rounded-full px-2 py-0.5">
                    expected
                  </span>
                )}
              </div>
              {call.args && Object.keys(call.args).length > 0 && (
                <pre className="mt-1 text-xs text-gray-600 bg-gray-50 rounded px-2 py-1 overflow-x-auto">
                  {JSON.stringify(call.args, null, 2)}
                </pre>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
