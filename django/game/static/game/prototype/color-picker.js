"use strict";
// One dialog and one set of listeners serve all six appearance colors.
function initializeColorPicker() {
    const dialog = document.getElementById("custom-color-dialog");
    const hue = document.getElementById("picker-hue");
    const saturation = document.getElementById("picker-saturation");
    const lightness = document.getElementById("picker-lightness");
    const hex = document.getElementById("picker-hex");
    const preview = document.getElementById("picker-preview");
    const status = document.getElementById("picker-status");
    const apply = document.getElementById("picker-apply");
    const cancel = document.getElementById("picker-cancel");
    const title = document.getElementById("picker-title");
    if (![dialog,hue,saturation,lightness,hex,preview,status,apply,cancel,title].every(Boolean)) return;

    const settings = [
        {key:"panel", title:"Panel Background Color"},
        {key:"text", title:"Primary Text Color"},
        {key:"muted", title:"Muted Text Color"},
        {key:"accent", title:"Accent Color"},
        {key:"border", title:"Border Color"},
        {key:"button", title:"Button Background Color"},
        {key:"background", title:"Page Background Color"}
    ];
    const validHex = /^#[0-9a-f]{6}$/i;
    let active = null;
    let proposed = "#e5c78e";
    let returnFocus = null;

    function hslToHex(h,s,l) {
        s /= 100; l /= 100;
        const a = s * Math.min(l,1-l);
        const channel = n => {
            const k = (n + h / 30) % 12;
            return Math.round(255*(l-a*Math.max(-1,Math.min(k-3,9-k,1)))).toString(16).padStart(2,"0");
        };
        return `#${channel(0)}${channel(8)}${channel(4)}`;
    }
    function hexToHsl(value) {
        const [r,g,b] = [1,3,5].map(i => parseInt(value.slice(i,i+2),16)/255);
        const max=Math.max(r,g,b), min=Math.min(r,g,b), d=max-min;
        let h=0,s=0,l=(max+min)/2;
        if (d) {
            s=d/(1-Math.abs(2*l-1));
            switch(max) {
                case r: h=((g-b)/d)%6; break;
                case g: h=(b-r)/d+2; break;
                default: h=(r-g)/d+4;
            }
            h=(h*60+360)%360;
        }
        return [Math.round(h),Math.round(s*100),Math.round(l*100)];
    }
    function display(value, syncSliders=true) {
        proposed=value.toLowerCase();
        hex.value=proposed;
        preview.style.backgroundColor=proposed;
        preview.setAttribute("aria-label", `Selected color preview: ${proposed}`);
        if (syncSliders) {
            const [h,s,l]=hexToHsl(proposed);
            hue.value=h; saturation.value=s; lightness.value=l;
        }
        status.textContent="";
    }
    function checkContrast() {
        const previous=appearanceThemes.custom[active.key];
        appearanceThemes.custom[active.key]=proposed;
        try { return validateAppearanceTheme("custom"); }
        finally { appearanceThemes.custom[active.key]=previous; }
    }
    settings.forEach(setting => {
        const trigger=document.getElementById(`open-${setting.key}-picker`);
        const input=document.getElementById(`custom-${setting.key}-color`);
        const swatch=document.getElementById(`${setting.key}-color-swatch`);
        if (!trigger || !input || !swatch) return;
        setting.input=input;
        setting.swatch=swatch;
        const sync=()=>{ swatch.style.backgroundColor=appearanceThemes.custom[setting.key]; };
        trigger.addEventListener("click",()=>{
            active=setting;
            returnFocus=trigger;
            title.textContent=`Choose ${setting.title.toLowerCase()}`;
            display(appearanceThemes.custom[setting.key]);
            dialog.showModal();
            hex.focus();
        });
        document.getElementById("theme-selector")?.addEventListener("change",sync);
        sync();
    });
    [hue,saturation,lightness].forEach(slider=>slider.addEventListener("input",()=>{
        display(hslToHex(Number(hue.value),Number(saturation.value),Number(lightness.value)),false);
    }));
    hex.addEventListener("input",()=>{
        const value=hex.value.trim();
        if (validHex.test(value)) display(value);
        else { proposed=value; status.textContent="Enter a six-digit hex color, such as #e5c78e."; }
    });
    dialog.querySelectorAll("[data-color]").forEach(button=>{
        button.style.backgroundColor=button.dataset.color;
        button.addEventListener("click",()=>display(button.dataset.color));
    });
    cancel.addEventListener("click",()=>dialog.close());
    apply.addEventListener("click",()=>{
        if (!active) return;
        if (!validHex.test(proposed)) {
            status.textContent="Enter a valid six-digit hex color."; return;
        }
        if (!checkContrast()) {
            status.textContent="Color rejected: insufficient contrast. Choose another color."; return;
        }
        active.input.value=proposed;
        active.input.dispatchEvent(new Event("change",{bubbles:true}));
        // Existing appearance.js listener applies and saves the change.
        if (appearanceThemes.custom[active.key].toLowerCase()===proposed) {
            active.swatch.style.backgroundColor=proposed;
            dialog.close();
        } else {
            status.textContent="Color could not be applied.";
        }
    });
    // Native modal dialogs contain keyboard focus and support Escape.
    // Escape is a cancellation, not an Apply action.
    dialog.addEventListener("cancel",()=>{
        status.textContent="";
    });
    dialog.addEventListener("close",()=>{
        active=null;
        returnFocus?.focus();
        returnFocus=null;
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded",initializeColorPicker);
} else {
    initializeColorPicker();
}
