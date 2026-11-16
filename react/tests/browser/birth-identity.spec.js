import { test, expect } from '@playwright/test';

async function start(page, { mobile = false } = {}) {
  await page.goto('/');
  if (mobile) {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.locator('.options-toggle').click();
    await page.getByLabel('Text Size', { exact: true }).selectOption('200');
  }
  await page.getByRole('button', { name: 'Create new account', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill(`identity-${Date.now()}`);
  await page.getByLabel('Email address', { exact: true }).fill(`identity-${Date.now()}@example.test`);
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByLabel('Confirm password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  const response = page.waitForResponse(response => response.url().endsWith('/api/creation/stats/') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  return (await (await response).json()).draft;
}
async function pick(page, group, option) {
  await page.getByRole('group', { name: group, exact: true }).getByRole('radio', { name: option, exact: true }).check();
}
async function fill(page, { bald = false, custom = false } = {}) {
  await page.getByLabel('Name', { exact: true }).fill('Ash');
  await page.getByLabel('Gender', { exact: true }).selectOption(custom ? 'custom' : 'nonbinary');
  if (custom) await page.getByLabel('Custom gender label', { exact: true }).fill('My identity');
  await pick(page, 'Skin tone', 'Dark brown');
  await pick(page, 'Eye color', 'Green');
  await pick(page, 'Hair length', bald ? 'Bald' : 'Long');
  if (!bald) { await pick(page, 'Hair color', 'Red'); await pick(page, 'Hair texture', 'Curly'); }
}
async function save(page) {
  await page.getByRole('button', { name: 'Save identity and looks', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save identity and looks', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Review birth', exact: true })).toBeEnabled();
}

test('every color choice has its matching visual and every hair length has an illustration', async ({ page }, testInfo) => {
  const initial = await start(page);
  for (const [key, label] of [['skin_tone', 'Skin tone'], ['eye_color', 'Eye color'], ['hair_color', 'Hair color']]) {
    const group = page.getByRole('group', { name: label, exact: true });
    for (const option of initial.identity_options[key]) {
      const card = group.locator('label').filter({ has: page.getByRole('radio', { name: option.label, exact: true }) });
      await expect(card.locator('[data-color]')).toHaveAttribute('data-color', option.color);
      await expect(card.locator('[data-color]')).toBeVisible();
      await card.getByRole('radio').check();
    }
  }
  const group = page.getByRole('group', { name: 'Hair length', exact: true });
  for (const option of initial.identity_options.hair_length) {
    await expect(group.locator(`[data-hair-length="${option.value}"]`)).toBeVisible();
  }
  await fill(page);
  await page.locator('.birth-identity').screenshot({ path: testInfo.outputPath('visual-choices.png') });
});

test('saved identity survives rolls and refresh; review is read-only and confirmation freezes the birth', async ({ page }, testInfo) => {
  const initial = await start(page);
  await fill(page);
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).toBeDisabled();
  await save(page);
  const saved = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  expect(saved.stats).toEqual(initial.stats);
  expect(saved.resources).toEqual(initial.resources);
  await page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).toBeEnabled();
  await page.reload();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  await expect(page.getByLabel('Name', { exact: true })).toHaveValue('Ash');
  await expect(page.getByRole('group', { name: 'Hair length', exact: true }).getByRole('radio', { name: 'Long', exact: true })).toBeChecked();
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Ash');
  await expect(page.getByRole('dialog')).toContainText('Nonbinary');
  await expect(page.getByRole('dialog').locator('[data-color]')).toHaveCount(3);
  await page.getByRole('button', { name: 'Back to choices', exact: true }).click();
  expect((await (await page.request.get('/api/player/')).status())).toBe(404);
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  const confirm = page.waitForResponse(response => response.url().endsWith('/api/creation/stats/confirm/'));
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).click();
  const result = await confirm;
  expect(result.status()).toBe(201);
  const confirmed = (await result.json()).draft;
  await page.getByRole('button', { name: 'Show character sheet', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ash · Nonbinary · Newborn', exact: true })).toBeVisible();
  await expect(page.getByText(`Character ID: ${confirmed.birth.character_id}`, { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Review birth', exact: true })).not.toBeVisible();
  const repeated = await page.request.post('/api/creation/stats/confirm/', {
    headers: { 'X-CSRFToken': (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value }, data: { revision: confirmed.revision },
  });
  expect(repeated.status()).toBe(200);
  expect((await repeated.json()).draft).toEqual(confirmed);
  await page.reload();
  await page.getByRole('button', { name: 'Show character sheet', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ash · Nonbinary · Newborn', exact: true })).toBeVisible();
  await page.locator('.birth-creation').screenshot({ path: testInfo.outputPath('confirmed-birth.png') });
});

test('bald selection clears irrelevant choices and custom gender is reviewed and saved', async ({ page }) => {
  await start(page);
  await fill(page, { custom: true });
  await pick(page, 'Hair length', 'Bald');
  await expect(page.getByRole('group', { name: 'Hair color', exact: true })).not.toBeVisible();
  await expect(page.getByRole('group', { name: 'Hair texture', exact: true })).not.toBeVisible();
  await save(page);
  const selected = (await (await page.request.get('/api/creation/stats/')).json()).draft.identity;
  expect(selected.hair_color).toBe(''); expect(selected.hair_texture).toBe('');
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('My identity');
  await expect(page.getByRole('dialog')).toContainText('Bald');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Review birth', exact: true })).toBeFocused();
});

test('a stale review cannot confirm changes made in another tab', async ({ page }) => {
  await start(page); await fill(page); await save(page);
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  const latest = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  await page.request.post('/api/creation/stats/reroll/', { data: { revision: latest.revision }, headers: { 'X-CSRFToken': (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value } });
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.getByText(/latest values are loaded/)).toBeVisible();
  expect((await page.request.get('/api/player/')).status()).toBe(404);
});

test('lost confirmation response recovers the confirmed birth without another POST', async ({ page }) => {
  await start(page); await fill(page, { bald: true }); await save(page);
  let confirmations = 0;
  await page.route('**/api/creation/stats/confirm/', async route => {
    confirmations++;
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    await route.abort('failed');
  });
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('Reload the draft before trying again');
  await expect(page.getByRole('button', { name: 'Confirm birth', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Back to choices', exact: true }).click();
  await page.getByRole('button', { name: 'Reload draft', exact: true }).click();
  await page.getByRole('button', { name: 'Show character sheet', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ash · Nonbinary · Newborn', exact: true })).toBeVisible();
  expect(confirmations).toBe(1);
});

test('visual identity choices and review fit mobile at 200% text with keyboard access', async ({ page }, testInfo) => {
  await start(page, { mobile: true });
  await fill(page, { bald: true });
  await save(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  const dialog = page.getByRole('dialog');
  expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  await dialog.screenshot({ path: testInfo.outputPath('mobile-review.png') });
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).focus();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Back to choices', exact: true })).toBeFocused();
});

test('an older character is retained while another character is created', async ({ page }) => {
  await page.request.get('/prototype/');
  const token = (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value;
  const original = await page.request.post('/api/player/create/', { headers: { 'X-CSRFToken': token } });
  const originalPlayer = (await original.json()).player;
  await start(page); await fill(page, { bald: true });
  await page.getByRole('button', { name: 'Save identity and looks', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Save identity and looks', exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Review birth', exact: true })).toBeEnabled();
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'You wake up in your crib', exact: true })).toBeVisible();
  const roster = (await (await page.request.get('/api/characters/')).json()).characters;
  expect(roster.map(character => character.name).sort()).toEqual(['Adventurer', 'Ash']);
  expect(roster.some(character => character.name === originalPlayer.name)).toBe(true);
});
