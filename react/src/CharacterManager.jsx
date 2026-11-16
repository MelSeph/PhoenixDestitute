import React, { cloneElement, useCallback, useEffect, useRef, useState } from 'react';
import BirthCreationPanel from './BirthCreationPanel.jsx';
import Dialog from './Dialog.jsx';

async function request(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const fieldErrors = Object.entries(body?.field_errors ?? {}).flatMap(([field, errors]) =>
      (Array.isArray(errors) ? errors : [errors]).map(error => `${field}: ${error}`));
    throw new Error([body?.error ?? `HTTP ${response.status}`, ...fieldErrors].join(' '));
  }
  return body;
}
function csrfToken() {
  const cookie = document.cookie.split('; ').find(value => value.startsWith('csrftoken='));
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

export default function CharacterManager({ optionsMenu, onCurrentChange }) {
  const [roster, setRoster] = useState(null);
  const [account, setAccount] = useState(null);
  const [accountMode, setAccountMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [email, setEmail] = useState('');
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
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
  const [activePane, setActivePane] = useState('crib');
  const [paneBeforeSheet, setPaneBeforeSheet] = useState('crib');
  const [paneBeforeOptions, setPaneBeforeOptions] = useState('crib');
  const [lifeEventView, setLifeEventView] = useState({ events: null, error: '' });
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
      setRoster(characters); setAccount(accountState);
      onCurrentChange?.(characters.current);
      setScreen(!accountState.authenticated ? 'landing' : characters.current ? 'game' : 'selection');
      setCreating(false); setActivePane('crib'); setPaneBeforeSheet('crib'); setReady(true); setMessage('Saved characters loaded.');
    }
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
      const characters = await request(`/api/characters/${action}/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body),
      });
      setRoster(characters);
      onCurrentChange?.(characters.current);
      if (action === 'load') { setScreen('game'); setCreating(false); setActivePane('crib'); setPaneBeforeSheet('crib'); }
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
      const body = logoutAction ? {} : action === 'register' ? { username, email, password1: password, password2 } : { username, password };
      const result = await request(`/api/account/${action}/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body),
      });
      const accountResult = action === 'register' ? await request('/api/account/logout/', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify({}),
      }) : result;
      const characters = await request('/api/characters/');
      setAccount(accountResult); setRoster(characters); onCurrentChange?.(characters.current); setPassword(''); setPassword2('');
      if (action === 'register') { setAccountMode('login'); setAccountMessage('Account created. Sign in with your new username and password.'); }
      setScreen(!accountResult.authenticated ? 'landing' : characters.current ? 'game' : 'selection');
      setCreating(false); setActivePane('crib'); setPaneBeforeSheet('crib');
      setViewKey(key => key + 1); setChildState({ busy: false, dirty: false }); setReady(true);
      setMessage(action === 'register' ? 'Account created. Please sign in.' : accountResult.authenticated ? 'Your account characters are ready in this browser.' : 'Signed out.');
    } catch (error) {
      setAccountMessage(error.message);
      setReady(true);
    } finally { pending.current = false; setBusy(false); }
  }
  const locked = busy || !ready || childState.busy;
  const current = roster?.current;
  const characterSheetOpen = activePane === 'sheet' || activePane === 'lifeEvents';
  const lifeEventsOpen = activePane === 'lifeEvents';
  function toggleCharacterSheet() {
    if (characterSheetOpen) setActivePane(paneBeforeSheet);
    else { setPaneBeforeSheet(activePane); setActivePane('sheet'); }
  }
  function openGameOptions() {
    setPaneBeforeOptions(activePane);
    setActivePane('options');
  }
  function closeGameOptions() { setActivePane(paneBeforeOptions); }
  async function deleteAccount(event) {
    event.preventDefault();
    if (pending.current || !csrfToken()) return;
    pending.current = true; setBusy(true);
    try {
      const result = await request('/api/account/delete/', { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({ password: deletePassword, confirmation: deleteConfirmation }) });
      setAccount({ authenticated: false }); setRoster({ characters: [], current: null });
      onCurrentChange?.(null); setScreen('landing'); setAccountMode('login'); setAccountMessage(result.message);
      setPassword(''); setDeletePassword(''); setDeleteConfirmation('');
    } catch (error) { setAccountMessage(error.message); }
    finally { pending.current = false; setBusy(false); }
  }
  const accountOptions = account?.authenticated ? cloneElement(optionsMenu, {}, <>
    {optionsMenu.props.children}
    <details className="setting-section account-deletion">
      <summary>Delete player account</summary>
      <p>Your account and live character records will be removed. You can reclaim them by signing in with your current username and password within two years.</p>
      <form onSubmit={deleteAccount}>
        <label htmlFor="delete-account-username">Type {account.username} to confirm</label>
        <input id="delete-account-username" value={deleteConfirmation} onChange={event => setDeleteConfirmation(event.target.value)} autoComplete="off" required />
        <label htmlFor="delete-account-password">Current password</label>
        <input id="delete-account-password" type="password" value={deletePassword} onChange={event => setDeletePassword(event.target.value)} autoComplete="current-password" required />
        <button disabled={locked || deleteConfirmation !== account.username}>Delete account</button>
      </form>
      {accountMessage && <p role="alert">{accountMessage}</p>}
    </details>
  </>) : optionsMenu;
  useEffect(() => {
    if (screen !== 'game') return undefined;
    const record = () => {
      if (document.visibilityState !== 'visible') return;
      fetch('/api/account/activity/', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({ seconds: 60 }) }).catch(() => {});
    };
    const timer = window.setInterval(record, 60_000);
    return () => window.clearInterval(timer);
  }, [screen, current?.id]);
  useEffect(() => {
    if (!lifeEventsOpen) return undefined;
    const controller = new AbortController();
    setLifeEventView({ events: null, error: '' });
    request(`/api/characters/events/?character_id=${encodeURIComponent(current?.id ?? '')}`, { signal: controller.signal })
      .then(result => setLifeEventView({ events: result.events, error: '' }))
      .catch(error => { if (error.name !== 'AbortError') setLifeEventView({ events: [], error: error.message }); });
    return () => controller.abort();
  }, [lifeEventsOpen, current?.id]);
  if (screen === 'loading') return <section className="panel"><p role="status">Loading account…</p></section>;

  if (screen === 'landing') return <section className="panel account-landing" aria-labelledby="account-heading">
    <div className="section-heading"><h2 id="account-heading">{accountMode === 'login' ? 'Sign in' : 'Create your account'}</h2>{optionsMenu}</div>
    <form className="account-form" onSubmit={accountAction}>
      <label htmlFor="account-username">Username</label>
      <input id="account-username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required />
      <label htmlFor="account-password">Password</label>
      <input id="account-password" type="password" autoComplete={accountMode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} required />
      {accountMode === 'register' && <>
        <p>Create a player account to save characters across browsers.</p>
        <label htmlFor="account-email">Email address</label>
        <input id="account-email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} required />
        <p className="help">Email verification is not enabled yet.</p>
        <p className="help">Use at least 10 characters; avoid common or numeric-only passwords.</p>
        <label htmlFor="account-password-confirm">Confirm password</label>
        <input id="account-password-confirm" type="password" autoComplete="new-password" value={password2} onChange={event => setPassword2(event.target.value)} required />
      </>}
      <div className="actions account-actions" aria-label="Account actions">
        {accountMode === 'login' ? <button type="submit" disabled={locked}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5m5 5H3" /></svg>Sign in
        </button> : <button type="button" className="secondary" onClick={() => { setAccountMode('login'); setAccountMessage(''); setPassword(''); setPassword2(''); }}>Back to sign in</button>}
        {accountMode === 'register' ? <button type="submit" disabled={locked}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14m-7-7h14" /></svg>Create account
        </button> : <button type="button" className="secondary" aria-label="Create new account" disabled={locked} onClick={() => { setAccountMode('register'); setAccountMessage(''); setPassword(''); setPassword2(''); }}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14m-7-7h14" /></svg>{accountMode === 'register' ? 'Create account' : 'Create new'}
        </button>}
      </div>
    </form>
    {accountMessage && <p role="alert">{accountMessage}</p>}
    <p className="help">Your characters are saved to your account and can be loaded from another browser.</p>
  </section>;

  if (screen === 'game') return <div className="game-area"><div className={`game-screen pane-${activePane}`}>
    <aside className="panel game-tools" aria-label="Character tools">
      {current?.kind === 'birth' && <button type="button" aria-expanded={characterSheetOpen}
        aria-controls={lifeEventsOpen ? 'life-events-page' : 'character-sheet'}
        className="icon-button sheet-toggle" aria-label={characterSheetOpen ? 'Hide character sheet' : 'Show character sheet'}
        title={characterSheetOpen ? 'Hide character sheet' : 'Show character sheet'}
        onClick={toggleCharacterSheet}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h11l3 3v15H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M8 3v18M11 8h6M11 12h6M11 16h4M17 3v4h3" /></svg>
      </button>}
    </aside>
    <section className="panel game-entry" aria-labelledby="game-heading">
      <div className="game-controls"><div className="game-control-icons">
        <button type="button" className="icon-button secondary" aria-label="Sign out" title="Sign out"
          disabled={busy || childState.busy} onClick={() => accountAction()}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 17l5-5-5-5m5 5H3M13 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" /></svg>
        </button>
        <button type="button" className="icon-button secondary" aria-label="Options" title="Options"
          aria-expanded={activePane === 'options'} onClick={openGameOptions}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 3-1 3-3 1-2 4 2 2 1 4 3 1 2 3 4-1 1-3 3-1 2-4-2-2-1-4-3-1-2-3Z" /><circle cx="12" cy="12" r="3" /></svg>
        </button>
      </div>
        <button className="secondary" disabled={busy || childState.busy} onClick={() => { setScreen('selection'); setCreating(false); }}>Choose another character</button>
      </div>
      {current?.kind === 'birth' ? <>
        <h2 id="game-heading">You wake up in your crib</h2>
        <p>Your first moments begin as a newborn. Your choices and starting attributes are ready below.</p>
      </> : <>
        <h2 id="game-heading">Welcome back, {current?.name}</h2>
        <p>Your saved story is loaded. Birth details are unavailable for this older character.</p>
      </>}
    </section>
    {current?.kind === 'birth' && activePane === 'sheet' && <div id="character-sheet" className="character-sheet-panel">
      <BirthCreationPanel key={`${current.id}-${viewKey}`} readUrl="/api/characters/current/" showStartingResources={false}
        disabled={busy || !ready} onConfirmed={reload} onStateChange={reportState}
        onOpenLifeEvents={() => setActivePane('lifeEvents')} />
    </div>}
    {current?.kind === 'birth' && lifeEventsOpen && <section id="life-events-page" className="panel life-events-panel" aria-labelledby="life-events-heading">
      <div className="life-events-header"><h2 id="life-events-heading">Life Events</h2>
        <button type="button" className="secondary" onClick={() => setActivePane('sheet')}>Back to Character Sheet</button></div>
      <div className="life-events-console" role="log" aria-label="Character life events">
        {lifeEventView.events === null ? <p role="status">Loading life events…</p> : lifeEventView.error ? <p role="alert">Could not load life events: {lifeEventView.error}</p> : lifeEventView.events.length ? lifeEventView.events.map((event, index) => <p className="life-event" key={`${event.event_type}-${event.occurred_at}-${index}`}>
          <time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time><br />{event.text}
        </p>) : <p>No life events have been recorded yet.</p>}
      </div>
    </section>}
    {activePane === 'options' && <section className="panel game-options-page" aria-labelledby="game-options-heading">
      <div className="game-options-header"><h2 id="game-options-heading">Game Options</h2>
        <button type="button" className="secondary" onClick={closeGameOptions}>Close</button></div>
      {cloneElement(accountOptions, { open: true, className: 'options-menu game-options-inline' })}
    </section>}
    {current?.kind === 'legacy' && <section className="panel"><h2>{current.name}</h2><p>Level {current.level} · Experience {current.experience}</p></section>}
  </div></div>;

  return <>
    <section className="panel" aria-labelledby="characters-heading" aria-label="Your characters">
      <div className="section-heading"><h2 id="characters-heading">Choose a character</h2>{accountOptions}</div>
      <div className="actions"><p>Signed in as <strong>{account?.username}</strong></p>
        <button className="secondary" disabled={busy || childState.busy} onClick={() => accountAction()}>Sign out</button></div>
      <p role="status">{message}</p>
      {roster?.characters.length === 0 && <p>No saved characters yet.</p>}
      <ul className="character-list">{roster?.characters.map(entry => <li key={entry.id}>
        <div><strong>{entry.name}</strong>{entry.active && <span> · Current character</span>}
          {entry.character_id && <p className="help">Character ID: {entry.character_id}</p>}</div>
        <div className="actions"><button className="icon-button compact-button" disabled={locked} aria-label={`Load ${entry.name}`} title={`Load ${entry.name}`} onClick={() => act('load', entry)}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h4m3-4 4-4-4-4m4 4H8" /></svg></button>
          <button className="icon-button compact-button secondary" disabled={locked} aria-label={`Delete ${entry.name}`} title={`Delete ${entry.name}`} onClick={() => { setDeleting(entry); setConfirmationName(''); }}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16m-10 4v6m4-6v6M5 7l1 14h12l1-14M9 7V4h6v3" /></svg></button></div>
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
