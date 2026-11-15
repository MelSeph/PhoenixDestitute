import React, { useEffect, useRef, useState } from 'react';

const statLabels = {
  luck: 'Luck', strength: 'Strength', defense: 'Defense', agility: 'Agility',
  likeability: 'Likeability', intelligence: 'Intelligence', endurance: 'Endurance', baseline_condition: 'Baseline Condition',
};
const resourceLabels = { health: ['Health', 'Strength'], mana: ['Mana', 'Intelligence'], stamina: ['Stamina', 'Endurance'] };
const endpoint = '/api/creation/stats/';

function csrfToken() {
  const cookie = document.cookie.split('; ').find(value => value.startsWith('csrftoken='));
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}
async function fetchDraft(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  if (response.status === 404 && !options.method) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(typeof body?.error === 'string' ? body.error : `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body.draft;
}

export default function BirthCreationPanel() {
  const [draft, setDraft] = useState(null);
  const [missing, setMissing] = useState(false);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(true);
  const [status, setStatus] = useState('Loading your birth draft…');
  // Block a second click immediately, before React has rendered disabled controls.
  const pending = useRef(false);

  function show(next, message) {
    setDraft(next);
    setMissing(next === null);
    setReady(next !== null);
    setStatus(next ? message : 'Choose your starting attributes before your first birth.');
  }
  async function load(signal) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true); setReady(false);
    try { show(await fetchDraft(endpoint, { signal }), 'Your starting attributes are saved.'); }
    catch (error) {
      if (error.name !== 'AbortError') { setMissing(false); setStatus(`Could not load your birth draft: ${error.message}`); }
    } finally {
      pending.current = false;
      if (!signal?.aborted) setBusy(false);
    }
  }
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, []);

  async function write(action, lockedStats) {
    if (pending.current || (action !== 'start' && !ready)) return;
    pending.current = true;
    setBusy(true); setReady(false); setMissing(false);
    setStatus(action === 'reroll' ? 'Rolling unlocked attributes…' : 'Saving your birth draft…');
    try {
      if (!csrfToken()) {
        const response = await fetch('/prototype/', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`Could not prepare creation (HTTP ${response.status}).`);
      }
      if (!csrfToken()) throw new Error('Cookies are required to save a birth draft.');
      const body = action === 'start' ? {} : { revision: draft.revision };
      if (action === 'locks') body.locked_stats = lockedStats;
      const next = await fetchDraft(endpoint + (action === 'start' ? '' : action + '/'), {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() }, body: JSON.stringify(body),
      });
      show(next, action === 'reroll' ? 'Unlocked attributes rerolled. Locked attributes were preserved.' : 'Your starting attributes are saved.');
    } catch (error) {
      if (error.status === 409) {
        // Reading is safe. Never replay the rejected action using a new revision.
        try {
          const next = await fetchDraft(endpoint);
          show(next, 'Your draft changed elsewhere. The latest values are loaded; review them before choosing another action.');
        } catch (reloadError) { setStatus(`Could not reload your birth draft: ${reloadError.message}. Reload before making another choice.`); }
      } else if (error.status === 404) {
        show(null, '');
        setStatus('Your birth draft is no longer available. Start a new draft to continue.');
      } else {
        // The server may have saved a request whose response was lost. Require a GET
        // before allowing another mutation; an automatic retry could roll twice.
        setStatus(`Could not save your birth draft: ${error.message}. Reload the draft before trying again.`);
      }
    } finally { pending.current = false; setBusy(false); }
  }
  const locks = draft?.locked_stats ?? [];
  function toggleLock(key) {
    const next = locks.includes(key) ? locks.filter(value => value !== key) : [...locks, key];
    if (next.length <= 3) write('locks', next);
  }

  return <section className="panel birth-creation" aria-labelledby="birth-heading" aria-busy={busy}>
    <h2 id="birth-heading">Begin your first life</h2>
    <p>Your story starts at birth. Shape your starting attributes with unlimited rolls and up to three locks.</p>
    <p className="status" role="status" aria-live="polite">{status}</p>
    {missing && <button disabled={busy} onClick={() => write('start')}>Roll starting attributes</button>}
    {draft && <>
      <fieldset className="birth-stats" aria-describedby="lock-help">
        <legend>Starting attributes</legend>
        <p id="lock-help">{locks.length} of 3 attributes locked. Unlock an attribute to choose a different lock. Unlocked values roll from 1 to 5.</p>
        {Object.entries(statLabels).map(([key, label]) => <div className="stat-row" key={key}>
          <span>{label}</span><output aria-label={`${label} value`}>{draft.stats[key]}</output>
          <label className="stat-lock"><input type="checkbox" aria-label={`Lock ${label}`} checked={locks.includes(key)} disabled={busy || !ready || (!locks.includes(key) && locks.length >= 3)} onChange={() => toggleLock(key)} />Lock</label>
        </div>)}
      </fieldset>
      <div className="actions"><button disabled={busy || !ready} onClick={() => write('reroll')}>Reroll unlocked attributes</button></div>
      <section aria-labelledby="resources-heading"><h3 id="resources-heading">Starting resources</h3>
        <div className="birth-resources">{Object.entries(resourceLabels).map(([key, [label, parent]]) => <div className="resource-preview" key={key}>
          <h4>{label}</h4><output aria-label={`${label} preview`}>{draft.resources[key].current} / {draft.resources[key].maximum}</output><p className="help">{parent} × 10 · Starts full</p>
        </div>)}</div>
      </section>
      <p className="help">Baseline Condition describes your starting physical condition. Your wellbeing will also depend on hunger, fatigue, illness, and injuries.</p>
    </>}
    <div className="actions"><button className="secondary" disabled={busy} onClick={() => load()}>Reload draft</button></div>
    <p className="help">These choices are saved as a draft. Name, gender, looks, and final birth confirmation are not available yet.</p>
  </section>;
}
