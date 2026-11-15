export const themes = {
  midnight: { background: '#111820', panel: '#202d3a', border: '#718298', text: '#f1f5f9', muted: '#c0ccd9', accent: '#e5c78e', button: '#b5c8db' },
  daylight: { background: '#f1f4f8', panel: '#ffffff', border: '#64748b', text: '#182536', muted: '#45546a', accent: '#234f85', button: '#234f85' },
  highContrast: { background: '#000000', panel: '#000000', border: '#ffffff', text: '#ffffff', muted: '#ffffff', accent: '#ffff00', button: '#ffffff' },
};
export const themeLabels = { midnight: 'Midnight', daylight: 'Daylight', highContrast: 'High Contrast', custom: 'Custom' };
export const colorLabels = { panel: 'Panel Background', text: 'Primary Text', muted: 'Muted Text', accent: 'Accent', border: 'Border', background: 'Page Background', button: 'Button Background' };
export const readabilityOptions = {
  'font-size': { label: 'Text Size', default: '100', css: 'font-size', options: [['100', 'Standard (100%)', '100%'], ['125', 'Large (125%)', '125%'], ['150', 'Extra Large (150%)', '150%'], ['200', 'Maximum (200%)', '200%']] },
  'line-spacing': { label: 'Line Spacing', default: 'comfortable', css: '--body-line-height', options: [['compact', 'Compact (1.4)', '1.4'], ['comfortable', 'Comfortable (1.6)', '1.6'], ['spacious', 'Spacious (1.9)', '1.9']] },
  'letter-spacing': { label: 'Letter Spacing', default: 'normal', css: '--body-letter-spacing', options: [['normal', 'Normal', '0em'], ['relaxed', 'Relaxed (0.03em)', '0.03em'], ['wide', 'Wide (0.06em)', '0.06em']] },
  'word-spacing': { label: 'Word Spacing', default: 'normal', css: '--body-word-spacing', options: [['normal', 'Normal', '0em'], ['relaxed', 'Relaxed (0.1em)', '0.1em'], ['wide', 'Wide (0.2em)', '0.2em']] },
  'paragraph-spacing': { label: 'Paragraph Spacing', default: 'comfortable', css: '--paragraph-spacing', options: [['compact', 'Compact (0.5em)', '0.5em'], ['comfortable', 'Comfortable (1em)', '1em'], ['spacious', 'Spacious (1.5em)', '1.5em']] },
  'font-family': { label: 'Font Style', default: 'sans', css: '--body-font-family', options: [['sans', 'Sans Serif', 'Arial, Helvetica, sans-serif'], ['serif', 'Serif', 'Georgia, "Times New Roman", serif'], ['mono', 'Monospace', '"Courier New", Courier, monospace']] },
  'reading-width': { label: 'Reading Width', default: 'standard', css: '--reading-width', options: [['narrow', 'Narrow (45 characters)', '45ch'], ['standard', 'Standard (65 characters)', '65ch'], ['wide', 'Wide (85 characters)', '85ch']] },
};
export function defaults() {
  return { theme: 'midnight', customColors: { ...themes.midnight }, readability: Object.fromEntries(Object.entries(readabilityOptions).map(([key, setting]) => [key, setting.default])) };
}
const prefix = 'phoenixdestitute-';
export const summaryKey = 'phoenix-appearance-live-summary-open';
const isRecord = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const own = (object, key) => Object.hasOwn(object, key);
export const isHex = value => typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value);

export function contrast(a, b) {
  function luminance(hex) {
    if (!isHex(hex)) throw new Error('Use a six-digit hexadecimal color.');
    const channels = [1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16) / 255)
      .map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  }
  const values = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (values[0] + 0.05) / (values[1] + 0.05);
}
export function buttonLabelColor(color) {
  return contrast(color, '#000000') >= contrast(color, '#ffffff') ? '#000000' : '#ffffff';
}
export function validPalette(palette) {
  if (!isRecord(palette) || Object.keys(palette).length !== 7 || !Object.keys(themes.midnight).every(key => own(palette, key) && isHex(palette[key]))) return false;
  return ['panel', 'background'].every(background =>
    ['text', 'muted', 'accent'].every(key => contrast(palette[key], palette[background]) >= 4.5)
    && ['border', 'button'].every(key => contrast(palette[key], palette[background]) >= 3))
    && contrast(buttonLabelColor(palette.button), palette.button) >= 4.5;
}
export function validateBackup(data) {
  if (!isRecord(data) || data.format !== 'phoenixdestitute-appearance' || data.version !== 1) throw new Error('Choose a PhoenixDestitute appearance backup (version 1).');
  if (!own(themeLabels, data.theme)) throw new Error('Unknown color theme.');
  if (!validPalette(data.customColors)) throw new Error('Custom colors must contain all seven colors and meet text (4.5:1) and control (3:1) contrast requirements.');
  if (!isRecord(data.readability) || Object.keys(data.readability).length !== 7 || !Object.entries(readabilityOptions).every(([key, setting]) => own(data.readability, key) && setting.options.some(([value]) => value === data.readability[key]))) throw new Error('The backup must contain all seven valid readability preferences.');
  return { theme: data.theme, customColors: { ...data.customColors }, readability: { ...data.readability } };
}
export const backup = settings => ({ format: 'phoenixdestitute-appearance', version: 1, ...settings });

export function loadAppearance(storage) {
  const settings = defaults();
  let warning = '';
  try {
    const savedTheme = storage.getItem(prefix + 'theme');
    if (savedTheme && own(themeLabels, savedTheme)) settings.theme = savedTheme;
    const colors = storage.getItem(prefix + 'custom-colors');
    if (colors) {
      try {
        const parsed = JSON.parse(colors);
        if (validPalette(parsed)) settings.customColors = parsed;
        else warning = 'Saved custom colors are invalid. Safe defaults are displayed.';
      } catch { warning = 'Saved custom colors could not be read. Safe defaults are displayed.'; }
    }
    for (const [key, setting] of Object.entries(readabilityOptions)) {
      const saved = storage.getItem(prefix + key);
      if (setting.options.some(([value]) => value === saved)) settings.readability[key] = saved;
    }
  } catch { warning = 'Browser storage is unavailable. Settings will last for this page only.'; }
  return { settings, warning };
}

// Save the complete selection before replacing React state. Failed imports leave it unchanged.
export function saveAppearance(storage, settings) {
  const entries = [[prefix + 'theme', settings.theme], [prefix + 'custom-colors', JSON.stringify(settings.customColors)], ...Object.entries(settings.readability).map(([key, value]) => [prefix + key, value])];
  const originals = entries.map(([key]) => [key, storage.getItem(key)]);
  try { for (const [key, value] of entries) storage.setItem(key, value); }
  catch (error) {
    for (const [key, value] of originals) {
      try { if (value === null) storage.removeItem(key); else storage.setItem(key, value); } catch { /* Storage can remain unavailable. */ }
    }
    throw error;
  }
}
export function applyAppearance(settings, root) {
  const palette = settings.theme === 'custom' ? settings.customColors : themes[settings.theme];
  const safePalette = validPalette(palette) ? palette : themes.highContrast;
  for (const [key, value] of Object.entries(safePalette)) root.style.setProperty('--color-' + key, value);
  root.style.setProperty('--color-button-text', buttonLabelColor(safePalette.button));
  for (const [key, setting] of Object.entries(readabilityOptions)) root.style.setProperty(setting.css, setting.options.find(([value]) => value === settings.readability[key])[2]);
}
export function summary(settings) {
  return ['PhoenixDestitute Appearance Summary', '', 'Selected theme: ' + themeLabels[settings.theme], '', 'Custom colors:', ...Object.entries(colorLabels).map(([key, label]) => `${label}: ${settings.customColors[key]}`), '', 'Readability:', ...Object.entries(readabilityOptions).map(([key, setting]) => `${setting.label}: ${setting.options.find(([value]) => value === settings.readability[key])[1]}`)].join('\n');
}
export function customizationCount(settings) {
  const initial = defaults();
  return Object.keys(initial.customColors).filter(key => initial.customColors[key].toLowerCase() !== settings.customColors[key].toLowerCase()).length
    + Object.keys(initial.readability).filter(key => initial.readability[key] !== settings.readability[key]).length;
}
