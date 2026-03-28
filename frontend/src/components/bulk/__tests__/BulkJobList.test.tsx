import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import BulkJobList from "../BulkJobList";
import type { BulkJob } from "../../../types/bulk";

// Mock the useBulk hook so JobRow doesn't make real queries
vi.mock("../../../hooks/useBulk", () => ({
  useBulkJobDetail: () => ({ data: null }),
}));

describe("BulkJobList", () => {
  const mockJobs: BulkJob[] = [
    {
      id: "job-1",
      status: "processing",
      totalDocuments: 10,
      processedCount: 6,
      failedCount: 1,
      createdAt: "2026-03-28T12:00:00Z",
      completedAt: null,
    },
    {
      id: "job-2",
      status: "completed",
      totalDocuments: 5,
      processedCount: 5,
      failedCount: 0,
      createdAt: "2026-03-28T11:00:00Z",
      completedAt: "2026-03-28T11:05:00Z",
    },
  ];

  it("renders empty state when no jobs", () => {
    render(<BulkJobList jobs={[]} />);

    expect(
      screen.getByText("No bulk jobs yet. Upload files above to get started."),
    ).toBeDefined();
  });

  it("renders job cards for each job", () => {
    render(<BulkJobList jobs={mockJobs} />);

    const cards = screen.getAllByTestId("bulk-job-card");
    expect(cards).toHaveLength(2);
  });

  it("displays status badges with correct text", () => {
    render(<BulkJobList jobs={mockJobs} />);

    const badges = screen.getAllByTestId("bulk-job-status-badge");
    expect(badges[0]?.textContent).toBe("processing");
    expect(badges[1]?.textContent).toBe("completed");
  });

  it("shows progress bar with processed/total counts", () => {
    render(<BulkJobList jobs={mockJobs} />);

    expect(screen.getByText("6 / 10")).toBeDefined();
    expect(screen.getByText("5 / 5")).toBeDefined();
  });

  it("displays failed count when present", () => {
    render(<BulkJobList jobs={mockJobs} />);

    expect(screen.getByText("1 failed")).toBeDefined();
  });

  it("renders expand toggle buttons", () => {
    render(<BulkJobList jobs={mockJobs} />);

    const toggles = screen.getAllByTestId("bulk-job-toggle");
    expect(toggles).toHaveLength(2);
  });
});
