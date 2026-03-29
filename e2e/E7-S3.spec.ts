import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('E7-S3: Upload Page with Drag-Drop', () => {

  test('AC-1: upload page renders a drag-drop zone', async ({ page }) => {
    await page.goto('/upload');

    // Verify the dropzone area is visible
    await expect(page.getByText(/drag.*drop|drop.*files|browse.*files/i)).toBeVisible();
  });

  test('AC-2: accepted file types displayed with visual indicators', async ({ page }) => {
    await page.goto('/upload');

    // Verify accepted file type information is shown
    await expect(page.getByText(/pdf/i)).toBeVisible();
    await expect(page.getByText(/docx/i)).toBeVisible();
    await expect(page.getByText(/xlsx/i)).toBeVisible();
  });

  test('AC-3: upload progress indicator shown during file upload', async ({ page }) => {
    await page.goto('/upload');

    // Create a test PDF file buffer
    const fileContent = Buffer.from('%PDF-1.4 test content for upload progress');

    // Intercept upload to add artificial delay so we can observe progress
    await page.route(`${API_BASE}/documents/upload`, async (route) => {
      // Simulate a slow response so progress indicator is visible
      await new Promise((resolve) => setTimeout(resolve, 1000));
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'doc_new_001',
          file_name: 'test_upload.pdf',
          status: 'uploaded',
          file_type: 'application/pdf',
          file_size: fileContent.length,
          created_at: new Date().toISOString(),
        }),
      });
    });

    // Use the file chooser to upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test_upload.pdf',
      mimeType: 'application/pdf',
      buffer: fileContent,
    });

    // Verify progress indicator appears during upload
    await expect(page.getByRole('progressbar').or(page.getByText(/uploading|progress/i))).toBeVisible();
  });

  test('AC-4: duplicate file shows notification with link to existing document', async ({ page }) => {
    await page.goto('/upload');

    // Mock the upload API to return a dedup response (existing document)
    await page.route(`${API_BASE}/documents/upload`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'doc_001',
          file_name: 'Horizon_Equity_Partners_IV_LPA.pdf',
          status: 'ingested',
          file_type: 'application/pdf',
          file_size: 2458624,
          created_at: '2026-03-20T10:30:00Z',
          is_duplicate: true,
        }),
      });
    });

    const fileContent = Buffer.from('%PDF-1.4 duplicate content');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'Horizon_Equity_Partners_IV_LPA.pdf',
      mimeType: 'application/pdf',
      buffer: fileContent,
    });

    // Verify duplicate notification
    await expect(page.getByText(/already exists|duplicate/i)).toBeVisible();

    // Verify link to existing document
    const docLink = page.getByRole('link', { name: /Horizon|existing|view/i });
    await expect(docLink).toBeVisible();
  });

  test('AC-5: successful upload navigates to parse page', async ({ page }) => {
    await page.goto('/upload');

    const newDocId = 'doc_new_002';

    await page.route(`${API_BASE}/documents/upload`, (route) => {
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: newDocId,
          file_name: 'new_document.pdf',
          status: 'uploaded',
          file_type: 'application/pdf',
          file_size: 1024,
          created_at: new Date().toISOString(),
        }),
      });
    });

    const fileContent = Buffer.from('%PDF-1.4 new document content');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'new_document.pdf',
      mimeType: 'application/pdf',
      buffer: fileContent,
    });

    // Verify navigation to parse page
    await expect(page).toHaveURL(`/documents/${newDocId}/parse`);
  });

  test('AC-2 (error): rejected file type shows error', async ({ page }) => {
    await page.goto('/upload');

    const fileContent = Buffer.from('plain text content that should be rejected');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'invalid_file.txt',
      mimeType: 'text/plain',
      buffer: fileContent,
    });

    // Verify rejection message
    await expect(page.getByText(/not supported|invalid.*type|rejected/i)).toBeVisible();
  });
});
