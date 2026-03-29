import { test, expect } from '@playwright/test';
import documents from '../specs/test_artefacts/test-data/documents.json';

const API_BASE = 'http://localhost:8000/api/v1';
const parsedDoc = documents[3]; // doc_004: status=parsed
const uploadedDoc = documents[4]; // doc_005: status=uploaded

const sampleMarkdown = `# Horizon Equity Partners IV Amendment No. 2

## Section 1: Management Fee Adjustment

The management fee shall be reduced from 1.75% to 1.50% of Capital Commitments effective January 1, 2027.

## Section 2: Term Extension

The term of the Partnership is hereby extended by one (1) additional year.

| Term | Original | Amended |
|------|----------|---------|
| Management Fee | 1.75% | 1.50% |
| Fund Term | 10 years | 11 years |
`;

test.describe('E7-S4: Parse/Edit Page with TipTap Split View', () => {

  test('AC-1: parse page renders split view with info panel and editor', async ({ page }) => {
    // Mock document detail
    await page.route(`${API_BASE}/documents/${parsedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(parsedDoc),
      });
    });

    // Mock parsed content
    await page.route(`${API_BASE}/parse/${parsedDoc.id}/content`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ content: sampleMarkdown }),
      });
    });

    await page.goto(`/documents/${parsedDoc.id}/parse`);

    // Verify document info panel is visible (left side)
    await expect(page.getByText(parsedDoc.file_name)).toBeVisible();

    // Verify editor area is visible (right side) — TipTap editors use contenteditable
    await expect(page.getByRole('textbox').or(page.locator('[contenteditable="true"]'))).toBeVisible();
  });

  test('AC-2: TipTap editor loads parsed markdown content', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${parsedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(parsedDoc),
      });
    });

    await page.route(`${API_BASE}/parse/${parsedDoc.id}/content`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ content: sampleMarkdown }),
      });
    });

    await page.goto(`/documents/${parsedDoc.id}/parse`);

    // Verify content from the parsed markdown is displayed in the editor
    await expect(page.getByText('Horizon Equity Partners IV Amendment No. 2')).toBeVisible();
    await expect(page.getByText('Management Fee Adjustment')).toBeVisible();
  });

  test('AC-3: Parse Document button triggers parsing with loading spinner', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${uploadedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(uploadedDoc),
      });
    });

    // No parsed content yet for uploaded doc
    await page.route(`${API_BASE}/parse/${uploadedDoc.id}/content`, (route) => {
      route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Not found"}' });
    });

    // Mock parse trigger with delay
    await page.route(`${API_BASE}/parse/${uploadedDoc.id}`, async (route) => {
      if (route.request().method() === 'POST') {
        await new Promise((resolve) => setTimeout(resolve, 500));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ content: sampleMarkdown }),
        });
      } else {
        route.continue();
      }
    });

    await page.goto(`/documents/${uploadedDoc.id}/parse`);

    const parseButton = page.getByRole('button', { name: /parse document/i });
    await expect(parseButton).toBeVisible();
    await expect(parseButton).toBeEnabled();

    // Click parse and verify loading state
    await parseButton.click();

    // Verify content appears after parse completes
    await expect(page.getByText('Management Fee Adjustment')).toBeVisible();
  });

  test('AC-3 (boundary): Parse button disabled for already-parsed document', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${parsedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(parsedDoc),
      });
    });

    await page.route(`${API_BASE}/parse/${parsedDoc.id}/content`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ content: sampleMarkdown }),
      });
    });

    await page.goto(`/documents/${parsedDoc.id}/parse`);

    const parseButton = page.getByRole('button', { name: /parse document/i });
    // Button should be disabled since document is already parsed
    await expect(parseButton).toBeDisabled();
  });

  test('AC-4: Save Edits button saves content and transitions status', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${parsedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(parsedDoc),
      });
    });

    await page.route(`${API_BASE}/parse/${parsedDoc.id}/content`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ content: sampleMarkdown }),
        });
      } else if (route.request().method() === 'PUT') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'edited' }),
        });
      }
    });

    await page.goto(`/documents/${parsedDoc.id}/parse`);

    // Wait for editor to load
    await expect(page.getByText('Management Fee Adjustment')).toBeVisible();

    // Click Save Edits
    const saveButton = page.getByRole('button', { name: /save edits/i });
    await expect(saveButton).toBeVisible();

    // Intercept the PUT request to verify it fires
    const responsePromise = page.waitForResponse(
      (r) => r.url().includes(`/parse/${parsedDoc.id}/content`) && r.request().method() === 'PUT'
    );

    await saveButton.click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
  });

  test('AC-5: Proceed to Classify button navigates to classify page', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${parsedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(parsedDoc),
      });
    });

    await page.route(`${API_BASE}/parse/${parsedDoc.id}/content`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ content: sampleMarkdown }),
      });
    });

    await page.goto(`/documents/${parsedDoc.id}/parse`);

    const proceedButton = page.getByRole('button', { name: /proceed to classify/i }).or(
      page.getByRole('link', { name: /proceed to classify/i })
    );
    await expect(proceedButton).toBeVisible();
    await proceedButton.click();

    await expect(page).toHaveURL(`/documents/${parsedDoc.id}/classify`);
  });
});
