import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import BulkPage from "../BulkPage";

// Mock the hooks
vi.mock("../../hooks/useBulk", () => ({
  useBulkJobs: vi.fn(() => ({
    data: {
      jobs: [
        {
          id: "job-1",
          status: "completed",
          totalDocuments: 3,
          processedCount: 3,
          failedCount: 0,
          createdAt: "2026-03-28T12:00:00Z",
          completedAt: "2026-03-28T12:05:00Z",
        },
      ],
    },
    isLoading: false,
  })),
  useUploadBulk: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    data: null,
    error: null,
  })),
  useBulkJobDetail: () => ({ data: null }),
}));

describe("BulkPage", () => {
  it("renders the page header", () => {
    render(<BulkPage />);

    expect(screen.getByText("Bulk Processing")).toBeDefined();
    expect(
      screen.getByText(
        "Upload multiple documents for batch processing through the full pipeline.",
      ),
    ).toBeDefined();
  });

  it("renders the New Bulk Job section with upload zone", () => {
    render(<BulkPage />);

    expect(screen.getByText("New Bulk Job")).toBeDefined();
    expect(screen.getByTestId("bulk-upload-dropzone")).toBeDefined();
  });

  it("renders the Bulk Jobs section with job list", () => {
    render(<BulkPage />);

    expect(screen.getByText("Bulk Jobs")).toBeDefined();
    expect(screen.getByTestId("bulk-job-list")).toBeDefined();
  });

  it("shows loading state when jobs are loading", async () => {
    const { useBulkJobs } = await import("../../hooks/useBulk");
    vi.mocked(useBulkJobs).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useBulkJobs>);

    render(<BulkPage />);

    expect(screen.getByText("Loading jobs...")).toBeDefined();
  });
});
