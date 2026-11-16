import React from 'react';

export const identityLabels = { skin_tone: 'Skin tone', eye_color: 'Eye color', hair_length: 'Hair length', hair_color: 'Hair color', hair_texture: 'Hair texture' };

export function GenderModelIcon({ gender }) {
  return <svg viewBox="0 0 48 48" className="gender-model" aria-hidden="true" data-gender-model={gender}>
    {gender === 'male' && <><circle cx="18" cy="30" r="12" /><path d="m27 21 14-14m-8 0h8v8" /></>}
    {gender === 'female' && <><circle cx="24" cy="17" r="12" /><path d="M24 29v15m-7.5-7.5h15" /></>}
    {gender === 'nonbinary' && <><circle cx="24" cy="24" r="12" /><path d="M24 12V3M24 36v9" /></>}
    {gender === 'custom' && <>
      <circle cx="18" cy="15" r="6" />
      <path d="M7 40c0-8 4-13 11-13s11 5 11 13m9-36 2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5Z" />
    </>}
  </svg>;
}

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

export function HairTexturePreview({ texture, hair = '#493025' }) {
  const strand = {
    straight: 'M6 6C5 20 7 40 6 54',
    wavy: 'M6 6C13 12-1 18 6 24S13 36 6 42S-1 50 6 54',
    curly: 'M6 6C15 8 13 15 6 17S-1 26 6 29S15 37 6 40S-1 49 6 54',
    coily: 'M6 6C12 7 12 12 6 13S0 19 6 20S12 26 6 27S0 33 6 34S12 40 6 41S0 47 6 48S12 52 6 54',
  }[texture] ?? 'M6 6C5 20 7 40 6 54';
  return <svg viewBox="0 0 78 60" className="hair-texture-preview" aria-hidden="true" data-hair-texture={texture}>
    <rect x="1" y="1" width="76" height="58" rx="10" fill="#ede8df" />
    {[12, 23, 34, 45, 56].map(x => <g key={x} transform={`translate(${x} 0)`}>
      <path d={strand} fill="none" stroke="#292324" strokeWidth="8" strokeLinecap="round" />
      <path d={strand} fill="none" stroke={hair} strokeWidth="5" strokeLinecap="round" />
    </g>)}
  </svg>;
}

function ColorVisual({ field, color }) {
  return field === 'eye_color'
    ? <svg viewBox="0 0 60 36" className="eye-swatch" aria-hidden="true" data-color={color}><path d="M2 18Q30-12 58 18Q30 48 2 18Z" fill="#f6f2e9" stroke="#383333" strokeWidth="2" /><circle cx="30" cy="18" r="12" fill={color} /><circle cx="30" cy="18" r="5" fill="#171415" /><circle cx="33" cy="14" r="2" fill="#fff" /></svg>
    : <span className="appearance-swatch" style={{ background: color }} aria-hidden="true" data-color={color} />;
}

function choice(options, key, value) { return options[key]?.find(option => option.value === value); }

export function AppearanceSummary({ identity, options, showIdentity = true }) {
  return <dl className="identity-summary">
    {showIdentity && <><dt>Name</dt><dd>{identity.name}</dd>
      <dt>Gender</dt><dd><GenderModelIcon gender={identity.gender} />{identity.gender === 'custom' ? identity.custom_gender : choice(options, 'gender', identity.gender)?.label}</dd></>}
    {Object.entries(identityLabels).filter(([key]) => (showIdentity || key !== 'hair_color') && (identity.hair_length !== 'bald' || !['hair_color', 'hair_texture'].includes(key))).map(([key, label]) => {
      const selected = choice(options, key, identity[key]);
      return <React.Fragment key={key}><dt>{label}</dt><dd>
        {selected?.color && <ColorVisual field={key} color={selected.color} />}
        {key === 'hair_length' && <HairPreview length={identity.hair_length} hair={choice(options, 'hair_color', identity.hair_color)?.color} skin={choice(options, 'skin_tone', identity.skin_tone)?.color} />}
        {key === 'hair_texture' && <HairTexturePreview texture={identity.hair_texture} hair={choice(options, 'hair_color', identity.hair_color)?.color} />}
        {selected?.label}
      </dd></React.Fragment>;
    })}
  </dl>;
}

export function BirthIdentityForm({ identity, options, disabled, dirty, onChange, onSave, mode = 'appearance' }) {
  function change(key, value) {
    const next = { ...identity, [key]: value };
    if (key === 'gender' && value !== 'custom') next.custom_gender = '';
    if (key === 'hair_length' && value === 'bald') { next.hair_color = ''; next.hair_texture = ''; }
    onChange(next);
  }
  return <form className="birth-identity" onSubmit={event => { event.preventDefault(); onSave(); }}>
    {mode === 'appearance' && <p className="help">Choose your appearance. These choices do not change your starting attributes. Illustrations show hair length; texture is chosen separately.</p>}
    {mode === 'name' && <fieldset disabled={disabled} className="identity-fields">
      <label htmlFor="birth-name">Name</label><input id="birth-name" value={identity.name} maxLength={100} autoComplete="off" onChange={event => change('name', event.target.value)} />
    </fieldset>}
    {mode === 'appearance' && <><fieldset disabled={disabled} className="appearance-choices gender-choices">
      <legend>Gender</legend><div className="choice-grid">{options.gender.map(option => <label className="choice-card" key={option.value}>
        <input type="radio" name="birth-gender" value={option.value} checked={identity.gender === option.value} onChange={() => change('gender', option.value)} />
        <GenderModelIcon gender={option.value} /><span>{option.label}</span>
      </label>)}</div>
      {identity.gender === 'custom' && <label htmlFor="custom-gender">Custom gender label<input id="custom-gender" value={identity.custom_gender} maxLength={40} onChange={event => change('custom_gender', event.target.value)} /></label>}
    </fieldset>
    {Object.entries(identityLabels).filter(([key]) => identity.hair_length !== 'bald' || !['hair_color', 'hair_texture'].includes(key)).map(([key, label]) => <fieldset key={key} disabled={disabled} className="appearance-choices">
      <legend>{label}</legend><div className="choice-grid">{options[key].map(option => <label className="choice-card" key={option.value}>
        <input type="radio" name={`birth-${key}`} value={option.value} checked={identity[key] === option.value} onChange={() => change(key, option.value)} />
        {option.color && <ColorVisual field={key} color={option.color} />}
        {key === 'hair_length' && <HairPreview length={option.value} hair={choice(options, 'hair_color', identity.hair_color)?.color} skin={choice(options, 'skin_tone', identity.skin_tone)?.color} />}
        {key === 'hair_texture' && <HairTexturePreview texture={option.value} hair={choice(options, 'hair_color', identity.hair_color)?.color} />}
        <span>{option.label}</span>
      </label>)}</div>
    </fieldset>)}</>}
    {mode === 'appearance' && <p className="help" role="status">{dirty ? 'You have unsaved identity or appearance changes. Save them before rolling or reviewing your birth.' : 'Identity and appearance match your saved draft.'}</p>}
    <button type="submit" disabled={disabled || !dirty || (mode === 'name' && !identity.name.trim())}>{mode === 'name' ? 'Save name' : 'Save appearance'}</button>
  </form>;
}
