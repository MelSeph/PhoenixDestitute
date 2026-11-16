import React from 'react';

const ageStages = {
  newborn: 'baby', baby: 'baby', toddler: 'toddler', kid: 'kid',
  young_adult: 'young adult', adult: 'adult', middle_age: 'middle age',
  elderly: 'elderly', deceased: 'deceased',
};

export function ageStageLabel(stage) {
  if (stage === 'newborn') return 'Newborn';
  return ageStages[stage] ?? 'Age unavailable';
}

export default function AgeStateIcon({ stage }) {
  const visual = ageStages[stage] ?? 'unknown';
  return <svg viewBox="0 0 48 48" className="age-state-icon" aria-hidden="true" data-age-stage={visual}>
    {visual === 'baby' && <><circle cx="24" cy="23" r="13" /><path d="M12 20c1-11 21-15 25-1M19 25h.1M29 25h.1M21 31q3 3 6 0M18 39q6-5 12 0" /><path d="M21 8q3-5 6 0" /></>}
    {visual === 'toddler' && <><circle cx="24" cy="15" r="9" /><path d="M15 14q2-9 10-8 7 1 8 9M18 18h.1M29 18h.1M21 22q3 2 6 0M24 24v11m0-7-9 7m9-7 9 7m-9 0-6 10m6-10 7 10" /></>}
    {visual === 'kid' && <><circle cx="24" cy="13" r="8" /><path d="M16 12q2-8 9-8 6 1 7 9M21 16h.1M27 16h.1M21 20q3 2 6 0M24 22v14m0-9-10 7m10-7 10 7m-10 2-7 11m7-11 8 11" /></>}
    {visual === 'young adult' && <><circle cx="24" cy="12" r="8" /><path d="M16 11q2-8 9-8 6 1 7 9M21 15h.1M27 15h.1M21 19q3 2 6 0M24 21v16m0-10-11 6m11-6 11 6m-11-2-8 13m8-13 8 13" /></>}
    {visual === 'adult' && <><circle cx="24" cy="12" r="8" /><path d="M16 11q2-8 9-8 6 1 7 9M21 15h.1M27 15h.1M21 19q3 2 6 0M24 21v16m0-10-11 6m11-6 11 6m-11-2-8 13m8-13 8 13M18 29h12" /></>}
    {visual === 'middle age' && <><circle cx="24" cy="12" r="8" /><path d="M16 11q2-8 9-8 6 1 7 9M21 15h.1M27 15h.1M21 19q3 2 6 0M24 21v16m0-10-11 6m11-6 11 6m-11-2-8 13m8-13 8 13M18 29h12M18 7l3 2m9-2-3 2" /></>}
    {visual === 'elderly' && <><circle cx="24" cy="12" r="8" /><path d="M16 11q2-8 9-8 6 1 7 9M21 15h.1M27 15h.1M21 19q3 2 6 0M24 21v15m0-9-10 5m10-5 8 4m-8 5-7 12m7-12 7 12M18 29h12M17 8q7 5 14 0M35 22v24m-4-1h8" /></>}
    {visual === 'deceased' && <><path d="M8 43V18L24 5l16 13v25H8Z" /><path d="M18 43V29h12v14M18 19h.1M30 19h.1M24 11v5m-3 4q3 2 6 0" /></>}
    {visual === 'unknown' && <><circle cx="24" cy="24" r="17" /><path d="M19 18q1-6 6-6t6 5q0 4-6 7v4m0 6h.1" /></>}
  </svg>;
}
