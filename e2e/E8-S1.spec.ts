import { test, expect } from '@playwright/test';
import categories from '../specs/test_artefacts/test-data/categories.json';
import extractionFields from '../specs/test_artefacts/test-data/extraction_fields.json';

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('E8-S1: Config Management Pages', () => {

  test.beforeEach(async ({ page }) => {
    // Mock categories API
    await page.route(`${API_BASE}/config/categories`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(categories),
        });
      } else {
        route.continue();
      }
    });
  });

  test('AC-1: category manager displays all categories in card list', async ({ page }) => {
    await page.goto('/config/categories');

    // Verify each category is displayed
    for (const cat of categories) {
      await expect(page.getByText(cat.name)).toBeVisible();
    }

    // Verify edit and delete actions are present
    const editButtons = page.getByRole('button', { name: /edit/i });
    const deleteButtons = page.getByRole('button', { name: /delete/i });
    expect(await editButtons.count()).toBeGreaterThanOrEqual(categories.length);
    expect(await deleteButtons.count()).toBeGreaterThanOrEqual(1);
  });

  test('AC-2: add category modal with required fields', async ({ page }) => {
    // Mock create
    await page.route(`${API_BASE}/config/categories`, (route) => {
      if (route.request().method() === 'POST') {
        route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'cat_new_001',
            name: 'Amendment',
            description: 'Fund amendment documents',
            classification_criteria: 'Contains amendment provisions',
          }),
        });
      } else {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(categories),
        });
      }
    });

    await page.goto('/config/categories');

    // Click add category button
    await page.getByRole('button', { name: /add.*category|new.*category|create/i }).click();

    // Verify modal fields
    await expect(page.getByLabel(/name/i)).toBeVisible();
    await expect(page.getByLabel(/description/i)).toBeVisible();
    await expect(page.getByLabel(/classification.*criteria|criteria/i)).toBeVisible();

    // Fill and submit
    await page.getByLabel(/name/i).fill('Amendment');
    await page.getByLabel(/description/i).fill('Fund amendment documents');
    await page.getByLabel(/classification.*criteria|criteria/i).fill('Contains amendment provisions');

    const submitButton = page.getByRole('button', { name: /save|create|submit/i });
    await submitButton.click();

    // Verify new category appears
    await expect(page.getByText('Amendment')).toBeVisible();
  });

  test('AC-2 (edit): edit category modal updates existing category', async ({ page }) => {
    await page.route(`${API_BASE}/config/categories/${categories[0].id}`, (route) => {
      if (route.request().method() === 'PUT') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...categories[0], name: 'Updated LPA Category' }),
        });
      } else {
        route.continue();
      }
    });

    await page.goto('/config/categories');

    // Click edit on first category
    const firstCategoryCard = page.getByText(categories[0].name).locator('..');
    const editButton = firstCategoryCard.getByRole('button', { name: /edit/i }).or(
      page.getByRole('button', { name: /edit/i }).first()
    );
    await editButton.click();

    // Modify name
    const nameField = page.getByLabel(/name/i);
    await nameField.clear();
    await nameField.fill('Updated LPA Category');

    await page.getByRole('button', { name: /save|update|submit/i }).click();
  });

  test('AC-3: delete category shows confirmation and succeeds when no documents assigned', async ({ page }) => {
    // Category cat_004 (Other/Unclassified) has no documents assigned in test data
    const emptyCategory = categories[3];

    await page.route(`${API_BASE}/config/categories/${emptyCategory.id}`, (route) => {
      if (route.request().method() === 'DELETE') {
        route.fulfill({ status: 204 });
      } else {
        route.continue();
      }
    });

    await page.goto('/config/categories');

    // Find delete button for the empty category
    const categoryCard = page.getByText(emptyCategory.name).locator('..');
    const deleteButton = categoryCard.getByRole('button', { name: /delete/i }).or(
      page.getByRole('button', { name: /delete/i }).last()
    );
    await deleteButton.click();

    // Verify confirmation dialog
    await expect(page.getByText(/confirm|are you sure/i)).toBeVisible();

    // Confirm deletion
    await page.getByRole('button', { name: /confirm|yes|delete/i }).click();
  });

  test('AC-3 (error): delete disabled for category with assigned documents', async ({ page }) => {
    await page.goto('/config/categories');

    // Categories with assigned documents should have delete disabled or show warning
    // cat_001 (LPA) has doc_001 assigned
    const lpaCard = page.getByText(categories[0].name).locator('..');
    const deleteButton = lpaCard.getByRole('button', { name: /delete/i }).or(
      page.getByRole('button', { name: /delete/i }).first()
    );

    // The button should either be disabled or clicking it should show an error
    if (await deleteButton.isDisabled()) {
      await expect(deleteButton).toBeDisabled();
    } else {
      await deleteButton.click();
      await expect(page.getByText(/cannot delete|has documents|assigned/i)).toBeVisible();
    }
  });

  test('AC-4: extraction field editor shows fields grouped by category', async ({ page }) => {
    await page.route(`${API_BASE}/config/categories/${categories[0].id}/fields`, (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(extractionFields.fields),
      });
    });

    await page.goto('/config/extraction-fields');

    // Verify fields are grouped under category name
    await expect(page.getByText(extractionFields.category_name)).toBeVisible();

    // Verify some extraction fields are visible
    await expect(page.getByText('Fund Name')).toBeVisible();
    await expect(page.getByText('General Partner')).toBeVisible();
    await expect(page.getByText('Management Fee Rate')).toBeVisible();
  });

  test('AC-5: add extraction field form with all required inputs', async ({ page }) => {
    await page.route(`${API_BASE}/config/categories/${categories[0].id}/fields`, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(extractionFields.fields),
        });
      } else if (route.request().method() === 'POST') {
        route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify([
            ...extractionFields.fields,
            {
              id: 'field_009',
              field_name: 'clawback_provision',
              display_name: 'Clawback Provision',
              description: 'GP clawback terms',
              examples: 'Full clawback',
              data_type: 'string',
              required: false,
              sort_order: 9,
            },
          ]),
        });
      }
    });

    await page.goto('/config/extraction-fields');

    // Click add field button
    await page.getByRole('button', { name: /add.*field|new.*field/i }).first().click();

    // Verify form fields
    await expect(page.getByLabel(/field.*name/i).first()).toBeVisible();
    await expect(page.getByLabel(/display.*name/i)).toBeVisible();
    await expect(page.getByLabel(/description/i)).toBeVisible();
    await expect(page.getByLabel(/examples/i)).toBeVisible();

    // Verify data_type dropdown exists
    const dataTypeSelect = page.getByLabel(/data.*type|type/i).or(page.getByRole('combobox'));
    await expect(dataTypeSelect).toBeVisible();

    // Verify required checkbox
    await expect(page.getByLabel(/required/i)).toBeVisible();
  });
});
