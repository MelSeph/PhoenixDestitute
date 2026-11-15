import { test, expect } from '@playwright/test';

test('real Django session and CSRF survive the Vite proxy and a reload', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('No local character yet.', { exact: true })).toBeVisible();
  const creation = page.waitForResponse(response => response.url().endsWith('/api/player/create/'));
  await page.getByRole('button', { name: 'Create local character', exact: true }).click();
  expect((await creation).status()).toBe(201);
  await expect(page.getByText('Adventurer — Level 1 — Experience 0')).toBeVisible();
  await page.reload();
  await expect(page.getByText('Adventurer — Level 1 — Experience 0')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create local character', exact: true })).not.toBeVisible();
});
