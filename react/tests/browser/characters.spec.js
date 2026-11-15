import { test, expect } from '@playwright/test';

async function create(page, name) {
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill(name);
  await page.getByLabel('Gender', { exact: true }).selectOption('nonbinary');
  for (const [group, value] of [['Skin tone', 'Fair'], ['Eye color', 'Blue'], ['Hair length', 'Bald']]) {
    await page.getByRole('group', { name: group, exact: true }).getByRole('radio', { name: value, exact: true }).check();
  }
  await page.getByRole('button', { name: 'Save identity and looks', exact: true }).click();
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).click();
  await expect(page.getByRole('heading', { name: `${name} · Newborn`, exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: `Load ${name}`, exact: true })).toBeEnabled();
}

test('create two characters, load either, and retain the selection across refresh', async ({ page }, testInfo) => {
  await page.goto('/'); await create(page, 'Ash');
  const first = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  await page.getByRole('button', { name: 'New character', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Load Ash', exact: true })).toBeVisible();
  await create(page, 'Ember');
  const second = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  expect(second.birth.character_id).not.toBe(first.birth.character_id);
  await page.getByRole('button', { name: 'Load Ash', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ash · Newborn', exact: true })).toBeVisible();
  await expect(page.getByLabel('Strength value', { exact: true })).toHaveText(String(first.stats.strength));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Ash · Newborn', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Load Ember', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ember · Newborn', exact: true })).toBeVisible();
  await page.getByRole('region', { name: 'Your characters', exact: true }).screenshot({ path: testInfo.outputPath('character-list.png') });
});

test('delete requires the exact name, can be cancelled, and removes the selected character', async ({ page }) => {
  await page.goto('/'); await create(page, 'Ash');
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('This cannot be undone');
  await expect(page.getByRole('button', { name: 'Delete character', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Load Ash', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  await page.getByLabel('Type Ash to delete', { exact: true }).fill('ash');
  await expect(page.getByRole('button', { name: 'Delete character', exact: true })).toBeDisabled();
  await page.getByLabel('Type Ash to delete', { exact: true }).fill('Ash');
  await page.getByRole('button', { name: 'Delete character', exact: true }).click();
  await expect(page.getByText('No saved characters yet.', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Roll starting attributes', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Load Ash', exact: true })).not.toBeVisible();
});

test('deleting an inactive character keeps the loaded character available', async ({ page }) => {
  await page.goto('/'); await create(page, 'Ash');
  await page.getByRole('button', { name: 'New character', exact: true }).click(); await create(page, 'Ember');
  await page.getByRole('button', { name: 'Load Ember', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ember · Newborn', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Delete Ash?' })).toBeVisible();
  await page.getByLabel('Type Ash to delete', { exact: true }).fill('Ash');
  await page.getByRole('button', { name: 'Delete character', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Load Ash', exact: true })).not.toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ember · Newborn', exact: true })).toBeVisible();
});

test('an unfinished draft survives loading a character and choosing New character again', async ({ page }) => {
  await page.goto('/'); await create(page, 'Ash');
  await page.getByRole('button', { name: 'New character', exact: true }).click();
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).toBeEnabled();
  const draft = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  await page.getByRole('button', { name: 'Load Ash', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Ash · Newborn', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'New character', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).toBeEnabled();
  expect((await (await page.request.get('/api/creation/stats/')).json()).draft).toEqual(draft);
});

test('foreign sessions cannot see, load, or delete another roster entry', async ({ page, browser }) => {
  await page.goto('/'); await create(page, 'Ash');
  const entry = (await (await page.request.get('/api/characters/')).json()).characters[0];
  const other = await browser.newContext();
  const otherPage = await other.newPage();
  await otherPage.goto('http://127.0.0.1:5173/');
  await expect(otherPage.getByText('No saved characters yet.', { exact: true })).toBeVisible();
  await other.request.get('http://127.0.0.1:5173/prototype/');
  const token = (await other.cookies()).find(cookie => cookie.name === 'csrftoken').value;
  for (const [action, fields] of [['load', {}], ['delete', { confirmation_name: 'Ash' }]]) {
    const response = await other.request.post(`http://127.0.0.1:5173/api/characters/${action}/`, {
      data: { character_id: entry.id, ...fields }, headers: { 'X-CSRFToken': token },
    });
    expect(response.status()).toBe(404);
  }
  await other.close();
});

test('a lost delete response recovers through Reload characters without another delete', async ({ page }) => {
  await page.goto('/'); await create(page, 'Ash');
  let calls = 0;
  await page.route('**/api/characters/delete/', async route => { calls++; await route.fetch(); await route.abort('failed'); });
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  await page.getByLabel('Type Ash to delete', { exact: true }).fill('Ash');
  await page.getByRole('button', { name: 'Delete character', exact: true }).click();
  await expect(page.getByText(/Reload characters before trying again/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'New character', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload characters', exact: true }).click();
  await expect(page.getByText('No saved characters yet.', { exact: true })).toBeVisible();
  expect(calls).toBe(1);
});

test('character controls and delete dialog fit at mobile 200% text', async ({ page }) => {
  await page.goto('/'); await create(page, 'Ash');
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByText('Options', { exact: true }).click();
  await page.getByLabel('Text Size', { exact: true }).selectOption('200');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  expect(await page.getByRole('dialog').evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Delete Ash', exact: true })).toBeFocused();
});

test('older characters load their existing progress without fabricated birth stats', async ({ page }) => {
  await page.request.get('/prototype/');
  const token = (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken').value;
  await page.request.post('/api/player/create/', { headers: { 'X-CSRFToken': token } });
  await page.goto('/');
  await page.getByRole('button', { name: 'Load Adventurer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Adventurer', exact: true })).toBeVisible();
  await expect(page.getByText('Level 1 · Experience 0', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Strength value', { exact: true })).not.toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Adventurer', exact: true })).toBeVisible();
});

test('recovery code adds a saved character to the current browser roster', async ({ page }) => {
  await page.goto('/');
  await page.getByText('Recover a saved character', { exact: true }).click();
  await page.route('**/api/characters/recover/', async route => {
    expect(route.request().postDataJSON()).toEqual({ code: 'one-use-code' });
    await route.fulfill({ json: {
      success: true, recovered: { id: 'recovered-id', name: 'Jo' }, current: null,
      characters: [{ id: 'recovered-id', name: 'Jo', character_id: 'person-id', active: false, created_at: '2026-01-01T00:00:00Z' }],
    } });
  });
  await page.getByLabel('Recovery code', { exact: true }).fill('one-use-code');
  await page.getByRole('button', { name: 'Recover character', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Load Jo', exact: true })).toBeVisible();
  await expect(page.getByText('Jo was added to this browser. Choose Load to open the character.', { exact: true })).toBeVisible();
});

test('registration transfers the current character and signing in elsewhere loads it', async ({ page, browser }) => {
  await page.goto('/'); await create(page, 'Across Worlds');
  await page.getByRole('button', { name: 'Create new account', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill('cross-browser-user');
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByLabel('Confirm password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByText('Signed in as', { exact: false })).toContainText('cross-browser-user');
  await expect(page.getByRole('button', { name: 'Load Across Worlds', exact: true })).toBeVisible();

  const second = await browser.newPage();
  await second.goto('/');
  await second.getByLabel('Username', { exact: true }).fill('cross-browser-user');
  await second.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await second.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(second.getByRole('button', { name: 'Load Across Worlds', exact: true })).toBeVisible();
  await second.getByRole('button', { name: 'Load Across Worlds', exact: true }).click();
  await expect(second.getByRole('heading', { name: 'Across Worlds · Newborn', exact: true })).toBeVisible();
});
