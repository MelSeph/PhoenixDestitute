import React, { useEffect, useState } from 'react';

export default function BirthResourceBars({ characterId, visible }) {
  const [resources, setResources] = useState(null);
  useEffect(() => {
    if (!visible) { setResources(null); return; }
    const controller = new AbortController();
    fetch('/api/characters/current/', { credentials: 'same-origin', signal: controller.signal })
      .then(response => response.json()).then(body => setResources(body.draft?.resources ?? null)).catch(() => {});
    return () => controller.abort();
  }, [characterId, visible]);
  if (!visible || !resources) return null;
  return <section className="birth-resource-bars" aria-label="Birth resources">{[['health', 'Health'], ['mana', 'Mana'], ['stamina', 'Stamina']].map(([key, label]) => {
    const resource = resources[key]; const percent = resource.maximum > 0 ? Math.max(0, Math.min(100, resource.current / resource.maximum * 100)) : 0;
    return <div className={`game-resource ${key}`} key={key}><div className="game-resource-reading"><strong>{label}</strong><span>{resource.current} / {resource.maximum}</span></div><div className="game-resource-track" role="progressbar" aria-label={label} aria-valuemin="0" aria-valuemax={resource.maximum} aria-valuenow={resource.current}><i style={{ width: `${percent}%` }} /></div></div>;
  })}</section>;
}
