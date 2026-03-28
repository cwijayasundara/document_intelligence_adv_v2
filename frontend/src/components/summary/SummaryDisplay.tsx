/** Displays the generated document summary text. */

interface SummaryDisplayProps {
  summary: string;
  isLoading: boolean;
}

export default function SummaryDisplay({
  summary,
  isLoading,
}: SummaryDisplayProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3 p-6">
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
        <div className="h-4 bg-gray-200 rounded w-4/6" />
        <div className="h-4 bg-gray-200 rounded w-full" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="p-6 text-gray-400 text-center">
        No summary generated yet. Click "Generate Summary" to start.
      </div>
    );
  }

  return (
    <div className="p-6" data-testid="summary-display">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Summary</h3>
      <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
        {summary}
      </div>
    </div>
  );
}
