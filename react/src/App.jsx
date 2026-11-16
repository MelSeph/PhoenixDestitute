import React, { useEffect, useState } from 'react';
import CharacterManager from './CharacterManager.jsx';
import ColorPicker from './ColorPicker.jsx';
import Dialog from './Dialog.jsx';
import { applyAppearance, backup, colorLabels, customizationCount, defaults, loadAppearance, readabilityOptions, saveAppearance, summary, summaryKey, themeLabels, validateBackup } from './appearance.js';

function download(content, type, name) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = name;
  document.body.append(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function initialAppearance() {
  try { return loadAppearance(window.localStorage); }
  catch { return { settings: defaults(), warning: 'Browser storage is unavailable. Settings will last for this page only.' }; }
}
function initialSummaryOpen() {
  try { return localStorage.getItem(summaryKey) !== 'false'; } catch { return true; }
}

export default function App() {
  const [initial] = useState(initialAppearance);
  const [settings, setSettings] = useState(initial.settings);
  const [message, setMessage] = useState(initial.warning);
  const [picker, setPicker] = useState(null);
  const [file, setFile] = useState(null);
  const [pendingImport, setPendingImport] = useState(null);
  const [undo, setUndo] = useState(null);
  const [summaryOpen, setSummaryOpen] = useState(initialSummaryOpen);
  useEffect(() => { applyAppearance(settings, document.documentElement); }, [settings]);

  function update(next, success, requireStorage = false) {
    try { saveAppearance(localStorage, next); }
    catch {
      if (requireStorage) { setMessage('Could not save settings. Your current appearance is unchanged.'); return false; }
      setSettings(next);
      setMessage('Appearance updated for this page. Browser storage is unavailable; changes may not survive a refresh.');
      return true;
    }
    setSettings(next); setMessage(success); return true;
  }
  function changeSummary(open) {
    setSummaryOpen(open);
    try { localStorage.setItem(summaryKey, String(open)); }
    catch { setMessage('Summary display changed for this page. Browser storage is unavailable.'); }
  }
  function reset(kind) {
    if (kind === 'all' && !window.confirm('Restore all appearance defaults? Export a backup first if you want to keep your settings.')) return;
    const initial = defaults();
    const next = kind === 'readability' ? { ...settings, readability: initial.readability }
      : kind === 'colors' ? { ...settings, theme: initial.theme, customColors: initial.customColors } : initial;
    if (update(next, `${kind === 'all' ? 'All appearance' : kind === 'colors' ? 'Color' : 'Readability'} defaults restored.`) && kind === 'all') setUndo(null);
  }
  async function importFile() {
    if (!file) { setMessage('Choose a JSON backup file first.'); return; }
    try {
      if (file.size > 1024 * 1024) throw new Error('Choose a backup smaller than 1 MB.');
      setPendingImport(validateBackup(JSON.parse(await file.text())));
      setMessage('Review the backup before importing.');
    } catch (error) { setMessage(`Could not import: ${error.message}`); }
  }
  async function copySummary() {
    try { await navigator.clipboard.writeText(summary(settings)); setMessage('Appearance summary copied.'); }
    catch { setMessage('Clipboard access is unavailable. You can download the summary instead.'); }
  }
  const comparison = pendingImport ? [
    ['Theme', themeLabels[settings.theme], themeLabels[pendingImport.theme]],
    ...Object.entries(colorLabels).map(([key, label]) => [label, settings.customColors[key], pendingImport.customColors[key]]),
    ...Object.entries(readabilityOptions).map(([key, setting]) => [setting.label, settings.readability[key], pendingImport.readability[key]]),
  ] : [];
  const optionsMenu = <details className="options-menu">
    <summary role="button" className="options-toggle icon-button" aria-label="Options" title="Options"><span className="visually-hidden">Options</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="m9 3-1 3-3 1-2 4 2 2 1 4 3 1 2 3 4-1 1-3 3-1 2-4-2-2-1-4-3-1-2-3Z" /><circle cx="12" cy="12" r="3" /></svg></summary>
    <section className="panel appearance-settings" aria-labelledby="appearance-heading">
      <h2 id="appearance-heading">Appearance Settings</h2>
      <label htmlFor="theme">Color Theme</label>
      <select id="theme" value={settings.theme} onChange={event => update({ ...settings, theme: event.target.value }, 'Color theme updated.')}>
        {Object.entries(themeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <div className="settings-grid">{Object.entries(readabilityOptions).map(([key, setting]) => <div key={key}>
        <label htmlFor={key}>{setting.label}</label>
        <select id={key} value={settings.readability[key]} onChange={event => update({ ...settings, readability: { ...settings.readability, [key]: event.target.value } }, `${setting.label} updated.`)}>
          {setting.options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>)}</div>
      <p className="help">Text size, fonts, and spacing are independent of your color theme. These preferences are stored in this browser.</p>
      <div className="game-prose" aria-label="Readability preview">
        <p>The trail winds through the quiet forest. You notice footprints leading toward an old stone bridge.</p>
        <p>Across the bridge, a lantern glows in a distant window. The next decision is yours.</p>
        <p>You check your supplies before moving forward, knowing the journey may be long.</p>
      </div>
      {settings.theme === 'custom' && <section aria-labelledby="custom-heading"><h3 id="custom-heading">Custom Theme Colors</h3>
        <div className="settings-grid">{Object.entries(colorLabels).map(([key, label]) => <div key={key}>
          <span className="field-label">{label} Color</span><button className="color-trigger secondary" aria-label={`Choose ${label.toLowerCase()} color`} onClick={() => setPicker(key)}><span className="swatch" style={{ background: settings.customColors[key] }} />{settings.customColors[key]}</button>
        </div>)}</div>
        <p className="help">Colors are checked for readable contrast before they are applied.</p>
        <button>Example game button</button>
      </section>}
      <section className="setting-section"><h3>Restore Defaults</h3>
        <p>Reset readability or colors independently. Export a backup before resetting all settings if you want to keep them.</p>
        <div className="actions"><button onClick={() => reset('readability')}>Reset Readability Settings</button><button onClick={() => reset('colors')}>Reset Color Settings</button><button onClick={() => reset('all')}>Reset All Appearance Settings</button></div>
      </section>
      <section className="setting-section"><h3>Back Up Appearance Settings</h3>
        <p>Save a JSON backup to restore later, or keep a readable summary for reference.</p>
        <div className="actions"><button onClick={() => { download(JSON.stringify(backup(settings), null, 2), 'application/json', 'phoenixdestitute-appearance-backup.json'); setMessage('Appearance backup prepared. Check your browser downloads.'); }}>Export Appearance Settings</button>
          <button onClick={copySummary}>Copy Appearance Summary</button>
          <button onClick={() => { download(summary(settings), 'text/plain', 'phoenixdestitute-appearance-summary.txt'); setMessage('Summary prepared. Check your browser downloads.'); }}>Download Appearance Summary (.txt)</button></div>
      </section>
      <section className="setting-section" aria-label="Live Appearance Summary">
        <details open={summaryOpen} onToggle={event => { if (event.currentTarget.open !== summaryOpen) changeSummary(event.currentTarget.open); }}>
          <summary>Live Appearance Summary <span className="help">(show / hide)</span></summary><pre>{summary(settings)}</pre>
        </details>
        <p>Customized preferences: {customizationCount(settings)} of 14</p>
        <p>Summary display: {summaryOpen ? 'Expanded' : 'Collapsed'}</p>
        <button onClick={() => { changeSummary(true); setMessage('Live Appearance Summary expanded.'); }}>Reset Summary Display</button>
      </section>
      <section className="setting-section"><h3>Restore Appearance Backup</h3>
        <p>Choose a backup from this app or the Django prototype. You can review changes before importing. Undo is available until you refresh.</p>
        <label htmlFor="import-file">Appearance backup JSON file</label><input id="import-file" type="file" accept=".json,application/json" onChange={event => setFile(event.target.files[0] ?? null)} />
        <div className="actions"><button onClick={importFile}>Import Appearance Settings</button>
          <button disabled={!undo} onClick={() => { if (update(undo, 'Last import undone.', true)) setUndo(null); }}>Undo Last Import</button></div>
      </section>
      <p className="status" role="status" aria-live="polite">{message}</p>
    </section>
  </details>;

  return <main className="prototype-container">
    <section className="panel masthead" aria-label="Phoenix Destitute">
      <svg className="phoenix-mark" viewBox="0 0 96 96" role="img" aria-label="Phoenix rising from ashes">
        <path fill="#9b4d24" d="M48 82c-14 0-25-5-33-15 10 4 19 5 27 2-7-5-12-12-13-22 7 7 14 10 21 9-6-8-8-18-5-29 4 9 10 14 17 16-1-8 2-17 9-26-2 13 1 23 8 30 6 6 8 13 6 21-2 8-10 14-23 14H48Z" />
        <path fill="#e0a33a" d="M48 77c-10 0-18-3-24-9 8 2 15 1 21-3-6-4-9-9-10-15 6 5 11 7 17 6-4-6-5-13-3-20 3 7 8 11 14 12-1-7 1-13 5-19 0 10 3 17 8 22 5 5 6 10 3 16-3 7-12 10-25 10H48Z" />
        <path fill="#f3d17a" d="M49 72c-6 0-10-2-14-5 6 1 10-1 13-4-4-3-6-6-6-10 4 3 7 4 11 3-2-4-2-8 0-12 2 5 5 7 9 8 0-4 1-8 4-11 0 7 2 11 5 15 3 3 3 7 0 10-3 4-10 6-19 6h-3Z" />
        <path fill="#d7c8a0" d="M19 84c8-4 14-4 20 0 6-4 12-4 18 0 6-4 12-4 20 0-7 1-12 3-16 7-7-3-14-3-21 0-6-4-13-6-21-7Z" />
      </svg><div><h1>Phoenix Destitute</h1><p>Your journey begins with possibility.</p></div>
    </section>
    <CharacterManager optionsMenu={optionsMenu} />
    {picker && <ColorPicker colorKey={picker} colors={settings.customColors} onClose={() => setPicker(null)} onApply={colors => { update({ ...settings, customColors: colors }, 'Custom color applied.'); setPicker(null); }} />}
    {pendingImport && <Dialog title="Review Appearance Backup" onClose={() => setPendingImport(null)}>
      <p>{comparison.filter(([, before, after]) => before !== after).length} of 15 settings will change. Nothing changes until you confirm.</p>
      <dl className="comparison">{comparison.map(([label, before, after]) => <React.Fragment key={label}><dt>{label}</dt><dd>{after}{before !== after && <span className="change-note">Changed from {before}</span>}</dd></React.Fragment>)}</dl>
      {message.startsWith('Could not save') && <p role="status">{message}</p>}
      <div className="actions"><button className="secondary" onClick={() => setPendingImport(null)}>Cancel</button><button onClick={() => {
        if (update(pendingImport, 'Appearance backup imported and saved.', true)) { setUndo(settings); setPendingImport(null); }
      }}>Import these settings</button></div>
    </Dialog>}
  </main>;
}
