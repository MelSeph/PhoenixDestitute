import { test, expect } from '@playwright/test';

async function enterCreation(page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Create new account', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill(`django-${Date.now()}`);
  await page.getByLabel('Email address', { exact: true }).fill(`django-${Date.now()}@example.test`);
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByLabel('Confirm password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
}

test('real birth draft, locks, resource previews, and rerolls persist through Django sessions', async ({ page }) => {
  const playerCalls = [];
  page.on('request', request => { if (request.url().includes('/api/player/')) playerCalls.push(request.url()); });
  await enterCreation(page);
  await expect(page.getByRole('button', { name: 'Roll starting attributes', exact: true })).toBeVisible();
  expect((await page.request.get('/api/creation/stats/')).status()).toBe(404);
  const creation = page.waitForResponse(response => response.url().endsWith('/api/creation/stats/') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  const response = await creation;
  expect(response.status()).toBe(201);
  const initial = (await response.json()).draft;
  for (const parent of ['Strength', 'Intelligence', 'Endurance']) {
    await page.getByRole('checkbox', { name: `Lock ${parent}`, exact: true }).click();
    await expect(page.getByRole('checkbox', { name: `Lock ${parent}`, exact: true })).toBeChecked();
    await expect(page.getByRole('checkbox', { name: `Lock ${parent}`, exact: true })).toBeEnabled();
  }
  await expect(page.getByText('3 of 3 attributes locked.', { exact: false })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: 'Lock Luck', exact: true })).toBeDisabled();
  for (const resource of ['health', 'mana', 'stamina']) {
    const label = resource[0].toUpperCase() + resource.slice(1);
    await expect(page.getByLabel(`${label} preview`, { exact: true })).toHaveText(`${initial.resources[resource].current} / ${initial.resources[resource].maximum}`);
  }
  const reroll = page.waitForResponse(response => response.url().endsWith('/api/creation/stats/reroll/'));
  await page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true }).click();
  const rolled = (await (await reroll).json()).draft;
  expect(rolled.draft_id).toBe(initial.draft_id);
  expect(rolled.revision).not.toBe(initial.revision);
  for (const key of ['strength', 'intelligence', 'endurance']) expect(rolled.stats[key]).toBe(initial.stats[key]);
  await page.reload();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: 'Lock Strength', exact: true })).toBeChecked();
  expect((await (await page.request.get('/api/creation/stats/')).json()).draft).toEqual(rolled);
  expect(playerCalls).toEqual([]);
  expect((await page.request.get('/api/player/')).status()).toBe(404);
});

test('existing character sessions can prepare a birth draft without changing their character', async ({ page }) => {
  await page.request.get('/prototype/');
  const token = (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value;
  const created = await page.request.post('/api/player/create/', { headers: { 'X-CSRFToken': token } });
  const original = (await created.json()).player;
  await enterCreation(page);
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: 'Lock Strength', exact: true })).toBeVisible();
  expect((await (await page.request.get('/api/characters/')).json()).characters.map(entry => entry.name)).toContain(original.name);
  await expect(page.getByRole('button', { name: 'Create local character', exact: true })).not.toBeVisible();
});
