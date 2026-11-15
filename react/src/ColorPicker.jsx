import React, { useState } from 'react';
import Dialog from './Dialog.jsx';
import { colorLabels, isHex, validPalette } from './appearance.js';

function hexToHsl(hex) {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b), min = Math.min(r, g, b), difference = max - min;
  const lightness = (max + min) / 2;
  const hue = !difference ? 0 : max === r ? ((g - b) / difference + 6) % 6 : max === g ? (b - r) / difference + 2 : (r - g) / difference + 4;
  return [Math.round(hue * 60), Math.round((difference ? difference / (1 - Math.abs(2 * lightness - 1)) : 0) * 100), Math.round(lightness * 100)];
}
function hslToHex([h, s, l]) {
  s /= 100; l /= 100;
  const a = s * Math.min(l, 1 - l);
  return '#' + [0, 8, 4].map(n => {
    const k = (n + h / 30) % 12;
    return Math.round((l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))) * 255).toString(16).padStart(2, '0');
  }).join('');
}
const presets = { White: '#ffffff', Black: '#000000', Gold: '#e5c78e', Pink: '#ff0080', Red: '#ff0000', Green: '#22c55e', Blue: '#3b82f6', Purple: '#a855f7' };

export default function ColorPicker({ colorKey, colors, onApply, onClose }) {
  const [hex, setHex] = useState(colors[colorKey]);
  const [hsl, setHsl] = useState(() => hexToHsl(colors[colorKey]));
  const [error, setError] = useState('');
  function select(value) {
    setHex(value);
    if (isHex(value)) setHsl(hexToHsl(value));
    setError('');
  }
  function apply() {
    if (!isHex(hex)) { setError('Enter a six-digit hex color, such as #e5c78e.'); return; }
    const next = { ...colors, [colorKey]: hex.toLowerCase() };
    if (!validPalette(next)) { setError('This color would reduce contrast below the readability requirements. Choose another color.'); return; }
    onApply(next);
  }
  return <Dialog title={`Choose ${colorLabels[colorKey].toLowerCase()} color`} onClose={onClose}>
    <p className="help">Use Tab to move between controls, arrow keys to adjust sliders, and Escape to cancel.</p>
    <div className="color-preview" style={{ background: isHex(hex) ? hex : colors[colorKey] }} role="img" aria-label="Selected color preview" />
    {['Hue', 'Saturation', 'Lightness'].map((label, index) => <label key={label}>{label}: {hsl[index]}
      <input type="range" min="0" max={index === 0 ? 360 : 100} value={hsl[index]} onChange={event => {
        const next = hsl.map((value, i) => i === index ? Number(event.target.value) : value);
        setHsl(next); setHex(hslToHex(next)); setError('');
      }} />
    </label>)}
    <label>Hexadecimal color<input value={hex} maxLength={7} spellCheck={false} onChange={event => select(event.target.value)} aria-describedby="picker-error" /></label>
    <div className="presets" role="group" aria-label="Suggested colors">{Object.entries(presets).map(([label, color]) => <button key={label} aria-label={label} style={{ background: color }} onClick={() => select(color)} />)}</div>
    <p id="picker-error" role="status">{error}</p>
    <div className="actions"><button className="secondary" onClick={onClose}>Cancel</button><button onClick={apply}>Apply color</button></div>
  </Dialog>;
}
