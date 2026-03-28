import { describe, it, expect, vi, beforeEach } from "vitest";
import { uploadBulkFiles, listBulkJobs, getBulkJobDetail } from "../bulk";
import apiClient from "../client";

vi.mock("../client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

describe("bulk API functions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("uploadBulkFiles", () => {
    it("posts files as multipart form data", async () => {
      const mockResponse = {
        data: {
          jobId: "job-1",
          status: "pending",
          totalDocuments: 2,
          documents: [],
          createdAt: "2026-03-28T12:00:00Z",
        },
      };
      mockPost.mockResolvedValue(mockResponse);

      const files = [
        new File(["content1"], "doc1.pdf", { type: "application/pdf" }),
        new File(["content2"], "doc2.pdf", { type: "application/pdf" }),
      ];

      const result = await uploadBulkFiles(files);

      expect(mockPost).toHaveBeenCalledWith(
        "/bulk/upload",
        expect.any(FormData),
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      expect(result.jobId).toBe("job-1");
    });
  });

  describe("listBulkJobs", () => {
    it("fetches all jobs without status filter", async () => {
      const mockResponse = { data: { jobs: [] } };
      mockGet.mockResolvedValue(mockResponse);

      const result = await listBulkJobs();

      expect(mockGet).toHaveBeenCalledWith("/bulk/jobs", {
        params: undefined,
      });
      expect(result.jobs).toEqual([]);
    });

    it("passes status filter when provided", async () => {
      const mockResponse = { data: { jobs: [] } };
      mockGet.mockResolvedValue(mockResponse);

      await listBulkJobs("processing");

      expect(mockGet).toHaveBeenCalledWith("/bulk/jobs", {
        params: { status: "processing" },
      });
    });
  });

  describe("getBulkJobDetail", () => {
    it("fetches job detail by id", async () => {
      const mockResponse = {
        data: {
          id: "job-1",
          status: "completed",
          totalDocuments: 3,
          processedCount: 3,
          failedCount: 0,
          documents: [],
          createdAt: "2026-03-28T12:00:00Z",
          completedAt: "2026-03-28T12:05:00Z",
        },
      };
      mockGet.mockResolvedValue(mockResponse);

      const result = await getBulkJobDetail("job-1");

      expect(mockGet).toHaveBeenCalledWith("/bulk/jobs/job-1");
      expect(result.id).toBe("job-1");
    });
  });
});
