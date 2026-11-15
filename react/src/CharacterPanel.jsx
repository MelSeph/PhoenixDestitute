import React, { useEffect, useState } from 'react';

function csrfToken() {
  const cookie = document.cookie.split('; ').find(value => value.startsWith('csrftoken='));
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : '';
}

export default function CharacterPanel() {
  const [player, setPlayer] = useState(null);
  const [status, setStatus] = useState('Loading character…');
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(true);

  async function load(signal) {
    setBusy(true);
    try {
      const response = await fetch('/api/player/', { credentials: 'same-origin', signal });
      if (response.status === 404) {
        setMissing(true);
        setStatus('No local character yet.');
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setPlayer((await response.json()).player);
      setMissing(false);
      setStatus('Character loaded from Django database.');
    } catch (error) {
      if (error.name !== 'AbortError') setStatus(`Could not load character: ${error.message}`);
    } finally { if (!signal?.aborted) setBusy(false); }
  }
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, []);

  async function create() {
    setBusy(true);
    setStatus('Creating character…');
    try {
      // The existing Django page issues the CSRF cookie. Do not render its HTML.
      if (!csrfToken()) {
        const bootstrap = await fetch('/prototype/', { credentials: 'same-origin' });
        if (!bootstrap.ok) throw new Error(`CSRF initialization failed (HTTP ${bootstrap.status})`);
      }
      if (!csrfToken()) throw new Error('Cookies are required to create a local character.');
      const response = await fetch('/api/player/create/', {
        method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setPlayer((await response.json()).player);
      setMissing(false);
      setStatus('Character loaded from Django database.');
    } catch (error) { setStatus(`Could not create character: ${error.message}`); }
    finally { setBusy(false); }
  }

  return <section className="panel" aria-labelledby="character-heading">
    <h2 id="character-heading">Character</h2>
    <p role="status">{status}</p>
    {player && <p>{player.name} — Level {player.level} — Experience {player.experience}</p>}
    {missing && <button disabled={busy} onClick={create}>Create local character</button>}
    {!busy && <button className="secondary" onClick={() => load()}>Reload character</button>}
  </section>;
}
