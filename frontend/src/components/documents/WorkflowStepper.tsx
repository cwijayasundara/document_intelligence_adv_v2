/** Workflow stepper showing single-document processing progress.
 *
 * Derives step state from the document's status and the current page.
 * Completed steps are clickable to navigate back. Upcoming steps are disabled.
 */

import { Link } from "react-router-dom";
import type { DocumentStatus } from "../../types/common";

export type WorkflowStep = "parse" | "summarize" | "classify" | "extract" | "chat";

const STEP_ORDER: WorkflowStep[] = ["parse", "summarize", "classify", "extract", "chat"];

const STEP_LABELS: Record<WorkflowStep, string> = {
  parse: "Parse",
  summarize: "Summarize",
  classify: "Classify",
  extract: "Extract",
  chat: "Ingest & Chat",
};

const STEP_ROUTES: Record<WorkflowStep, string> = {
  parse: "parse",
  summarize: "summary",
  classify: "classify",
  extract: "extract",
  chat: "chat",
};

/** Which steps are COMPLETED given the document's backend status. */
function completedStepsFor(status: DocumentStatus | undefined): Set<WorkflowStep> {
  const done = new Set<WorkflowStep>();
  if (!status) return done;
  const reached = (s: DocumentStatus[]) => s.includes(status);

  if (reached(["parsed", "edited", "summarized", "classified", "extracted", "ingested"])) {
    done.add("parse");
  }
  if (reached(["summarized", "classified", "extracted", "ingested"])) {
    done.add("summarize");
  }
  if (reached(["classified", "extracted", "ingested"])) {
    done.add("classify");
  }
  if (reached(["extracted", "ingested"])) {
    done.add("extract");
  }
  if (reached(["ingested"])) {
    done.add("chat");
  }
  return done;
}

interface WorkflowStepperProps {
  documentId: string;
  documentStatus: DocumentStatus | undefined;
  currentStep: WorkflowStep;
}

export default function WorkflowStepper({
  documentId,
  documentStatus,
  currentStep,
}: WorkflowStepperProps) {
  const completed = completedStepsFor(documentStatus);
  const currentIdx = STEP_ORDER.indexOf(currentStep);

  return (
    <div
      className="flex items-center w-full px-6 py-4 border-b border-gray-200 bg-gray-50"
      data-testid="workflow-stepper"
    >
      {STEP_ORDER.map((step, idx) => {
        const isCompleted = completed.has(step);
        const isCurrent = step === currentStep;
        const isUpcoming = !isCompleted && !isCurrent;
        // Clickable if completed OR current-or-earlier (so user can go back)
        const canNavigate = isCompleted || idx <= currentIdx;

        const circleClass = isCompleted
          ? "bg-green-500 text-white"
          : isCurrent
            ? "bg-blue-600 text-white ring-4 ring-blue-100"
            : "bg-gray-200 text-gray-500";

        const labelClass = isCurrent
          ? "text-blue-600 font-semibold"
          : isCompleted
            ? "text-gray-700"
            : "text-gray-400";

        const connectorClass =
          idx < STEP_ORDER.length - 1 && completed.has(step)
            ? "bg-green-500"
            : "bg-gray-300";

        const content = (
          <div className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${circleClass}`}
              >
                {isCompleted ? (
                  <svg
                    className="w-5 h-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  idx + 1
                )}
              </div>
              <span className={`mt-1.5 text-xs ${labelClass}`}>
                {STEP_LABELS[step]}
              </span>
            </div>
          </div>
        );

        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            {canNavigate && !isUpcoming ? (
              <Link
                to={`/documents/${documentId}/${STEP_ROUTES[step]}`}
                className="hover:opacity-80"
                data-testid={`workflow-step-${step}`}
              >
                {content}
              </Link>
            ) : (
              <div
                className="opacity-60 cursor-not-allowed"
                data-testid={`workflow-step-${step}`}
              >
                {content}
              </div>
            )}
            {idx < STEP_ORDER.length - 1 && (
              <div className="flex-1 px-3 pb-6">
                <div className={`h-0.5 w-full ${connectorClass}`} />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
