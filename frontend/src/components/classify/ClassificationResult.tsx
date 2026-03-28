/** Displays the detected classification category and reasoning text. */

interface ClassificationResultProps {
  categoryName: string | null;
  reasoning: string | null;
}

export default function ClassificationResult({
  categoryName,
  reasoning,
}: ClassificationResultProps) {
  if (!categoryName) {
    return (
      <div className="p-6 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500">
          No classification result yet. Click "Classify" to detect the document
          category.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg border border-gray-200 space-y-4">
      <div>
        <h3 className="text-sm font-medium text-gray-500">Detected Category</h3>
        <p
          className="mt-1 text-lg font-semibold text-gray-900"
          data-testid="detected-category"
        >
          {categoryName}
        </p>
      </div>
      {reasoning && (
        <div>
          <h3 className="text-sm font-medium text-gray-500">Reasoning</h3>
          <p className="mt-1 text-gray-700" data-testid="classification-reasoning">
            {reasoning}
          </p>
        </div>
      )}
    </div>
  );
}
