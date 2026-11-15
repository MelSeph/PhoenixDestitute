import React, { useCallback, useEffect, useRef, useState } from 'react';
import BirthCreationPanel from './BirthCreationPanel.jsx';
import Dialog from './Dialog.jsx';

async function request(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error ?? `HTTP ${response.status}`);
  return body;
}
function csrfToken() {
  const cookie = document.cookie.split('; ').find(value => value.startsWith('csrftoken='));
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

export default function CharacterManager() {
  const [roster, setRoster] = useState(null);
  const [busy, setBusy] = useState(true);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState('Loading saved characters…');
  const [deleting, setDeleting] = useState(null);
  const [confirmationName, setConfirmationName] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [viewKey, setViewKey] = useState(0);
  const [childState, setChildState] = useState({ busy: false, dirty: false });
  const pending = useRef(false);
  const reportState = useCallback(state => setChildState(state), []);

  async function reload(signal) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setReady(false);
    try { setRoster(await request('/api/characters/', { signal })); setReady(true); setMessage('Saved characters loaded.'); }
    catch (error) { if (error.name !== 'AbortError') setMessage(`Could not load saved characters: ${error.message}`); }
    finally { pending.current = false; if (!signal?.aborted) setBusy(false); }
  }
  useEffect(() => {
    const controller = new AbortController(); reload(controller.signal);
    return () => controller.abort();
  }, []);
  function mayLeave() {
    return !childState.dirty || window.confirm('Discard unsaved identity changes? Your saved birth draft will be kept.');
  }
  async function act(action, entry) {
    if (pending.current || childState.busy || !ready || !mayLeave()) return;
    pending.current = true; setBusy(true); setReady(false);
    setMessage(action === 'delete' ? 'Deleting character…' : 'Loading your choice…');
    try {
      if (!csrfToken()) {
        const response = await fetch('/prototype/', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
      }
      if (!csrfToken()) throw new Error('Cookies are required to manage characters.');
      const body = entry ? { character_id: entry.id } : {};
      if (action === 'delete') body.confirmation_name = confirmationName;
      setRoster(await request(`/api/characters/${action}/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body),
      }));
      setViewKey(key => key + 1); setChildState({ busy: false, dirty: false });
      setDeleting(null); setConfirmationName(''); setReady(true);
      setMessage(action === 'delete' ? 'Character and saved story permanently deleted.' : action === 'new' ? 'Your saved characters are kept. Continue your unfinished draft or roll a new one.' : `${entry.name} loaded.`);
    } catch (error) {
      setDeleting(null);
      setMessage(`Could not complete character action: ${error.message}. Reload characters before trying again.`);
    } finally { pending.current = false; setBusy(false); }
  }
  async function recover(event) {
    event.preventDefault();
    if (pending.current || childState.busy || !ready || !mayLeave()) return;
    pending.current = true; setBusy(true); setReady(false);
    setMessage('Recovering saved character…');
    try {
      if (!csrfToken()) {
        const response = await fetch('/prototype/', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
      }
      if (!csrfToken()) throw new Error('Cookies are required to recover a character.');
      const result = await request('/api/characters/recover/', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({ code: recoveryCode.trim() }),
      });
      setRoster(result); setRecoveryCode(''); setReady(true);
      setMessage(`${result.recovered.name} was added to this browser. Choose Load to open the character.`);
    } catch (error) {
      setMessage(`Could not recover character: ${error.message}`);
    } finally { pending.current = false; setBusy(false); }
  }
  const locked = busy || !ready || childState.busy;
  const current = roster?.current;
  return <>
    <section className="panel" aria-labelledby="characters-heading">
      <h2 id="characters-heading">Your characters</h2>
      <p className="help">Saved characters belong to this browser session. New character keeps your other stories available to load.</p>
      <p role="status">{message}</p>
      {roster?.characters.length === 0 && <p>No saved characters yet.</p>}
      <ul className="character-list">{roster?.characters.map(entry => <li key={entry.id}>
        <div><strong>{entry.name}</strong>{entry.active && <span> · Current character</span>}
          {entry.character_id && <p className="help">Character ID: {entry.character_id}</p>}</div>
        <div className="actions"><button disabled={locked} aria-label={`Load ${entry.name}`} onClick={() => act('load', entry)}>Load</button>
          <button className="secondary" disabled={locked} aria-label={`Delete ${entry.name}`} onClick={() => { setDeleting(entry); setConfirmationName(''); }}>Delete</button></div>
      </li>)}</ul>
      <div className="actions"><button disabled={locked} onClick={() => act('new')}>New character</button>
        <button className="secondary" disabled={busy || childState.busy} onClick={() => { if (mayLeave()) { setViewKey(key => key + 1); reload(); } }}>Reload characters</button></div>
      <details>
        <summary>Recover a saved character</summary>
        <p className="help">Enter a one-use code issued for your character in Django admin. Codes expire after 24 hours.</p>
        <form className="actions" onSubmit={recover}>
          <label htmlFor="character-recovery-code">Recovery code</label>
          <input id="character-recovery-code" autoComplete="off" value={recoveryCode} onChange={event => setRecoveryCode(event.target.value)} />
          <button disabled={locked || !recoveryCode.trim()}>Recover character</button>
        </form>
      </details>
    </section>
    {roster && (current?.kind === 'legacy'
      ? <section className="panel"><h2>{current.name}</h2><p>Level {current.level} · Experience {current.experience}</p><p>Your saved story is loaded. Birth details are unavailable for this life.</p></section>
      : <BirthCreationPanel key={`${current?.id ?? 'creation'}-${viewKey}`} readUrl={current ? '/api/characters/current/' : undefined}
          disabled={busy || !ready} onConfirmed={reload} onStateChange={reportState} />)}
    {deleting && <Dialog title={`Delete ${deleting.name}?`} onClose={() => { if (!busy) setDeleting(null); }}>
      <p>Permanently destroy this character and its entire saved story, including all lives, saves, items, birth records, and history? This cannot be undone. Other characters will be kept.</p>
      <label htmlFor="delete-character-name">Type {deleting.name} to delete</label><input id="delete-character-name" value={confirmationName} onChange={event => setConfirmationName(event.target.value)} autoComplete="off" />
      <div className="actions"><button className="secondary" disabled={busy} onClick={() => setDeleting(null)}>Cancel</button>
        <button disabled={locked || confirmationName !== deleting.name} onClick={() => act('delete', deleting)}>Delete character</button></div>
    </Dialog>}
  </>;
}
