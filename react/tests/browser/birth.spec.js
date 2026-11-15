import { test, expect } from '@playwright/test';

const base = '/api/creation/stats/';
function draft(overrides = {}) {
  return {
    draft_id: 'draft-1', revision: 'revision-1',
    stats: { luck: 1, strength: 2, defense: 3, agility: 4, likeability: 5, intelligence: 4, endurance: 3, baseline_condition: 2 },
    locked_stats: [], resources: { health: { current: 20, maximum: 20 }, mana: { current: 40, maximum: 40 }, stamina: { current: 30, maximum: 30 } },
    ...overrides,
  };
}
async function reply(route, value, status = 200) {
  await route.fulfill({ status, json: { success: true, draft: value } });
}
test.beforeEach(async ({ context, page }) => {
  await context.addCookies([{ name: 'csrftoken', value: 'test-token', url: 'http://127.0.0.1:5173' }]);
  let signedInAs = null;
  await page.route('**/api/account/', route => route.fulfill({ json: { success: true, authenticated: Boolean(signedInAs), username: signedInAs } }));
  await page.route('**/api/account/register/', async route => {
    signedInAs = route.request().postDataJSON().username;
    await route.fulfill({ json: { success: true, authenticated: true, username: signedInAs } });
  });
  await page.route('**/api/characters/', route => route.fulfill({ json: { success: true, characters: [], current: null } }));
  await page.route('**/api/characters/new/', route => route.fulfill({ json: { success: true, characters: [], current: null } }));
});

async function signUpAndStart(page) {
  await page.getByRole('button', { name: 'Create new account', exact: true }).click();
  await page.getByLabel('Username', { exact: true }).fill(`birth-${Date.now()}`);
  await page.getByLabel('Password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByLabel('Confirm password', { exact: true }).fill('A-Secure-Player-Password-938!');
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Choose a character', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
}
async function enterCreation(page) { await page.goto('/'); await signUpAndStart(page); }

test('start is explicit, bootstraps CSRF, and displays only server stats/resources', async ({ page, context }, testInfo) => {
  await context.clearCookies();
  const writes = [], legacy = [];
  page.on('request', request => { if (request.url().includes('/api/player/')) legacy.push(request.url()); });
  await page.route('**/prototype/', route => route.fulfill({ status: 200, headers: { 'set-cookie': 'csrftoken=birth-test-token; Path=/; SameSite=Lax' }, body: '<html></html>' }));
  await page.route('**' + base, async route => {
    if (route.request().method() === 'GET') { await route.fulfill({ status: 404, json: { error: 'Missing' } }); return; }
    writes.push(route.request().postDataJSON());
    expect(route.request().headers()['x-csrftoken']).toBe('birth-test-token');
    await reply(route, draft(), 201);
  });
  await page.goto('/');
  await signUpAndStart(page);
  const start = page.getByRole('button', { name: 'Roll starting attributes', exact: true });
  await expect(start).toBeVisible();
  expect(writes).toEqual([]);
  await start.click();
  await expect(page.getByLabel('Luck value', { exact: true })).toHaveText('1');
  await expect(page.getByLabel('Health preview', { exact: true })).toHaveText('20 / 20');
  await expect(page.getByLabel('Mana preview', { exact: true })).toHaveText('40 / 40');
  await expect(page.getByLabel('Stamina preview', { exact: true })).toHaveText('30 / 30');
  expect(writes).toEqual([{}]);
  expect(legacy).toEqual([]);
  await expect(page.getByRole('button', { name: 'Review birth', exact: true })).toBeDisabled();
  await page.locator('.birth-creation').screenshot({ path: testInfo.outputPath('birth-desktop.png') });
});

test('locks enforce three, unlock and switch, and send the complete server-owned selection', async ({ page }) => {
  let current = draft();
  const submissions = [];
  await page.route('**' + base, route => reply(route, current));
  await page.route('**' + base + 'locks/', async route => {
    const data = route.request().postDataJSON();
    expect(data.revision).toBe(current.revision);
    expect(Object.keys(data).sort()).toEqual(['locked_stats', 'revision']);
    submissions.push(data.locked_stats);
    current = { ...current, locked_stats: data.locked_stats, revision: `revision-${submissions.length + 1}` };
    await reply(route, current);
  });
  await enterCreation(page);
  for (const label of ['Strength', 'Intelligence', 'Endurance']) {
    await page.getByRole('checkbox', { name: `Lock ${label}`, exact: true }).click();
    await expect(page.getByRole('checkbox', { name: `Lock ${label}`, exact: true })).toBeChecked();
    await expect(page.getByRole('checkbox', { name: `Lock ${label}`, exact: true })).toBeEnabled();
  }
  await expect(page.getByRole('checkbox', { name: 'Lock Luck', exact: true })).toBeDisabled();
  await page.getByRole('checkbox', { name: 'Lock Strength', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: 'Lock Strength', exact: true })).not.toBeChecked();
  await page.getByRole('checkbox', { name: 'Lock Luck', exact: true }).click();
  await expect(page.getByRole('checkbox', { name: 'Lock Luck', exact: true })).toBeChecked();
  await expect(page.getByRole('checkbox', { name: 'Lock Luck', exact: true })).toBeEnabled();
  expect(submissions.at(-1)).toEqual(['intelligence', 'endurance', 'luck']);
  await expect(page.getByLabel('Strength value', { exact: true })).toHaveText('2');
});

test('unlimited explicit rerolls use each revision and rapid clicks submit only once', async ({ page }) => {
  let current = draft({ locked_stats: ['strength'] });
  let count = 0;
  let release;
  const hold = new Promise(resolve => { release = resolve; });
  await page.route('**' + base, route => reply(route, current));
  await page.route('**' + base + 'reroll/', async route => {
    expect(route.request().postDataJSON()).toEqual({ revision: current.revision });
    count++;
    if (count === 1) await hold;
    current = { ...current, revision: `rolled-${count}` };
    await reply(route, current);
  });
  await enterCreation(page);
  const reroll = page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true });
  await expect(reroll).toBeEnabled();
  await reroll.evaluate(button => { button.click(); button.click(); });
  await expect(reroll).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Reload draft' })).toBeDisabled();
  release();
  await expect(reroll).toBeEnabled();
  expect(count).toBe(1);
  for (let index = 0; index < 12; index++) { await reroll.click(); await expect(reroll).toBeEnabled(); }
  expect(count).toBe(13);
  await expect(page.getByLabel('Strength value', { exact: true })).toHaveText('2');
  await page.reload();
  await page.getByRole('button', { name: 'Create a character', exact: true }).click();
  await expect(reroll).toBeEnabled();
  expect(count).toBe(13);
});

test('a stale revision reloads the latest draft without replaying the failed action', async ({ page }) => {
  let current = draft();
  let posts = 0;
  await page.route('**' + base, route => reply(route, current));
  await page.route('**' + base + 'reroll/', async route => {
    posts++;
    expect(route.request().postDataJSON()).toEqual({ revision: 'revision-1' });
    current = draft({ revision: 'other-tab', locked_stats: ['luck'], stats: { ...current.stats, luck: 5 } });
    await route.fulfill({ status: 409, json: { error: 'The creation draft changed.' } });
  });
  await enterCreation(page);
  await page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true }).click();
  await expect(page.getByText(/latest values are loaded/)).toBeVisible();
  await expect(page.getByLabel('Luck value', { exact: true })).toHaveText('5');
  await expect(page.getByRole('checkbox', { name: 'Lock Luck', exact: true })).toBeChecked();
  expect(posts).toBe(1);
});

test('a lost response requires read recovery rather than repeating a possibly saved roll', async ({ page }) => {
  let current = draft();
  let posts = 0;
  await page.route('**' + base, route => reply(route, current));
  await page.route('**' + base + 'reroll/', async route => {
    posts++;
    current = draft({ revision: 'saved-but-lost', stats: { ...current.stats, luck: 4 } });
    await route.abort('failed');
  });
  await enterCreation(page);
  const reroll = page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true });
  await reroll.click();
  await expect(page.getByText(/Reload the draft before trying again/)).toBeVisible();
  await expect(reroll).toBeDisabled();
  await expect(page.getByRole('checkbox', { name: 'Lock Luck', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload draft' }).click();
  await expect(page.getByLabel('Luck value', { exact: true })).toHaveText('4');
  await expect(reroll).toBeEnabled();
  expect(posts).toBe(1);
});

test('expired drafts return to explicit creation, while account rejection offers no creation action', async ({ page }) => {
  await page.route('**' + base, route => reply(route, draft()));
  await page.route('**' + base + 'reroll/', route => route.fulfill({ status: 404, json: { error: 'Missing' } }));
  await enterCreation(page);
  await page.getByRole('button', { name: 'Reroll unlocked attributes', exact: true }).click();
  await expect(page.getByText(/no longer available/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Roll starting attributes', exact: true })).toBeEnabled();
  await expect(page.getByRole('checkbox')).toHaveCount(0);
  await page.route('**' + base, route => route.fulfill({ status: 403, json: { error: 'Account creation drafts are not implemented.' } }));
  await page.getByRole('button', { name: 'Reload draft' }).click();
  await expect(page.getByText(/Could not load your birth draft: Account creation/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Roll starting attributes', exact: true })).not.toBeVisible();
});

test('starting attributes fit a mobile viewport with 200% text', async ({ page }, testInfo) => {
  await page.route('**' + base, route => reply(route, draft()));
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/');
  await page.getByText('Options', { exact: true }).click();
  await page.getByLabel('Text Size', { exact: true }).selectOption('200');
  await signUpAndStart(page);
  await expect(page.getByRole('checkbox', { name: 'Lock Baseline Condition', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath('birth-mobile.png'), fullPage: true });
});
