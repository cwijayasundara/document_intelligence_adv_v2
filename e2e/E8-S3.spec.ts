import { test, expect } from '@playwright/test';
import documents from '../specs/test_artefacts/test-data/documents.json';
import extractedValues from '../specs/test_artefacts/test-data/extracted_values.json';

const API_BASE = 'http://localhost:8000/api/v1';
const extractedDoc = documents[1]; // doc_002: status=extracted
const classifiedDoc = documents[2]; // doc_003: status=classified

test.describe('E8-S3: Extraction Results 3-Column View + Review Gate', () => {

  function mockExtractionRoutes(page: any, docId: string) {
    return Promise.all([
      page.route(`${API_BASE}/documents/${docId}`, (route: any) => {
        const doc = documents.find((d) => d.id === docId) || extractedDoc;
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(doc),
        });
      }),
      page.route(`${API_BASE}/extract/${docId}/results`, (route: any) => {
        if (route.request().method() === 'GET') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(extractedValues.values),
          });
        } else if (route.request().method() === 'PUT') {
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ updated: true }),
          });
        }
      }),
    ]);
  }

  test('AC-1: extraction page renders 3-column table with field name, value, and source text', async ({ page }) => {
    await mockExtractionRoutes(page, extractedDoc.id);

    await page.goto(`/documents/${extractedDoc.id}/extract`);

    // Verify table structure
    await expect(page.getByRole('columnheader', { name: /field/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /value|extracted/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /source/i })).toBeVisible();

    // Verify data rows
    await expect(page.getByText('Fund Name')).toBeVisible();
    await expect(page.getByText('Horizon Equity Partners IV, L.P.')).toBeVisible();
  });

  test('AC-2: confidence badges are green/yellow/red with tooltip', async ({ page }) => {
    await mockExtractionRoutes(page, extractedDoc.id);

    await page.goto(`/documents/${extractedDoc.id}/extract`);

    // High confidence badge (green) — Fund Name has "high" confidence
    const highBadge = page.getByText('high', { exact: true }).first();
    await expect(highBadge).toBeVisible();

    // Medium confidence badge (yellow) — Fund Term has "medium" confidence
    const mediumBadge = page.getByText('medium', { exact: true }).first();
    await expect(mediumBadge).toBeVisible();

    // Low confidence badge (red) — Governing Law has "low" confidence
    const lowBadge = page.getByText('low', { exact: true }).first();
    await expect(lowBadge).toBeVisible();

    // Hover over a badge to check tooltip with reasoning
    await lowBadge.hover();
    await expect(page.getByText(/arbitration clause/i)).toBeVisible();
  });

  test('AC-3: low-confidence rows highlighted with amber background and review label', async ({ page }) => {
    await mockExtractionRoutes(page, extractedDoc.id);

    await page.goto(`/documents/${extractedDoc.id}/extract`);

    // Verify "Requires Review" label for low-confidence field
    await expect(page.getByText(/requires review/i).first()).toBeVisible();

    // Verify "Edit" button exists for low-confidence rows
    const editButtons = page.getByRole('button', { name: /edit/i });
    expect(await editButtons.count()).toBeGreaterThanOrEqual(1);
  });

  test('AC-4: inline editing saves value and marks field as reviewed', async ({ page }) => {
    await mockExtractionRoutes(page, extractedDoc.id);

    await page.goto(`/documents/${extractedDoc.id}/extract`);

    // Find edit button for a requires_review field (governing_law)
    const governingLawRow = page.getByText('Governing Law').locator('..');
    const editButton = governingLawRow.getByRole('button', { name: /edit/i }).or(
      page.getByRole('button', { name: /edit/i }).last()
    );
    await editButton.click();

    // Verify input appears
    const input = page.getByRole('textbox').last().or(page.locator('input[type="text"]').last());
    await expect(input).toBeVisible();

    // Clear and enter new value
    await input.clear();
    await input.fill('State of Delaware');

    // Save the edit
    const saveButton = page.getByRole('button', { name: /save|confirm|check/i }).last();

    const responsePromise = page.waitForResponse(
      (r: any) => r.url().includes(`/extract/${extractedDoc.id}/results`) && r.request().method() === 'PUT'
    );

    await saveButton.click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
  });

  test('AC-5: proceed button disabled with message when unreviewed fields exist', async ({ page }) => {
    await mockExtractionRoutes(page, extractedDoc.id);

    await page.goto(`/documents/${extractedDoc.id}/extract`);

    // Find the proceed button
    const proceedButton = page.getByRole('button', { name: /save.*proceed.*summary|proceed.*summary/i });
    await expect(proceedButton).toBeVisible();
    await expect(proceedButton).toBeDisabled();

    // Verify the warning message
    await expect(page.getByText(/review all flagged fields/i)).toBeVisible();
  });

  test('AC-5 (success): proceed button enabled after all fields reviewed', async ({ page }) => {
    // Mock extraction results where all requires_review fields are reviewed
    const allReviewedValues = extractedValues.values.map((v) => ({
      ...v,
      reviewed: v.requires_review ? true : v.reviewed,
    }));

    await page.route(`${API_BASE}/documents/${extractedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(extractedDoc),
      });
    });

    await page.route(`${API_BASE}/extract/${extractedDoc.id}/results`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(allReviewedValues),
      });
    });

    await page.goto(`/documents/${extractedDoc.id}/extract`);

    const proceedButton = page.getByRole('button', { name: /save.*proceed.*summary|proceed.*summary/i });
    await expect(proceedButton).toBeEnabled();

    await proceedButton.click();
    await expect(page).toHaveURL(`/documents/${extractedDoc.id}/summary`);
  });

  test('AC-6: extract button triggers extraction with loading state', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(classifiedDoc),
      });
    });

    await page.route(`${API_BASE}/extract/${classifiedDoc.id}/results`, (route) => {
      route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Not extracted yet"}' });
    });

    await page.route(`${API_BASE}/extract/${classifiedDoc.id}`, async (route) => {
      if (route.request().method() === 'POST') {
        await new Promise((resolve) => setTimeout(resolve, 500));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(extractedValues.values),
        });
      } else {
        route.continue();
      }
    });

    await page.goto(`/documents/${classifiedDoc.id}/extract`);

    const extractButton = page.getByRole('button', { name: /extract/i });
    await expect(extractButton).toBeVisible();
    await extractButton.click();

    // Verify results appear after loading
    await expect(page.getByText('Fund Name')).toBeVisible();
  });

  test('AC-6 (boundary): extract button disabled during loading', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(classifiedDoc),
      });
    });

    await page.route(`${API_BASE}/extract/${classifiedDoc.id}/results`, (route) => {
      route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Not extracted"}' });
    });

    await page.route(`${API_BASE}/extract/${classifiedDoc.id}`, async (route) => {
      if (route.request().method() === 'POST') {
        // Long delay to observe disabled state
        await new Promise((resolve) => setTimeout(resolve, 3000));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(extractedValues.values),
        });
      } else {
        route.continue();
      }
    });

    await page.goto(`/documents/${classifiedDoc.id}/extract`);

    const extractButton = page.getByRole('button', { name: /extract/i });
    await extractButton.click();

    // During loading, the button should be disabled
    await expect(extractButton).toBeDisabled();
  });
});
