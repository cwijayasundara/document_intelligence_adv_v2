import { test, expect } from '@playwright/test';
import documents from '../specs/test_artefacts/test-data/documents.json';
import categories from '../specs/test_artefacts/test-data/categories.json';

const API_BASE = 'http://localhost:8000/api/v1';
const parsedDoc = documents[3]; // doc_004: status=parsed
const classifiedDoc = documents[2]; // doc_003: status=classified

test.describe('E8-S2: Classification Page with Override', () => {

  test.beforeEach(async ({ page }) => {
    // Mock categories list for dropdown
    await page.route(`${API_BASE}/config/categories`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(categories),
      });
    });
  });

  test('AC-1: classification page displays detected category and reasoning', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(classifiedDoc),
      });
    });

    await page.route(`${API_BASE}/classify/${classifiedDoc.id}`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            category_id: 'cat_003',
            category_name: 'Side Letter',
            reasoning: 'Document references a main LPA and is addressed to a specific LP. Contains fee discount provisions and most-favored-nation clauses typical of side letters.',
          }),
        });
      } else {
        route.continue();
      }
    });

    await page.goto(`/documents/${classifiedDoc.id}/classify`);

    // Verify category name displayed
    await expect(page.getByText('Side Letter')).toBeVisible();

    // Verify reasoning text displayed
    await expect(page.getByText(/references a main LPA/i)).toBeVisible();
  });

  test('AC-2: classify button triggers classification with loading state', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${parsedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(parsedDoc),
      });
    });

    await page.route(`${API_BASE}/classify/${parsedDoc.id}`, async (route) => {
      if (route.request().method() === 'POST') {
        await new Promise((resolve) => setTimeout(resolve, 500));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            category_id: 'cat_004',
            category_name: 'Other/Unclassified',
            reasoning: 'Document is an amendment to an existing LPA. It does not match the core categories with sufficient confidence.',
          }),
        });
      } else {
        route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"Not classified yet"}' });
      }
    });

    await page.goto(`/documents/${parsedDoc.id}/classify`);

    const classifyButton = page.getByRole('button', { name: /classify/i });
    await expect(classifyButton).toBeVisible();
    await classifyButton.click();

    // Verify result appears after loading
    await expect(page.getByText('Other/Unclassified')).toBeVisible();
    await expect(page.getByText(/amendment to an existing LPA/i)).toBeVisible();
  });

  test('AC-3: category override dropdown allows selecting a different category', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(classifiedDoc),
      });
    });

    await page.route(`${API_BASE}/classify/${classifiedDoc.id}`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            category_id: 'cat_003',
            category_name: 'Side Letter',
            reasoning: 'Detected as side letter.',
          }),
        });
      } else {
        route.continue();
      }
    });

    // Mock category update on document
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}/category`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ document_category_id: 'cat_001' }),
      });
    });

    await page.goto(`/documents/${classifiedDoc.id}/classify`);

    // Find and interact with the override dropdown
    const dropdown = page.getByRole('combobox').or(page.getByLabel(/category|override/i));
    await expect(dropdown).toBeVisible();

    // Select a different category
    await dropdown.selectOption({ label: 'Limited Partnership Agreement' }).catch(async () => {
      // If it's a custom dropdown, click and select
      await dropdown.click();
      await page.getByRole('option', { name: /Limited Partnership Agreement/i }).click();
    });
  });

  test('AC-4: Accept and Proceed saves and navigates to extract page', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(classifiedDoc),
      });
    });

    await page.route(`${API_BASE}/classify/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          category_id: 'cat_003',
          category_name: 'Side Letter',
          reasoning: 'Detected as side letter.',
        }),
      });
    });

    await page.goto(`/documents/${classifiedDoc.id}/classify`);

    const proceedButton = page.getByRole('button', { name: /accept.*proceed|proceed/i });
    await expect(proceedButton).toBeVisible();
    await proceedButton.click();

    await expect(page).toHaveURL(`/documents/${classifiedDoc.id}/extract`);
  });

  test('AC-5: page shows error or redirect for document with wrong status', async ({ page }) => {
    const uploadedDoc = documents[4]; // status=uploaded

    await page.route(`${API_BASE}/documents/${uploadedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(uploadedDoc),
      });
    });

    await page.goto(`/documents/${uploadedDoc.id}/classify`);

    // Should show 404, error message, or redirect
    const errorVisible = await page.getByText(/not found|not available|must be parsed/i).isVisible();
    const redirected = !page.url().includes('/classify');

    expect(errorVisible || redirected).toBeTruthy();
  });

  test('AC-1 (detail): reasoning text is readable and meaningful', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(classifiedDoc),
      });
    });

    const longReasoning = 'Document references a main LPA titled "Meridian Capital Partners Fund II, L.P." and is specifically addressed to LP-42 (Pacific Coast Pension Fund). The document contains fee discount provisions reducing management fees from 2.0% to 1.5%, a most-favored-nation clause in Section 3, and enhanced quarterly reporting requirements. These characteristics are strongly indicative of a Side Letter.';

    await page.route(`${API_BASE}/classify/${classifiedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          category_id: 'cat_003',
          category_name: 'Side Letter',
          reasoning: longReasoning,
        }),
      });
    });

    await page.goto(`/documents/${classifiedDoc.id}/classify`);

    await expect(page.getByText(/Meridian Capital Partners/i)).toBeVisible();
    await expect(page.getByText(/most-favored-nation/i)).toBeVisible();
  });
});
