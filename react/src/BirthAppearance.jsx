import React from 'react';

export const identityLabels = { skin_tone: 'Skin tone', eye_color: 'Eye color', hair_length: 'Hair length', hair_color: 'Hair color', hair_texture: 'Hair texture' };

export function HairPreview({ length, hair = '#493025', skin = '#c58c63' }) {
  const outline = '#292324';
  return <svg viewBox="0 0 80 88" className="hair-preview" aria-hidden="true" data-hair-length={length}>
    <rect x="1" y="1" width="78" height="86" rx="12" fill="#ede8df" />
    {['medium', 'long'].includes(length) && <path d={length === 'long' ? 'M17 36Q15 8 40 8T63 36L68 82H12Z' : 'M18 36Q15 8 40 8T62 36L64 62H16Z'} fill={hair} stroke={outline} strokeWidth="1.5" />}
    <path d="M20 86Q21 66 40 66T60 86" fill="#879eaa" />
    <path d="M34 57V71Q40 76 46 71V57" fill={skin} stroke={outline} />
    <ellipse cx="40" cy="38" rx="19" ry="25" fill={skin} stroke={outline} strokeWidth="1.5" />
    {length !== 'bald' && <path d="M21 37Q15 8 40 8T59 37L53 25L45 22L31 29L25 26Z" fill={hair} stroke={outline} strokeWidth="1.5" />}
    <circle cx="33" cy="39" r="1.8" fill={outline} /><circle cx="47" cy="39" r="1.8" fill={outline} />
    <path d="M35 51Q40 55 45 51" fill="none" stroke={outline} strokeWidth="1.5" />
  </svg>;
}

function ColorVisual({ field, color }) {
  return field === 'eye_color'
    ? <svg viewBox="0 0 60 36" className="eye-swatch" aria-hidden="true" data-color={color}><path d="M2 18Q30-12 58 18Q30 48 2 18Z" fill="#f6f2e9" stroke="#383333" strokeWidth="2" /><circle cx="30" cy="18" r="12" fill={color} /><circle cx="30" cy="18" r="5" fill="#171415" /><circle cx="33" cy="14" r="2" fill="#fff" /></svg>
    : <span className="appearance-swatch" style={{ background: color }} aria-hidden="true" data-color={color} />;
}

function choice(options, key, value) { return options[key]?.find(option => option.value === value); }

export function AppearanceSummary({ identity, options }) {
  return <dl className="identity-summary">
    <dt>Name</dt><dd>{identity.name}</dd>
    <dt>Gender</dt><dd>{identity.gender === 'custom' ? identity.custom_gender : choice(options, 'gender', identity.gender)?.label}</dd>
    {Object.entries(identityLabels).filter(([key]) => identity.hair_length !== 'bald' || !['hair_color', 'hair_texture'].includes(key)).map(([key, label]) => {
      const selected = choice(options, key, identity[key]);
      return <React.Fragment key={key}><dt>{label}</dt><dd>
        {selected?.color && <ColorVisual field={key} color={selected.color} />}
        {key === 'hair_length' && <HairPreview length={identity.hair_length} hair={choice(options, 'hair_color', identity.hair_color)?.color} skin={choice(options, 'skin_tone', identity.skin_tone)?.color} />}
        {selected?.label}
      </dd></React.Fragment>;
    })}
  </dl>;
}

export function BirthIdentityForm({ identity, options, disabled, dirty, onChange, onSave }) {
  function change(key, value) {
    const next = { ...identity, [key]: value };
    if (key === 'gender' && value !== 'custom') next.custom_gender = '';
    if (key === 'hair_length' && value === 'bald') { next.hair_color = ''; next.hair_texture = ''; }
    onChange(next);
  }
  return <form className="birth-identity" onSubmit={event => { event.preventDefault(); onSave(); }}>
    <h3>Identity and looks</h3>
    <p className="help">Choose your appearance. These choices do not change your starting attributes. Illustrations show hair length; texture is chosen separately.</p>
    <fieldset disabled={disabled} className="identity-fields">
      <legend>Name and gender</legend>
      <label htmlFor="birth-name">Name</label><input id="birth-name" value={identity.name} maxLength={100} autoComplete="off" onChange={event => change('name', event.target.value)} />
      <label htmlFor="birth-gender">Gender</label><select id="birth-gender" value={identity.gender} onChange={event => change('gender', event.target.value)}>
        <option value="">Choose gender</option>{options.gender.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
      {identity.gender === 'custom' && <><label htmlFor="custom-gender">Custom gender label</label><input id="custom-gender" value={identity.custom_gender} maxLength={40} onChange={event => change('custom_gender', event.target.value)} /></>}
    </fieldset>
    {Object.entries(identityLabels).filter(([key]) => identity.hair_length !== 'bald' || !['hair_color', 'hair_texture'].includes(key)).map(([key, label]) => <fieldset key={key} disabled={disabled} className="appearance-choices">
      <legend>{label}</legend><div className="choice-grid">{options[key].map(option => <label className="choice-card" key={option.value}>
        <input type="radio" name={`birth-${key}`} value={option.value} checked={identity[key] === option.value} onChange={() => change(key, option.value)} />
        {option.color && <ColorVisual field={key} color={option.color} />}
        {key === 'hair_length' && <HairPreview length={option.value} hair={choice(options, 'hair_color', identity.hair_color)?.color} skin={choice(options, 'skin_tone', identity.skin_tone)?.color} />}
        <span>{option.label}</span>
      </label>)}</div>
    </fieldset>)}
    <p className="help" role="status">{dirty ? 'You have unsaved identity or appearance changes. Save them before rolling or reviewing your birth.' : 'Identity and appearance match your saved draft.'}</p>
    <button type="submit" disabled={disabled || !dirty}>Save identity and looks</button>
  </form>;
}
