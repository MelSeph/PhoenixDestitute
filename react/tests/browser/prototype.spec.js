import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/creation/stats/', route => route.fulfill({ status: 404, json: { error: 'No birth stat draft in this session.' } }));
  await page.goto('/');
});
async function options(page) { await page.locator('.options-toggle').click(); }
async function registerAndStart(page) {
  await page.getByRole('button', { name: 'Create new account', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill(`prototype-${Date.now()}`);
  await page.getByLabel('Email address', { exact: true }).fill(`prototype-${Date.now()}@example.test`);
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByLabel('Confirm password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
}

test('prototype layout, readability persistence, and independent resets', async ({ page }, testInfo) => {
  await expect(page.getByRole('heading', { name: 'PhoenixDestitute', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Appearance Settings' })).not.toBeVisible();
  await options(page);
  await page.screenshot({ path: testInfo.outputPath('desktop.png'), fullPage: true });
  await page.getByLabel('Color Theme').selectOption('daylight');
  await page.getByLabel('Text Size', { exact: true }).selectOption('150');
  await page.getByLabel('Word Spacing', { exact: true }).selectOption('wide');
  await expect(page.getByText('Customized preferences: 2 of 14')).toBeVisible();
  await page.reload(); await options(page);
  await expect(page.getByLabel('Text Size', { exact: true })).toHaveValue('150');
  await page.getByRole('button', { name: 'Reset Readability Settings', exact: true }).click();
  await expect(page.getByLabel('Color Theme')).toHaveValue('daylight');
  await expect(page.getByLabel('Text Size', { exact: true })).toHaveValue('100');
  await page.getByText('Live Appearance Summary', { exact: false }).filter({ has: page.locator('span') }).click();
  await expect(page.getByText('Summary display: Collapsed')).toBeVisible();
  await page.reload(); await options(page);
  await expect(page.getByText('Summary display: Collapsed')).toBeVisible();
});
test('custom picker validates contrast, cancels with Escape, and returns focus', async ({ page }) => {
  await options(page);
  await page.getByLabel('Color Theme').selectOption('custom');
  const trigger = page.getByRole('button', { name: 'Choose accent color', exact: true });
  await trigger.click();
  await page.getByLabel('Hexadecimal color').fill('#202d3a');
  await page.getByRole('button', { name: 'Apply color', exact: true }).click();
  await expect(page.getByText(/reduce contrast/)).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page.getByLabel('Hexadecimal color').fill('#ffffff');
  await page.getByRole('button', { name: 'Apply color', exact: true }).click();
  await expect(trigger).toContainText('#ffffff');
});
test('import review cancellation, confirmation, undo, and malformed backup rejection', async ({ page }) => {
  await options(page);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export Appearance Settings', exact: true }).click();
  const downloaded = await downloadPromise;
  expect(downloaded.suggestedFilename()).toBe('phoenixdestitute-appearance-backup.json');
  const path = await downloaded.path();
  await page.getByLabel('Color Theme').selectOption('daylight');
  await page.getByLabel('Appearance backup JSON file').setInputFiles(path);
  await page.getByRole('button', { name: 'Import Appearance Settings', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Changed from Daylight');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByLabel('Color Theme')).toHaveValue('daylight');
  await page.getByRole('button', { name: 'Import Appearance Settings', exact: true }).click();
  await page.getByRole('button', { name: 'Import these settings' }).click();
  await expect(page.getByLabel('Color Theme')).toHaveValue('midnight');
  await page.getByRole('button', { name: 'Undo Last Import' }).click();
  await expect(page.getByLabel('Color Theme')).toHaveValue('daylight');
  await expect(page.getByRole('button', { name: 'Undo Last Import' })).toBeDisabled();
  await page.getByLabel('Appearance backup JSON file').setInputFiles({ name: 'invalid.json', mimeType: 'application/json', buffer: Buffer.from('{}') });
  await page.getByRole('button', { name: 'Import Appearance Settings', exact: true }).click();
  await expect(page.getByText(/Could not import:/)).toBeVisible();
  await expect(page.getByLabel('Color Theme')).toHaveValue('daylight');
});
test('mobile layout fits at 200% text and modal traps keyboard focus', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await options(page);
  await page.getByLabel('Text Size', { exact: true }).selectOption('200');
  await page.getByLabel('Color Theme').selectOption('custom');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('mobile.png'), fullPage: true });
  await page.getByRole('button', { name: 'Choose accent color', exact: true }).click();
  await page.getByRole('button', { name: 'Apply color', exact: true }).focus();
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement.closest('dialog') !== null)).toBe(true);
  await page.keyboard.press('Escape');
});
test('backend errors are visible and do not fabricate a birth draft', async ({ page }) => {
  await page.route('**/api/creation/stats/', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await registerAndStart(page);
  await page.getByRole('button', { name: 'Reload draft' }).click();
  await expect(page.getByText('Could not load your birth draft: HTTP 503')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Roll starting attributes', exact: true })).not.toBeVisible();
});
