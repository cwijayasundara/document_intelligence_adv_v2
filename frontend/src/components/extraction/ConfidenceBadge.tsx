/** Color-coded confidence badge with tooltip. */

import type { ConfidenceLevel } from "../../types/extraction";

interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel;
  reasoning: string;
}

const BADGE_STYLES: Record<ConfidenceLevel, string> = {
  high: "bg-green-100 text-green-800 border-green-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-red-100 text-red-800 border-red-200",
};

const BADGE_LABELS: Record<ConfidenceLevel, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

export default function ConfidenceBadge({
  confidence,
  reasoning,
}: ConfidenceBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${BADGE_STYLES[confidence]}`}
      title={reasoning}
      data-testid={`confidence-badge-${confidence}`}
    >
      {BADGE_LABELS[confidence]}
    </span>
  );
}
