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

export default function CharacterManager({ onAccountStateChange }) {
  const [roster, setRoster] = useState(null);
  const [account, setAccount] = useState(null);
  const [accountMode, setAccountMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [accountMessage, setAccountMessage] = useState('');
  const [busy, setBusy] = useState(true);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState('Loading saved characters…');
  const [deleting, setDeleting] = useState(null);
  const [confirmationName, setConfirmationName] = useState('');
  const [recoveryCode, setRecoveryCode] = useState('');
  const [viewKey, setViewKey] = useState(0);
  const [screen, setScreen] = useState('loading');
  const [creating, setCreating] = useState(false);
  const [childState, setChildState] = useState({ busy: false, dirty: false });
  const pending = useRef(false);
  const reportState = useCallback(state => setChildState(state), []);

  async function reload(signal) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setReady(false);
    try {
      const [characters, accountState] = await Promise.all([
        request('/api/characters/', { signal }), request('/api/account/', { signal }),
      ]);
      setRoster(characters); setAccount(accountState); onAccountStateChange?.(accountState);
      setScreen(!accountState.authenticated ? 'landing' : characters.current ? 'game' : 'selection');
      setCreating(false); setReady(true); setMessage('Saved characters loaded.');
    }
    catch (error) { if (error.name !== 'AbortError') setMessage(`Could not load saved characters: ${error.message}`); }
    finally { pending.current = false; if (!signal?.aborted) setBusy(false); }
  }
  useEffect(() => {
    const controller = new AbortController(); reload(controller.signal);
    return () => controller.abort();
  }, [onAccountStateChange]);
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
      const characters = await request(`/api/characters/${action}/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body),
      });
      setRoster(characters);
      if (action === 'load') { setScreen('game'); setCreating(false); }
      if (action === 'new') { setScreen('selection'); setCreating(true); }
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
  async function accountAction(event) {
    event?.preventDefault();
    if (pending.current || childState.busy || !ready || !mayLeave()) return;
    pending.current = true; setBusy(true); setReady(false); setAccountMessage('');
    try {
      if (!csrfToken()) {
        const response = await fetch('/prototype/', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
      }
      if (!csrfToken()) throw new Error('Cookies are required for player accounts.');
      const logoutAction = account?.authenticated;
      const action = logoutAction ? 'logout' : accountMode;
      const body = logoutAction ? {} : action === 'register' ? { username, password1: password, password2 } : { username, password };
      const result = await request(`/api/account/${action}/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body),
      });
      const characters = await request('/api/characters/');
      setAccount(result); onAccountStateChange?.(result); setRoster(characters); setPassword(''); setPassword2('');
      setScreen(!result.authenticated ? 'landing' : characters.current ? 'game' : 'selection');
      setCreating(false);
      setViewKey(key => key + 1); setChildState({ busy: false, dirty: false }); setReady(true);
      setMessage(result.authenticated ? 'Your account characters are ready in this browser.' : 'Signed out.');
    } catch (error) {
      setAccountMessage(error.message);
      setReady(true);
    } finally { pending.current = false; setBusy(false); }
  }
  const locked = busy || !ready || childState.busy;
  const current = roster?.current;
  if (screen === 'loading') return <section className="panel"><p role="status">Loading account…</p></section>;

  if (screen === 'landing') return <section className="panel account-landing" aria-labelledby="account-heading">
    <h2 id="account-heading">{accountMode === 'login' ? 'Sign in' : 'Create your account'}</h2>
    <div className="actions" aria-label="Account actions">
      <button type="button" className={accountMode === 'login' ? '' : 'secondary'} disabled={locked} onClick={() => { setAccountMode('login'); setAccountMessage(''); }}>Sign in</button>
      <button type="button" className={accountMode === 'register' ? '' : 'secondary'} disabled={locked} onClick={() => { setAccountMode('register'); setAccountMessage(''); }}>Create new account</button>
    </div>
    <form className="account-form" onSubmit={accountAction}>
      <label htmlFor="account-username">Username</label>
      <input id="account-username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required />
      <label htmlFor="account-password">Password</label>
      <input id="account-password" type="password" autoComplete={accountMode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} required />
      {accountMode === 'register' && <>
        <p className="help">Use at least 10 characters; avoid common or numeric-only passwords.</p>
        <label htmlFor="account-password-confirm">Confirm password</label>
        <input id="account-password-confirm" type="password" autoComplete="new-password" value={password2} onChange={event => setPassword2(event.target.value)} required />
      </>}
      <button disabled={locked}>{accountMode === 'login' ? 'Sign in' : 'Create account'}</button>
    </form>
    {accountMessage && <p role="alert">{accountMessage}</p>}
    <p className="help">Your characters are saved to your account and can be loaded from another browser.</p>
  </section>;

  if (screen === 'game') return <>
    <section className="panel game-entry" aria-labelledby="game-heading">
      <div className="actions"><button className="secondary" disabled={busy || childState.busy} onClick={() => { setScreen('selection'); setCreating(false); }}>Choose another character</button>
        <button className="secondary" disabled={busy || childState.busy} onClick={() => accountAction()}>Sign out</button></div>
      {current?.kind === 'birth' ? <>
        <h2 id="game-heading">You wake up in your crib</h2>
        <p>Your first moments begin as a newborn. Your choices and starting attributes are ready below.</p>
      </> : <>
        <h2 id="game-heading">Welcome back, {current?.name}</h2>
        <p>Your saved story is loaded. Birth details are unavailable for this older character.</p>
      </>}
    </section>
    {current?.kind === 'birth' && <BirthCreationPanel key={`${current.id}-${viewKey}`} readUrl="/api/characters/current/"
      disabled={busy || !ready} onConfirmed={reload} onStateChange={reportState} />}
    {current?.kind === 'legacy' && <section className="panel"><h2>{current.name}</h2><p>Level {current.level} · Experience {current.experience}</p></section>}
  </>;

  return <>
    <section className="panel" aria-labelledby="characters-heading" aria-label="Your characters">
      <div className="actions"><p>Signed in as <strong>{account?.username}</strong></p>
        <button className="secondary" disabled={busy || childState.busy} onClick={() => accountAction()}>Sign out</button></div>
      <h2 id="characters-heading">Choose a character</h2>
      <p role="status">{message}</p>
      {roster?.characters.length === 0 && <p>No saved characters yet.</p>}
      <ul className="character-list">{roster?.characters.map(entry => <li key={entry.id}>
        <div><strong>{entry.name}</strong>{entry.active && <span> · Current character</span>}
          {entry.character_id && <p className="help">Character ID: {entry.character_id}</p>}</div>
        <div className="actions"><button disabled={locked} aria-label={`Load ${entry.name}`} onClick={() => act('load', entry)}>Load</button>
          <button className="secondary" disabled={locked} aria-label={`Delete ${entry.name}`} onClick={() => { setDeleting(entry); setConfirmationName(''); }}>Delete</button></div>
      </li>)}</ul>
      <div className="actions"><button disabled={locked} onClick={() => creating ? setCreating(false) : act('new')}>{creating ? 'Back to characters' : 'Create a character'}</button>
        <button className="secondary" disabled={busy || childState.busy} onClick={() => { if (mayLeave()) { setViewKey(key => key + 1); reload(); } }}>Reload characters</button></div>
      {creating && roster && <BirthCreationPanel key={`creation-${viewKey}`} disabled={busy || !ready}
        onConfirmed={reload} onStateChange={reportState} />}
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
    {deleting && <Dialog title={`Delete ${deleting.name}?`} onClose={() => { if (!busy) setDeleting(null); }}>
      <p>Permanently destroy this character and its entire saved story, including all lives, saves, items, birth records, and history? This cannot be undone. Other characters will be kept.</p>
      <label htmlFor="delete-character-name">Type {deleting.name} to delete</label><input id="delete-character-name" value={confirmationName} onChange={event => setConfirmationName(event.target.value)} autoComplete="off" />
      <div className="actions"><button className="secondary" disabled={busy} onClick={() => setDeleting(null)}>Cancel</button>
        <button disabled={locked || confirmationName !== deleting.name} onClick={() => act('delete', deleting)}>Delete character</button></div>
    </Dialog>}
  </>;
}
