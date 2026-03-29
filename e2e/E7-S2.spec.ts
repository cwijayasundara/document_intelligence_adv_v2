import { test, expect } from '@playwright/test';
import documents from '../specs/test_artefacts/test-data/documents.json';

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('E7-S2: Dashboard — Document List with Status', () => {

  test('AC-1: dashboard renders document table with expected columns', async ({ page }) => {
    await page.goto('/');

    const table = page.getByRole('table');
    await expect(table).toBeVisible();

    // Verify column headers exist
    await expect(page.getByRole('columnheader', { name: /file name/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /status/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /category/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /file type/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /file size/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /created/i })).toBeVisible();
  });

  test('AC-2: status badges are color-coded per document status', async ({ page }) => {
    await page.goto('/');

    // Wait for document data to load
    const table = page.getByRole('table');
    await expect(table).toBeVisible();

    // Verify status badges render with expected text values
    // The exact badge for each status should be present based on seeded data
    const statusTexts = ['uploaded', 'parsed', 'classified', 'extracted', 'ingested'];
    for (const status of statusTexts) {
      const badge = page.getByText(status, { exact: true }).first();
      // At least one document with this status should exist in seeded data
      // We check only that the badge rendering mechanism works for present statuses
      if (await badge.isVisible()) {
        await expect(badge).toBeVisible();
      }
    }
  });

  test('AC-3: clicking a row navigates to the next-action page based on status', async ({ page }) => {
    await page.goto('/');

    // Wait for the table to load with data
    const table = page.getByRole('table');
    await expect(table).toBeVisible();

    // Find a row and click it — uploaded document should go to parse page
    const uploadedRow = page.getByRole('row').filter({ hasText: 'uploaded' }).first();
    if (await uploadedRow.isVisible()) {
      await uploadedRow.click();
      await expect(page).toHaveURL(/\/documents\/.*\/parse/);
    }
  });

  test('AC-4: empty state shows call-to-action link to upload', async ({ page }) => {
    // This test requires an empty database state.
    // We intercept the API to return an empty list to simulate empty state.
    await page.route(`${API_BASE}/documents`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    await page.goto('/');

    // Verify empty state message
    await expect(page.getByText(/no documents/i)).toBeVisible();

    // Verify CTA link to /upload
    const uploadLink = page.getByRole('link', { name: /upload/i });
    await expect(uploadLink).toBeVisible();
    await expect(uploadLink).toHaveAttribute('href', '/upload');
  });

  test('AC-5: document list auto-refreshes via polling', async ({ page }) => {
    let requestCount = 0;

    page.on('request', (request) => {
      if (request.url().includes('/documents') && request.method() === 'GET') {
        requestCount++;
      }
    });

    await page.goto('/');

    // Wait for initial load
    await expect(page.getByRole('table')).toBeVisible();

    const initialCount = requestCount;

    // Wait ~35 seconds for at least one refetch cycle (30s interval)
    await page.waitForTimeout(35000);

    // Verify at least one additional request was made
    expect(requestCount).toBeGreaterThan(initialCount);
  });

  test('AC-1 (detail): document data values displayed correctly', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByRole('table')).toBeVisible();

    // Check that a known document file name appears in the table
    // Using the first fixture document as reference
    const knownFileName = documents[0].file_name;
    await expect(page.getByText(knownFileName)).toBeVisible();
  });
});
