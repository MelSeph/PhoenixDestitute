import React, { useEffect, useState } from 'react';

export default function BirthResourceBars({ characterId, visible }) {
  const [resources, setResources] = useState(null);
  const [experience, setExperience] = useState(null);
  useEffect(() => {
    if (!visible) { setResources(null); setExperience(null); return; }
    const controller = new AbortController();
    fetch('/api/characters/current/', { credentials: 'same-origin', signal: controller.signal })
      .then(response => response.json()).then(body => {
        setResources(body.draft?.resources ?? null);
        setExperience(body.character?.experience ?? null);
      }).catch(() => {});
    return () => controller.abort();
  }, [characterId, visible]);
  if (!visible || !resources) return null;
  return <section className="birth-resource-bars" aria-label="Birth resources">{[['health', 'Health'], ['mana', 'Mana'], ['stamina', 'Stamina']].map(([key, label]) => {
    const resource = resources[key]; const percent = resource.maximum > 0 ? Math.max(0, Math.min(100, resource.current / resource.maximum * 100)) : 0;
    return <div className={`game-resource ${key}`} key={key}><strong>{label}</strong><div className="game-resource-track" role="progressbar" aria-label={label} aria-valuemin="0" aria-valuemax={resource.maximum} aria-valuenow={resource.current}><i style={{ width: `${percent}%` }} /><span>{resource.current} / {resource.maximum}</span></div></div>;
  })}{experience && <div className="game-resource experience"><strong>Experience</strong><div className="game-resource-track" role="progressbar" aria-label="Experience" aria-valuemin="0" aria-valuemax={experience.maximum} aria-valuenow={experience.current}><i style={{ width: `${experience.maximum > 0 ? Math.max(0, Math.min(100, experience.current / experience.maximum * 100)) : 0}%` }} /><span>{experience.current} / {experience.maximum}</span></div></div>}</section>;
}
