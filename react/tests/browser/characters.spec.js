import { test, expect } from '@playwright/test';

let accountNumber = 0;
const password = 'A-Secure-Player-Password-938!';
function nextUsername() { accountNumber++; return `player-${Date.now()}-${accountNumber}`; }

async function register(page, username = nextUsername()) {
  await page.getByRole('button', { name: 'Create new account', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Confirm password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
  return username;
}

async function signIn(page, username) {
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).last().click();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
}

async function create(page, name) {
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  await page.getByLabel('Name', { exact: true }).fill(name);
  await page.getByLabel('Gender', { exact: true }).selectOption('nonbinary');
  for (const [group, value] of [['Skin tone', 'Fair'], ['Eye color', 'Blue'], ['Hair length', 'Bald']]) {
    await page.getByRole('group', { name: group, exact: true }).getByRole('radio', { name: value, exact: true }).check();
  }
  await page.getByRole('button', { name: 'Save identity and looks', exact: true }).click();
  await page.getByRole('button', { name: 'Review birth', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm birth', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'You wake up in your crib', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: `${name} · Newborn`, exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Choose another character', exact: true }).click();
  await expect(page.getByRole('button', { name: `Load ${name}`, exact: true })).toBeEnabled();
}

test('landing stays focused on account access and options until sign-in', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Sign in', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Create a character', exact: true })).not.toBeVisible();
  await expect(page.getByText('Options', { exact: true })).toBeVisible();
  await register(page);
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
  await expect(page.getByText('Options', { exact: true })).not.toBeVisible();
});

test('a failed sign-in leaves the landing form available for another choice', async ({ page }) => {
  await page.goto('/');
  const username = nextUsername();
  await page.getByLabel('Username', { exact: true }).fill(username);
  await page.getByLabel('Password', { exact: true }).fill('incorrect-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).last().click();
  await expect(page.getByRole('alert')).toHaveText('Username or password is incorrect.');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true }).last()).toBeEnabled();
  await register(page, username);
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
});

test('create two characters, load either, and retain the selection across refresh', async ({ page }, testInfo) => {
  await page.goto('/'); await register(page); await create(page, 'Ash');
  const first = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  await create(page, 'Ember');
  const second = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  expect(second.birth.character_id).not.toBe(first.birth.character_id);
  await page.getByRole('button', { name: 'Load Ash', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'You wake up in your crib', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ash · Newborn', exact: true })).toBeVisible();
  await expect(page.getByLabel('Strength value', { exact: true })).toHaveText(String(first.stats.strength));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'You wake up in your crib', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ash · Newborn', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Choose another character', exact: true }).click();
  await page.getByRole('button', { name: 'Load Ember', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'You wake up in your crib', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ember · Newborn', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Choose another character', exact: true }).click();
  await page.locator('.character-list').screenshot({ path: testInfo.outputPath('character-list.png') });
});

test('delete requires the exact name, can be cancelled, and removes the selected character', async ({ page }) => {
  await page.goto('/'); await register(page); await create(page, 'Ash');
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
  await expect(page.getByRole('button', { name: 'Create a character', exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Load Ash', exact: true })).not.toBeVisible();
});

test('deleting an inactive character keeps the loaded character available', async ({ page }) => {
  await page.goto('/'); await register(page); await create(page, 'Ash'); await create(page, 'Ember');
  await page.getByRole('button', { name: 'Load Ember', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Choose another character', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Choose another character', exact: true }).click();
  await expect(page.getByText(/Ember · Current character/)).toBeVisible();
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  await expect(page.getByRole('dialog', { name: 'Delete Ash?' })).toBeVisible();
  await page.getByLabel('Type Ash to delete', { exact: true }).fill('Ash');
  await page.getByRole('button', { name: 'Delete character', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Load Ash', exact: true })).not.toBeVisible();
  await expect(page.getByText(/Ember · Current character/)).toBeVisible();
});

test('an unfinished draft survives loading a character and choosing New character again', async ({ page }) => {
  await page.goto('/'); await register(page); await create(page, 'Ash');
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  await page.getByRole('button', { name: 'Roll starting attributes', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).toBeEnabled();
  const draft = (await (await page.request.get('/api/creation/stats/')).json()).draft;
  await page.getByRole('button', { name: 'Load Ash', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Choose another character', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Choose another character', exact: true }).click();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true })).toBeEnabled();
  expect((await (await page.request.get('/api/creation/stats/')).json()).draft).toEqual(draft);
});

test('foreign sessions cannot see, load, or delete another roster entry', async ({ page, browser }) => {
  await page.goto('/'); await register(page); await create(page, 'Ash');
  const entry = (await (await page.request.get('/api/characters/')).json()).characters[0];
  const other = await browser.newContext();
  const otherPage = await other.newPage();
  await otherPage.goto('http://127.0.0.1:5173/');
  await register(otherPage);
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
  await page.goto('/'); await register(page); await create(page, 'Ash');
  let calls = 0;
  await page.route('**/api/characters/delete/', async route => { calls++; await route.fetch(); await route.abort('failed'); });
  await page.getByRole('button', { name: 'Delete Ash', exact: true }).click();
  await page.getByLabel('Type Ash to delete', { exact: true }).fill('Ash');
  await page.getByRole('button', { name: 'Delete character', exact: true }).click();
  await expect(page.getByText(/Reload characters before trying again/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create a character', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload characters', exact: true }).click();
  await expect(page.getByText('No saved characters yet.', { exact: true })).toBeVisible();
  expect(calls).toBe(1);
});

test('character controls and delete dialog fit at mobile 200% text', async ({ page }) => {
  await page.goto('/');
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByText('Options', { exact: true }).click();
  await page.getByLabel('Text Size', { exact: true }).selectOption('200');
  await register(page); await create(page, 'Ash');
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
  await register(page);
  await page.getByRole('button', { name: 'Load Adventurer', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back, Adventurer', exact: true })).toBeVisible();
  await expect(page.getByText('Level 1 · Experience 0', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Strength value', { exact: true })).not.toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Welcome back, Adventurer', exact: true })).toBeVisible();
});

test('recovery code adds a saved character to the current browser roster', async ({ page }) => {
  await page.goto('/'); await register(page);
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

test('a new account character loads into the game after signing in elsewhere', async ({ page, browser }) => {
  await page.goto('/'); const username = await register(page, 'cross-browser-user');
  await create(page, 'Across Worlds');
  await expect(page.getByText('Signed in as', { exact: false })).toContainText('cross-browser-user');
  await expect(page.getByRole('button', { name: 'Load Across Worlds', exact: true })).toBeVisible();

  const second = await browser.newPage();
  await second.goto('/');
  await signIn(second, username);
  await expect(second.getByRole('button', { name: 'Load Across Worlds', exact: true })).toBeVisible();
  await second.getByRole('button', { name: 'Load Across Worlds', exact: true }).click();
  await expect(second.getByRole('heading', { name: 'You wake up in your crib', exact: true })).toBeVisible();
  await expect(second.getByRole('heading', { name: 'Across Worlds · Newborn', exact: true })).toBeVisible();
});
