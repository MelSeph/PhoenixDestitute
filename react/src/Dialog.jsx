import React, { useEffect, useRef } from 'react';

export default function Dialog({ title, onClose, children }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement;
    dialog.showModal();
    return () => { dialog.close(); previous?.focus(); };
  }, []);
  function keepFocus(event) {
    if (event.key !== 'Tab') return;
    const controls = [...ref.current.querySelectorAll('button, input, select, textarea, a[href], [tabindex="0"]')].filter(element => !element.disabled);
    const first = controls[0], last = controls.at(-1);
    if ((!event.shiftKey && document.activeElement === last) || (event.shiftKey && document.activeElement === first)) {
      event.preventDefault();
      (event.shiftKey ? last : first)?.focus();
    }
  }
  return <dialog ref={ref} aria-label={title} onKeyDown={keepFocus} onCancel={event => { event.preventDefault(); onClose(); }}>
    <h2>{title}</h2>
    {children}
  </dialog>;
}
