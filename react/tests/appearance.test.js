import { test } from 'node:test';
import assert from 'node:assert/strict';
import { backup, buttonLabelColor, customizationCount, defaults, loadAppearance, saveAppearance, themes, validPalette, validateBackup } from '../src/appearance.js';

function storage() {
  const data = new Map();
  return { data, getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) };
}
test('prototype palettes meet contrast requirements and choose readable button labels', () => {
  for (const palette of Object.values(themes)) assert.equal(validPalette(palette), true);
  assert.equal(buttonLabelColor('#ffffff'), '#000000');
  assert.equal(buttonLabelColor('#000000'), '#ffffff');
  assert.equal(validPalette({ ...themes.midnight, text: themes.midnight.panel }), false);
});
test('version 1 backups from the prototype round trip without changing their schema', () => {
  const settings = defaults();
  settings.theme = 'custom';
  settings.readability['font-size'] = '200';
  settings.customColors.accent = '#ffffff';
  assert.deepEqual(validateBackup(JSON.parse(JSON.stringify(backup(settings)))), settings);
  assert.equal(customizationCount(settings), 2);
});
test('malformed or unreadable imports are rejected before application', () => {
  for (const value of [null, [], {}, { ...backup(defaults()), version: 2 }, { ...backup(defaults()), theme: '__proto__' }, { ...backup(defaults()), readability: {} }, { ...backup(defaults()), customColors: { ...themes.midnight, text: '#202d3a' } }]) assert.throws(() => validateBackup(value));
  const invalid = backup(defaults());
  invalid.readability['font-size'] = 200;
  assert.throws(() => validateBackup(invalid));
});
test('existing localStorage keys are read and saved independently of game data', () => {
  const store = storage();
  store.setItem('game-save', 'untouched');
  const settings = defaults();
  settings.theme = 'daylight';
  settings.readability['word-spacing'] = 'wide';
  saveAppearance(store, settings);
  assert.equal(store.getItem('phoenixdestitute-theme'), 'daylight');
  assert.deepEqual(loadAppearance(store).settings, settings);
  assert.equal(store.getItem('game-save'), 'untouched');
});
test('failed persistence restores earlier keys rather than partially importing', () => {
  const store = storage();
  saveAppearance(store, defaults());
  const previous = new Map(store.data);
  const originalSet = store.setItem;
  let writes = 0;
  store.setItem = (key, value) => { if (++writes === 4) throw new Error('quota'); originalSet(key, value); };
  assert.throws(() => saveAppearance(store, { ...defaults(), theme: 'daylight' }));
  assert.deepEqual(store.data, previous);
});
test('unavailable storage and corrupt preferences leave the page usable', () => {
  assert.match(loadAppearance({ getItem() { throw new Error('blocked'); } }).warning, /unavailable/);
  const store = storage();
  store.setItem('phoenixdestitute-custom-colors', '{broken');
  store.setItem('phoenixdestitute-font-size', '999');
  const loaded = loadAppearance(store);
  assert.deepEqual(loaded.settings, defaults());
  assert.match(loaded.warning, /could not be read/);
  assert.equal(store.getItem('phoenixdestitute-custom-colors'), '{broken');
});
