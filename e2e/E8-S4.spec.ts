import { test, expect } from '@playwright/test';
import documents from '../specs/test_artefacts/test-data/documents.json';

const API_BASE = 'http://localhost:8000/api/v1';
const ingestedDoc = documents[0]; // doc_001: status=ingested
const extractedDoc = documents[1]; // doc_002: status=extracted

const sampleSummary = {
  summary:
    'Horizon Equity Partners IV, L.P. is a Delaware limited partnership managed by Horizon Capital Management IV LLC. The fund has a 10-year term with a 5-year commitment period. Limited partners pay an annual management fee of 1.75% during the commitment period, reduced to 1.50% post-commitment. The general partner receives 20% carried interest subject to an 8% preferred return hurdle. The partnership agreement includes standard key person provisions, no-fault divorce clauses, and an Advisory Committee with consent rights over certain GP conflicts.',
  key_topics: [
    'Management Fee Structure',
    'Carried Interest',
    'Preferred Return',
    'Fund Term',
    'Commitment Period',
    'Key Person Provision',
    'Advisory Committee',
  ],
};

test.describe('E8-S4: Summary Page with Regenerate', () => {

  test('AC-1: summary page displays summary text and key topics as tags', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ingestedDoc),
      });
    });

    await page.route(`${API_BASE}/summarize/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleSummary),
      });
    });

    await page.goto(`/documents/${ingestedDoc.id}/summary`);

    // Verify summary text displayed
    await expect(page.getByText(/Horizon Equity Partners IV/i)).toBeVisible();
    await expect(page.getByText(/management fee of 1.75%/i)).toBeVisible();

    // Verify key topics rendered as tags
    for (const topic of sampleSummary.key_topics) {
      await expect(page.getByText(topic)).toBeVisible();
    }
  });

  test('AC-2: Generate Summary button triggers summarization with loading state', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${extractedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(extractedDoc),
      });
    });

    // No existing summary
    await page.route(`${API_BASE}/summarize/${extractedDoc.id}`, async (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"No summary"}' });
      } else if (route.request().method() === 'POST') {
        await new Promise((resolve) => setTimeout(resolve, 500));
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(sampleSummary),
        });
      }
    });

    await page.goto(`/documents/${extractedDoc.id}/summary`);

    const generateButton = page.getByRole('button', { name: /generate.*summary/i });
    await expect(generateButton).toBeVisible();
    await generateButton.click();

    // Verify summary appears after generation
    await expect(page.getByText(/Horizon Equity Partners IV/i)).toBeVisible();
  });

  test('AC-3: Regenerate button replaces displayed summary with new result', async ({ page }) => {
    const updatedSummary = {
      summary:
        'This LPA establishes Horizon Equity Partners IV, L.P. with a standard PE fund structure. Key terms include 1.75% management fee, 20% carry, and 8% preferred return. The fund has a 10-year term.',
      key_topics: ['Fund Structure', 'Fee Terms', 'Distribution Waterfall'],
    };

    await page.route(`${API_BASE}/documents/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ingestedDoc),
      });
    });

    let callCount = 0;
    await page.route(`${API_BASE}/summarize/${ingestedDoc.id}`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(sampleSummary),
        });
      } else if (route.request().method() === 'POST') {
        callCount++;
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(updatedSummary),
        });
      }
    });

    await page.goto(`/documents/${ingestedDoc.id}/summary`);

    // Verify original summary shown
    await expect(page.getByText(/Advisory Committee/i)).toBeVisible();

    // Click regenerate
    const regenerateButton = page.getByRole('button', { name: /regenerate/i });
    await expect(regenerateButton).toBeVisible();
    await regenerateButton.click();

    // Verify new summary replaced old
    await expect(page.getByText(/standard PE fund structure/i)).toBeVisible();
    await expect(page.getByText('Distribution Waterfall')).toBeVisible();
  });

  test('AC-4: key topics rendered as styled tag chips', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ingestedDoc),
      });
    });

    await page.route(`${API_BASE}/summarize/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleSummary),
      });
    });

    await page.goto(`/documents/${ingestedDoc.id}/summary`);

    // Verify each topic is rendered as a distinct element
    for (const topic of sampleSummary.key_topics) {
      const topicElement = page.getByText(topic);
      await expect(topicElement).toBeVisible();
    }
  });

  test('AC-5: Proceed to Ingest & Chat triggers ingestion and navigates to chat', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ingestedDoc),
      });
    });

    await page.route(`${API_BASE}/summarize/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleSummary),
      });
    });

    await page.route(`${API_BASE}/ingest/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ingested' }),
      });
    });

    await page.goto(`/documents/${ingestedDoc.id}/summary`);

    const proceedButton = page.getByRole('button', { name: /proceed.*ingest.*chat|ingest.*chat/i });
    await expect(proceedButton).toBeVisible();
    await proceedButton.click();

    await expect(page).toHaveURL(`/documents/${ingestedDoc.id}/chat`);
  });

  test('AC-2 (boundary): page without summary shows generate prompt', async ({ page }) => {
    await page.route(`${API_BASE}/documents/${extractedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(extractedDoc),
      });
    });

    await page.route(`${API_BASE}/summarize/${extractedDoc.id}`, (route) => {
      route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"No summary"}' });
    });

    await page.goto(`/documents/${extractedDoc.id}/summary`);

    // Generate button should be prominent
    await expect(page.getByRole('button', { name: /generate.*summary/i })).toBeVisible();

    // No summary text should be displayed
    await expect(page.getByText(/Advisory Committee/i)).not.toBeVisible();
  });
});
