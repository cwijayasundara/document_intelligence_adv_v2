/** Displays parse confidence as a colored banner with percentage. */

interface ConfidenceBannerProps {
  confidencePct: number;
}

const CONFIDENCE_THRESHOLD = 90;

export default function ConfidenceBanner({
  confidencePct,
}: ConfidenceBannerProps) {
  const isHigh = confidencePct >= CONFIDENCE_THRESHOLD;

  return (
    <div
      className={`flex items-center gap-2 px-4 py-2 text-sm border-b ${
        isHigh
          ? "bg-green-50 border-green-200 text-green-800"
          : "bg-amber-50 border-amber-200 text-amber-800"
      }`}
    >
      <span className="font-medium">
        Parse Confidence: {confidencePct.toFixed(1)}%
      </span>
      {!isHigh && (
        <span className="text-xs">
          — Low confidence detected. Review and edit the parsed content below.
        </span>
      )}
      {isHigh && (
        <span className="text-xs">
          — High confidence. Content is ready for processing.
        </span>
      )}
    </div>
  );
}

export { CONFIDENCE_THRESHOLD };
