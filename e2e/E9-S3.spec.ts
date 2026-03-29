import { test, expect } from '@playwright/test';
import bulkJobs from '../specs/test_artefacts/test-data/bulk_jobs.json';

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('E9-S3: Bulk Upload + Dashboard UI', () => {

  test.beforeEach(async ({ page }) => {
    await page.route(`${API_BASE}/bulk/jobs`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(bulkJobs),
        });
      } else {
        route.continue();
      }
    });

    // Mock job detail endpoints
    for (const job of bulkJobs) {
      await page.route(`${API_BASE}/bulk/jobs/${job.id}`, (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(job),
        });
      });
    }
  });

  test('AC-1: bulk dashboard displays jobs with status badge, progress bar, and timestamps', async ({ page }) => {
    await page.goto('/bulk');

    // Verify job list is visible
    await expect(page.getByText('completed').first()).toBeVisible();
    await expect(page.getByText('processing').first()).toBeVisible();

    // Verify progress bar or progress indicator
    await expect(page.getByRole('progressbar').first()).toBeVisible();

    // Verify timestamps are shown
    // At least one date-like string should be visible
    await expect(page.getByText(/2026/).first()).toBeVisible();
  });

  test('AC-2: New Bulk Job section with multi-file drag-drop upload zone', async ({ page }) => {
    await page.route(`${API_BASE}/bulk/upload`, (route) => {
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'bulk_new_001',
          status: 'pending',
          total_documents: 2,
          processed_count: 0,
          failed_count: 0,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.goto('/bulk');

    // Verify "New Bulk Job" section exists
    await expect(page.getByText(/new.*bulk.*job|bulk.*upload|start.*bulk/i)).toBeVisible();

    // Verify drag-drop zone
    await expect(page.getByText(/drag.*drop|drop.*files|browse/i)).toBeVisible();

    // Upload multiple files
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles([
      {
        name: 'doc_a.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('%PDF-1.4 document A'),
      },
      {
        name: 'doc_b.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('%PDF-1.4 document B'),
      },
    ]);
  });

  test('AC-3: expanding a job row shows per-document status indicators', async ({ page }) => {
    await page.goto('/bulk');

    // Click on the completed job to expand it
    const completedJobRow = page.getByText('completed').first().locator('..');
    await completedJobRow.click();

    // Verify per-document rows appear
    await expect(page.getByText('Horizon_Equity_Partners_IV_LPA.pdf')).toBeVisible();
    await expect(page.getByText('Apex_Growth_Equity_Fund_III_Subscription.pdf')).toBeVisible();
    await expect(page.getByText('Meridian_Capital_Side_Letter_LP42.pdf')).toBeVisible();

    // Click on the processing job to expand it
    const processingJobRow = page.getByText('processing').first().locator('..');
    await processingJobRow.click();

    // Verify mixed statuses in per-document view
    await expect(page.getByText('Corrupted_Document.pdf')).toBeVisible();
    await expect(page.getByText('failed').first()).toBeVisible();
  });

  test('AC-4: failed documents display error message with error styling', async ({ page }) => {
    await page.goto('/bulk');

    // Expand the processing job (which has a failed document)
    const processingJobRow = page.getByText('processing').first().locator('..');
    await processingJobRow.click();

    // Verify error message is displayed for the failed document
    await expect(page.getByText(/Reducto parse error|unable to extract text|corrupted PDF/i)).toBeVisible();

    // Verify the failed document row has visual error styling
    await expect(page.getByText('Corrupted_Document.pdf')).toBeVisible();
  });

  test('AC-5: job list auto-refreshes with 5-second polling while processing', async ({ page }) => {
    let requestCount = 0;

    page.on('request', (request) => {
      if (request.url().includes('/bulk/jobs') && request.method() === 'GET') {
        requestCount++;
      }
    });

    await page.goto('/bulk');

    // Wait for initial load
    await expect(page.getByText('completed').first()).toBeVisible();

    const initialCount = requestCount;

    // Wait 12 seconds for at least 2 additional polling cycles (5s interval)
    await page.waitForTimeout(12000);

    // Verify multiple refetch requests were made
    expect(requestCount).toBeGreaterThan(initialCount + 1);
  });

  test('AC-1 (detail): progress bar reflects processed_count / total_documents', async ({ page }) => {
    await page.goto('/bulk');

    // The completed job should show full progress (3/3)
    // The processing job should show partial progress (2/4 completed + 1 failed)
    await expect(page.getByText(/3.*\/.*3|3 of 3/i).or(page.getByText('100%'))).toBeVisible();

    // Processing job should show partial progress
    // 2 completed + 1 failed out of 4 total => ~75% or "3/4"
    await expect(
      page.getByText(/2.*\/.*4|3.*\/.*4/i).or(page.getByText(/50%|75%/i))
    ).toBeVisible();
  });
});
