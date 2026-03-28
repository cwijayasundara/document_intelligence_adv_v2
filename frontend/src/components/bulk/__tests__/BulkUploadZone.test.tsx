import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import BulkUploadZone from "../BulkUploadZone";

describe("BulkUploadZone", () => {
  it("renders the dropzone with multi-file instructions", () => {
    render(<BulkUploadZone onFilesAccepted={vi.fn()} />);

    expect(
      screen.getByText(
        "Drag and drop multiple documents, or click to browse",
      ),
    ).toBeDefined();
    expect(
      screen.getByText("Supports PDF, DOCX, XLSX, PNG, JPG, TIFF"),
    ).toBeDefined();
  });

  it("renders the dropzone element with test id", () => {
    render(<BulkUploadZone onFilesAccepted={vi.fn()} />);

    expect(screen.getByTestId("bulk-upload-dropzone")).toBeDefined();
  });

  it("applies disabled styling when disabled", () => {
    render(<BulkUploadZone onFilesAccepted={vi.fn()} disabled />);

    const dropzone = screen.getByTestId("bulk-upload-dropzone");
    expect(dropzone.className).toContain("opacity-50");
    expect(dropzone.className).toContain("cursor-not-allowed");
  });
});
