import { test, expect, chromium } from '@playwright/test';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

test('closing and reopening a real browser profile preserves saved-character ownership', async () => {
  const profile = await mkdtemp(join(tmpdir(), 'phoenix-browser-restart-'));
  const options = { channel: 'msedge', headless: true };
  let context = await chromium.launchPersistentContext(profile, options);
  let entry;
  const username = `restart-${Date.now()}`;
  const password = 'A-Secure-Player-Password-938!';
  try {
    await context.request.get('http://127.0.0.1:5173/prototype/');
    const csrf = (await context.cookies()).find(cookie => cookie.name === 'csrftoken').value;
    await context.request.post('http://127.0.0.1:5173/api/player/create/', { headers: { 'X-CSRFToken': csrf } });
    const page = await context.newPage();
    await page.goto('http://127.0.0.1:5173/');
    await page.getByRole('button', { name: 'Create new account', exact: true }).click();
    await page.getByLabel('Username', { exact: true }).fill(username);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByLabel('Confirm password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Create account', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Load Adventurer', exact: true })).toBeVisible();
    entry = (await (await context.request.get('http://127.0.0.1:5173/api/characters/')).json()).characters[0];
    await page.getByRole('button', { name: 'Load Adventurer', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Welcome back, Adventurer', exact: true })).toBeVisible();
    const cookie = (await context.cookies()).find(cookie => cookie.name === 'sessionid');
    expect(cookie.expires).toBeGreaterThan(Date.now() / 1000);
    expect(cookie.httpOnly).toBe(true);
  } finally { await context.close(); }
  context = await chromium.launchPersistentContext(profile, options);
  try {
    const page = await context.newPage();
    await page.goto('http://127.0.0.1:5173/');
    await expect(page.getByLabel('Username', { exact: true })).toBeVisible();
    await page.getByLabel('Username', { exact: true }).fill(username);
    await page.getByLabel('Password', { exact: true }).fill(password);
    await page.getByRole('button', { name: 'Sign in', exact: true }).last().click();
    await expect(page.getByRole('button', { name: 'Load Adventurer', exact: true })).toBeVisible();
    await page.getByRole('button', { name: 'Load Adventurer', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Welcome back, Adventurer', exact: true })).toBeVisible();
    const roster = (await (await context.request.get('http://127.0.0.1:5173/api/characters/')).json()).characters;
    expect(roster).toHaveLength(1);
    expect(roster[0].id).toBe(entry.id);
  } finally { await context.close(); }
});
