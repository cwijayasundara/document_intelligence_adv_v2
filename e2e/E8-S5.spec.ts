import { test, expect } from '@playwright/test';
import documents from '../specs/test_artefacts/test-data/documents.json';
import categories from '../specs/test_artefacts/test-data/categories.json';

const API_BASE = 'http://localhost:8000/api/v1';
const ingestedDoc = documents[0]; // doc_001: status=ingested

const sampleRagResponse = {
  answer:
    'The management fee rate for Horizon Equity Partners IV is 1.75% of Capital Commitments during the Commitment Period, reduced to 1.50% of invested capital after the Commitment Period expires.',
  citations: [
    {
      chunk_text:
        'During the Commitment Period, each Limited Partner shall pay an annual management fee equal to 1.75% of its Capital Commitment. Following the expiration of the Commitment Period, the management fee shall be reduced to 1.50% of invested capital.',
      document_name: 'Horizon_Equity_Partners_IV_LPA.pdf',
      document_id: 'doc_001',
      relevance_score: 0.94,
    },
    {
      chunk_text:
        'Management fees shall be payable quarterly in advance, calculated on a 365-day basis. The first management fee payment shall be prorated from the date of the Initial Closing.',
      document_name: 'Horizon_Equity_Partners_IV_LPA.pdf',
      document_id: 'doc_001',
      relevance_score: 0.78,
    },
  ],
};

test.describe('E8-S5: RAG Chat Page with Citations', () => {

  test.beforeEach(async ({ page }) => {
    await page.route(`${API_BASE}/documents/${ingestedDoc.id}`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ingestedDoc),
      });
    });

    await page.route(`${API_BASE}/config/categories`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(categories),
      });
    });
  });

  test('AC-1: chat page renders conversation interface with input field', async ({ page }) => {
    await page.goto(`/documents/${ingestedDoc.id}/chat`);

    // Verify input field for typing queries
    const input = page.getByRole('textbox').or(page.getByPlaceholder(/ask|query|question|type/i));
    await expect(input).toBeVisible();

    // Verify submit button
    const submitButton = page.getByRole('button', { name: /send|submit|ask/i });
    await expect(submitButton).toBeVisible();
  });

  test('AC-2: scope selector with This Document default and category dropdown', async ({ page }) => {
    await page.goto(`/documents/${ingestedDoc.id}/chat`);

    // Verify "This Document" is default scope
    await expect(page.getByText(/this document/i)).toBeVisible();

    // Verify "All Documents" option exists
    await expect(page.getByText(/all documents/i)).toBeVisible();

    // Select "By Category" and verify category dropdown appears
    const byCategoryOption = page.getByText(/by category/i);
    await expect(byCategoryOption).toBeVisible();
    await byCategoryOption.click();

    // Category dropdown should now be visible
    const categoryDropdown = page.getByRole('combobox').or(page.getByLabel(/category/i));
    await expect(categoryDropdown).toBeVisible();
  });

  test('AC-3: search mode toggle with Semantic, Keyword, Hybrid options', async ({ page }) => {
    await page.goto(`/documents/${ingestedDoc.id}/chat`);

    // Verify all three search mode options
    await expect(page.getByText(/semantic/i)).toBeVisible();
    await expect(page.getByText(/keyword/i)).toBeVisible();
    await expect(page.getByText(/hybrid/i)).toBeVisible();

    // Verify hybrid is the default (could be checked via aria-selected or visual indicator)
    // Click each mode to verify they are interactive
    await page.getByText(/semantic/i).click();
    await page.getByText(/keyword/i).click();
    await page.getByText(/hybrid/i).click();
  });

  test('AC-4: query submission renders AI response with expandable citation cards', async ({ page }) => {
    await page.route(`${API_BASE}/rag/query`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(sampleRagResponse),
      });
    });

    await page.goto(`/documents/${ingestedDoc.id}/chat`);

    // Type query
    const input = page.getByRole('textbox').or(page.getByPlaceholder(/ask|query|question|type/i));
    await input.fill('What is the management fee rate?');

    // Submit
    const submitButton = page.getByRole('button', { name: /send|submit|ask/i });
    await submitButton.click();

    // Verify AI answer displayed
    await expect(page.getByText(/1\.75% of Capital Commitments/i)).toBeVisible();

    // Verify citations are present
    await expect(page.getByText(/Horizon_Equity_Partners_IV_LPA\.pdf/i).first()).toBeVisible();

    // Verify relevance score shown
    await expect(page.getByText(/0\.94|94%/i)).toBeVisible();

    // Expand a citation card to see chunk text
    const citationCard = page.getByText(/Horizon_Equity_Partners_IV_LPA\.pdf/i).first().locator('..');
    await citationCard.click();

    // Verify chunk text is visible in expanded citation
    await expect(page.getByText(/payable quarterly in advance/i).or(
      page.getByText(/annual management fee equal to 1\.75%/i)
    )).toBeVisible();
  });

  test('AC-5: multi-turn conversation maintains chat history within session', async ({ page }) => {
    let queryCount = 0;

    await page.route(`${API_BASE}/rag/query`, (route) => {
      queryCount++;
      const responses: Record<number, any> = {
        1: {
          answer: 'The management fee is 1.75% during the commitment period.',
          citations: [sampleRagResponse.citations[0]],
        },
        2: {
          answer: 'The carried interest rate is 20% of net profits, subject to the 8% preferred return hurdle.',
          citations: [
            {
              chunk_text: 'The General Partner shall be entitled to receive a carried interest allocation equal to twenty percent (20%) of the net profits.',
              document_name: 'Horizon_Equity_Partners_IV_LPA.pdf',
              document_id: 'doc_001',
              relevance_score: 0.91,
            },
          ],
        },
      };
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(responses[queryCount] || responses[1]),
      });
    });

    await page.goto(`/documents/${ingestedDoc.id}/chat`);

    const input = page.getByRole('textbox').or(page.getByPlaceholder(/ask|query|question|type/i));
    const submitButton = page.getByRole('button', { name: /send|submit|ask/i });

    // First query
    await input.fill('What is the management fee?');
    await submitButton.click();
    await expect(page.getByText(/1\.75% during the commitment period/i)).toBeVisible();

    // Second query
    await input.fill('What is the carried interest rate?');
    await submitButton.click();
    await expect(page.getByText(/20% of net profits/i)).toBeVisible();

    // Verify both exchanges are visible in chat history
    await expect(page.getByText(/What is the management fee/i)).toBeVisible();
    await expect(page.getByText(/What is the carried interest rate/i)).toBeVisible();
  });

  test('AC-4 (boundary): empty query submission prevented', async ({ page }) => {
    await page.goto(`/documents/${ingestedDoc.id}/chat`);

    const submitButton = page.getByRole('button', { name: /send|submit|ask/i });

    // Submit with empty input
    await submitButton.click();

    // Either button is disabled or validation message shown
    const isDisabled = await submitButton.isDisabled();
    const validationVisible = await page.getByText(/enter.*query|cannot be empty|required/i).isVisible();

    expect(isDisabled || validationVisible).toBeTruthy();
  });
});
