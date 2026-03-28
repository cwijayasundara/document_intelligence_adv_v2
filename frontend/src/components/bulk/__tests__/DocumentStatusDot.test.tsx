import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import DocumentStatusDot from "../DocumentStatusDot";
import type { BulkDocumentStatus } from "../../../types/bulk";

describe("DocumentStatusDot", () => {
  const cases: Array<{
    status: BulkDocumentStatus;
    color: string;
    label: string;
  }> = [
    { status: "pending", color: "bg-gray-400", label: "Pending" },
    { status: "processing", color: "bg-blue-500", label: "Processing" },
    { status: "completed", color: "bg-green-500", label: "Completed" },
    { status: "failed", color: "bg-red-500", label: "Failed" },
  ];

  cases.forEach(({ status, color, label }) => {
    it(`renders ${status} status with correct color and label`, () => {
      render(<DocumentStatusDot status={status} />);

      const dot = screen.getByTestId(`status-dot-${status}`);
      expect(dot).toBeDefined();
      expect(dot.className).toContain(color);
      expect(screen.getByText(label)).toBeDefined();
    });
  });
});
