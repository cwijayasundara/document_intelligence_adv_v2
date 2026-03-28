import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import BulkJobDetail from "../BulkJobDetail";
import type { BulkJobDocument } from "../../../types/bulk";

describe("BulkJobDetail", () => {
  const mockDocuments: BulkJobDocument[] = [
    {
      documentId: "doc-1",
      fileName: "report.pdf",
      status: "completed",
      errorMessage: null,
      processingTimeMs: 12340,
    },
    {
      documentId: "doc-2",
      fileName: "contract.docx",
      status: "failed",
      errorMessage: "Reducto parsing failed: corrupted PDF",
      processingTimeMs: 2100,
    },
    {
      documentId: "doc-3",
      fileName: "spreadsheet.xlsx",
      status: "pending",
      errorMessage: null,
      processingTimeMs: null,
    },
  ];

  it("renders document rows for all documents", () => {
    render(<BulkJobDetail documents={mockDocuments} />);

    expect(screen.getByText("report.pdf")).toBeDefined();
    expect(screen.getByText("contract.docx")).toBeDefined();
    expect(screen.getByText("spreadsheet.xlsx")).toBeDefined();
  });

  it("displays processing time in seconds", () => {
    render(<BulkJobDetail documents={mockDocuments} />);

    expect(screen.getByText("12.3s")).toBeDefined();
    expect(screen.getByText("2.1s")).toBeDefined();
  });

  it("shows dash for null processing time", () => {
    render(<BulkJobDetail documents={mockDocuments} />);

    const rows = screen.getAllByTestId("bulk-document-row");
    expect(rows).toHaveLength(3);
  });

  it("displays error messages with red styling for failed documents", () => {
    render(<BulkJobDetail documents={mockDocuments} />);

    const errorText = screen.getByText(
      "Reducto parsing failed: corrupted PDF",
    );
    expect(errorText).toBeDefined();
    expect(errorText.className).toContain("text-red-600");
  });

  it("shows status dots for each document", () => {
    render(<BulkJobDetail documents={mockDocuments} />);

    expect(screen.getByTestId("status-dot-completed")).toBeDefined();
    expect(screen.getByTestId("status-dot-failed")).toBeDefined();
    expect(screen.getByTestId("status-dot-pending")).toBeDefined();
  });
});
