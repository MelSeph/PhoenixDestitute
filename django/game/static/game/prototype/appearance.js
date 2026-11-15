
"use strict";

// PhoenixDestitute appearance settings.
// These preferences will eventually belong to
// the player's Django account.

const appearanceThemes = {
    midnight: {
        background: "#111820",
        panel: "#202d3a",
        border: "#718298",
        text: "#f1f5f9",
        muted: "#c0ccd9",
        accent: "#e5c78e",
        button: "#b5c8db"
    },

    daylight: {
        background: "#f1f4f8",
        panel: "#ffffff",
        border: "#64748b",
        text: "#182536",
        muted: "#45546a",
        accent: "#234f85",
        button: "#234f85"
    },

    highContrast: {
        background: "#000000",
        panel: "#000000",
        border: "#ffffff",
        text: "#ffffff",
        muted: "#ffffff",
        accent: "#ffff00",
        button: "#ffffff"
    },

    custom: {
        background: "#111820",
        panel: "#202d3a",
        border: "#718298",
        text: "#f1f5f9",
        muted: "#c0ccd9",
        accent: "#e5c78e",
        button: "#b5c8db"
    }
};

// Emergency fallback used when a selected theme is invalid.
// This palette is independent of player-created themes.
const fallbackAppearanceTheme = Object.freeze({
    background: "#000000",
    panel: "#000000",
    border: "#ffffff",
    text: "#ffffff",
    muted: "#ffffff",
    accent: "#ffff00",
    button: "#ffffff"
});

// Calculate the WCAG contrast ratio between two hex colors.
function calculateContrastRatio(color1, color2) {

    // Convert a six-digit hex color to relative luminance.
    function getLuminance(hexColor) {
        const hex = hexColor.replace("#", "");

        // Require exactly six hexadecimal characters.
        if (!/^[0-9a-fA-F]{6}$/.test(hex)) {
            throw new Error("Invalid hex color: " + hexColor);
        }

        const red = parseInt(hex.substring(0, 2), 16) / 255;
        const green = parseInt(hex.substring(2, 4), 16) / 255;
        const blue = parseInt(hex.substring(4, 6), 16) / 255;

        // Convert sRGB channels to linear-light values.
        function linearize(channel) {
            return channel <= 0.04045
                ? channel / 12.92
                : Math.pow((channel + 0.055) / 1.055, 2.4);
        }

        return (
            0.2126 * linearize(red) +
            0.7152 * linearize(green) +
            0.0722 * linearize(blue)
        );
    }

    const luminance1 = getLuminance(color1);
    const luminance2 = getLuminance(color2);

    const lighter = Math.max(luminance1, luminance2);
    const darker = Math.min(luminance1, luminance2);

    return (lighter + 0.05) / (darker + 0.05);
}

function buttonLabelColor(buttonBackground) {
    return calculateContrastRatio(buttonBackground, "#000000") >=
        calculateContrastRatio(buttonBackground, "#ffffff") ? "#000000" : "#ffffff";
}

function validateAppearanceTheme(themeName) {
    const theme = appearanceThemes[themeName];

    if (!theme) {
        console.warn("Unknown theme:", themeName);
        return false;
    }

    const textChecks = [
        {
            label: "Primary text on panel",
            foreground: theme.text,
            background: theme.panel
        },
        {
            label: "Muted text on panel",
            foreground: theme.muted,
            background: theme.panel
        },
        {
            label: "Accent text on panel",
            foreground: theme.accent,
            background: theme.panel
        },
        {
            label: "Primary text on page background",
            foreground: theme.text,
            background: theme.background
        },
        {
            label: "Muted text on page background",
            foreground: theme.muted,
            background: theme.background
        },
        {
            label: "Accent text on page background",
            foreground: theme.accent,
            background: theme.background
        }
    ];

    const borderChecks = [
        {
            label: "Border against panel",
            foreground: theme.border,
            background: theme.panel
        },
        {
            label: "Border against page background",
            foreground: theme.border,
            background: theme.background
        }
    ];

    const buttonChecks = [
        {label: "Button against panel", foreground: theme.button, background: theme.panel, minimum: 3},
        {label: "Button against page", foreground: theme.button, background: theme.background, minimum: 3},
        {label: "Button label", foreground: buttonLabelColor(theme.button), background: theme.button, minimum: 4.5}
    ];

    let allPassed = true;

    console.log("Validating theme:", themeName);

    textChecks.forEach(function (check) {
        const ratio = calculateContrastRatio(
            check.foreground,
            check.background
        );

        const passed = ratio >= 4.5;

        if (!passed) {
            allPassed = false;
        }

        console.log(
            check.label + ":",
            ratio.toFixed(2) + ":1",
            passed ? "PASS" : "FAIL"
        );
    });

    borderChecks.forEach(function (check) {
        const ratio = calculateContrastRatio(
            check.foreground,
            check.background
        );

        const passed = ratio >= 3;

        if (!passed) {
            allPassed = false;
        }

        console.log(
            check.label + ":",
            ratio.toFixed(2) + ":1",
            passed ? "PASS" : "FAIL"
        );
    });

    buttonChecks.forEach(function (check) {
        const ratio = calculateContrastRatio(check.foreground, check.background);
        const passed = ratio >= check.minimum;
        if (!passed) allPassed = false;
        console.log(check.label + ":", ratio.toFixed(2) + ":1", passed ? "PASS" : "FAIL");
    });

    return allPassed;
}

function saveCustomAppearanceColors() {
    const customColors = {
        panel: appearanceThemes.custom.panel,
        text: appearanceThemes.custom.text,
        muted: appearanceThemes.custom.muted,
        accent: appearanceThemes.custom.accent,
        border: appearanceThemes.custom.border,
        button: appearanceThemes.custom.button,
        background: appearanceThemes.custom.background
    };

    try {
        localStorage.setItem(
            "phoenixdestitute-custom-colors",
            JSON.stringify(customColors)
        );

        return true;
    } catch (error) {
        console.warn("Unable to save custom colors:", error);
        return false;
    }
}

function loadCustomAppearanceColors() {
    try {
        const storedColors = localStorage.getItem(
            "phoenixdestitute-custom-colors"
        );

        if (!storedColors) {
            return;
        }

        const parsedColors = JSON.parse(storedColors);
        console.log("LOADING CUSTOM COLORS:", parsedColors);


        if (
            !parsedColors ||
            typeof parsedColors !== "object" ||
            Array.isArray(parsedColors)
        ) {
            console.warn("Invalid saved custom colors.");
            return;
        }

        const validHexColor = /^#[0-9a-fA-F]{6}$/;

        const previousColors = {
            panel: appearanceThemes.custom.panel,
            text: appearanceThemes.custom.text,
            muted: appearanceThemes.custom.muted,
            accent: appearanceThemes.custom.accent,
            border: appearanceThemes.custom.border,
            button: appearanceThemes.custom.button,
            background: appearanceThemes.custom.background
        };

        // Validate both colors before changing the theme.
        if (
            parsedColors.panel !== undefined &&
            (
                typeof parsedColors.panel !== "string" ||
                !validHexColor.test(parsedColors.panel)
            )
        ) {
            console.warn("Invalid saved panel color.");
            return;
        }

        if (
            parsedColors.text !== undefined &&
            (
                typeof parsedColors.text !== "string" ||
                !validHexColor.test(parsedColors.text)
            )
        ) {
            console.warn("Invalid saved text color.");
            return;
        }

        if (
            parsedColors.muted !== undefined &&
            (
                typeof parsedColors.muted !== "string" ||
                !validHexColor.test(parsedColors.muted)
            )
        ) {
            console.warn("Invalid saved muted color.");
            return;
        }

        if (
            parsedColors.accent !== undefined &&
            (
                typeof parsedColors.accent !== "string" ||
                !validHexColor.test(parsedColors.accent)
            )
        ) {
            console.warn("Invalid saved accent color.");
            return;
        }

        if (
            parsedColors.border !== undefined &&
            (
                typeof parsedColors.border !== "string" ||
                !validHexColor.test(parsedColors.border)
            )
        ) {
            console.warn("Invalid saved border color.");
            return;
        }

        if (
            parsedColors.background !== undefined && (
                typeof parsedColors.background !== "string" ||
                !validHexColor.test(parsedColors.background)
            )
        ) {
            console.warn("Invalid saved page background color.");
            return;
        }

        if (parsedColors.button !== undefined && (typeof parsedColors.button !== "string" || !validHexColor.test(parsedColors.button))) {
            console.warn("Invalid saved button color.");
            return;
        }

        // Older saves may contain only the panel color.
        if (parsedColors.panel !== undefined) {
            appearanceThemes.custom.panel = parsedColors.panel;
        }

        if (parsedColors.text !== undefined) {
            appearanceThemes.custom.text = parsedColors.text;
        }

        if (parsedColors.muted !== undefined) {
            appearanceThemes.custom.muted = parsedColors.muted;
        }

        if (parsedColors.accent !== undefined) {
            appearanceThemes.custom.accent = parsedColors.accent;
        }

        if (parsedColors.border !== undefined) {
            appearanceThemes.custom.border = parsedColors.border;
        }

        if (parsedColors.button !== undefined) {
            appearanceThemes.custom.button = parsedColors.button;
        }

        if (parsedColors.background !== undefined) {
            appearanceThemes.custom.background = parsedColors.background;
        }

        console.log(
            "CUSTOM COLORS BEFORE VALIDATION:",
            appearanceThemes.custom
        );

        // Validate the combined palette.
        if (!validateAppearanceTheme("custom")) {
            appearanceThemes.custom.panel = previousColors.panel;
            appearanceThemes.custom.text = previousColors.text;
            appearanceThemes.custom.muted = previousColors.muted;
            appearanceThemes.custom.accent = previousColors.accent;
            appearanceThemes.custom.border = previousColors.border;
            appearanceThemes.custom.button = previousColors.button;
            appearanceThemes.custom.background = previousColors.background;


            console.warn(
                "Saved custom colors failed accessibility checks."
            );
        }
        console.log("CUSTOM COLORS AFTER LOAD:", appearanceThemes.custom);
    } catch (error) {
        console.warn("Unable to load custom colors:", error);
    }
}

function applyFallbackAppearanceTheme() {
    const root = document.documentElement;
    const theme = fallbackAppearanceTheme;

    root.style.setProperty("--color-background", theme.background);
    root.style.setProperty("--color-panel", theme.panel);
    root.style.setProperty("--color-border", theme.border);
    root.style.setProperty("--color-text", theme.text);
    root.style.setProperty("--color-muted", theme.muted);
    root.style.setProperty("--color-accent", theme.accent);
    root.style.setProperty("--color-button", theme.button);
    root.style.setProperty("--color-button-text", buttonLabelColor(theme.button));

    console.warn("Emergency fallback appearance applied.");
}

// Apply a selected theme to the interface.
function applyAppearanceTheme(themeName) {
    const theme = appearanceThemes[themeName];

    // Prevent errors if the theme doesn't exist.
    if (!theme) {
        console.warn("Unknown appearance theme:", themeName);
        return false;
    }

    // Reject themes that fail our current text contrast checks.
    if (!validateAppearanceTheme(themeName)) {
        console.warn(
            "Theme rejected because it failed accessibility checks:",
            themeName
        );
        return false;
    }

    // Update the CSS variables on the root element.
    const root = document.documentElement;

    root.style.setProperty("--color-background", theme.background);
    root.style.setProperty("--color-panel", theme.panel);
    root.style.setProperty("--color-border", theme.border);
    root.style.setProperty("--color-text", theme.text);
    root.style.setProperty("--color-muted", theme.muted);
    root.style.setProperty("--color-accent", theme.accent);
    root.style.setProperty("--color-button", theme.button);
    root.style.setProperty("--color-button-text", buttonLabelColor(theme.button));

    console.log("Appearance theme applied:", themeName);

    return true;
}

// Initialize the appearance settings controls.
function initializeAppearanceSettings() {
    console.log("INITIALIZE APPEARANCE SETTINGS CALLED");
    const themeSelector = document.getElementById("theme-selector");

    if (!themeSelector) {
        return;
    }

    // Load the player's previously selected theme.
    let savedTheme = "midnight";

    try {
        const storedTheme = localStorage.getItem(
            "phoenixdestitute-theme"
        );

        // Only accept themes that actually exist.
        if (Object.hasOwn(appearanceThemes, storedTheme)) {
            savedTheme = storedTheme;
        }
    } catch (error) {
        console.warn("Unable to read appearance preferences:", error);
    }

    console.log("ABOUT TO LOAD CUSTOM COLORS");
    loadCustomAppearanceColors();

    // Apply the saved theme and update the selector.
    themeSelector.value = savedTheme;

    // Attempt to apply the saved theme.
    if (!applyAppearanceTheme(savedTheme)) {
        // Try the standard Midnight theme.
        savedTheme = "midnight";

        if (!applyAppearanceTheme(savedTheme)) {
            // Both attempts failed. Use the protected fallback.
            applyFallbackAppearanceTheme();
            savedTheme = "fallback";
        }
    }

    // Keep the dropdown synchronized with the active palette.
    themeSelector.value = savedTheme;
    themeSelector.dataset.activeTheme = savedTheme;

    // Save future theme selections.
    themeSelector.addEventListener("change", function () {
        const selectedTheme = themeSelector.value;

        if (applyAppearanceTheme(selectedTheme)) {
            // Remember the last successfully applied theme.
            themeSelector.dataset.activeTheme = selectedTheme;

            try {
                localStorage.setItem(
                    "phoenixdestitute-theme",
                    selectedTheme
                );
            } catch (error) {
                console.warn("Unable to save appearance preferences:", error);
            }
        } else {
            // Restore the dropdown to the active theme.
            themeSelector.value = themeSelector.dataset.activeTheme;

            console.warn(
                "Theme selection reverted to:",
                themeSelector.value
            );
        }
    });
}

function initializeCustomColorSettings() {
    const themeSelector = document.getElementById("theme-selector");
    const customSettings = document.getElementById("custom-color-settings");
    const panelColorInput = document.getElementById("custom-panel-color");
    const textColorInput = document.getElementById("custom-text-color");
    const mutedColorInput = document.getElementById("custom-muted-color");
    const accentColorInput = document.getElementById("custom-accent-color");
    const borderColorInput = document.getElementById("custom-border-color");
    const buttonColorInput = document.getElementById("custom-button-color");
    const backgroundColorInput = document.getElementById("custom-background-color");
    const message = document.getElementById("custom-color-message");

    if (!themeSelector || !customSettings || !panelColorInput || !textColorInput || !mutedColorInput || !accentColorInput || !borderColorInput || !buttonColorInput || !backgroundColorInput || !message) {
        return;
    }

    function updateCustomSettingsVisibility() {
        const isCustom = themeSelector.value === "custom";

        customSettings.hidden = !isCustom;

        if (isCustom) {
            panelColorInput.value = appearanceThemes.custom.panel;
            textColorInput.value = appearanceThemes.custom.text;
            mutedColorInput.value = appearanceThemes.custom.muted;
            accentColorInput.value = appearanceThemes.custom.accent;
            borderColorInput.value = appearanceThemes.custom.border;
            buttonColorInput.value = appearanceThemes.custom.button;
            backgroundColorInput.value = appearanceThemes.custom.background;
        }
    }

    themeSelector.addEventListener(
        "change",
        updateCustomSettingsVisibility
    );

    buttonColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.button;
        const selectedColor = buttonColorInput.value;
        appearanceThemes.custom.button = selectedColor;
        if (!validateAppearanceTheme("custom") || !applyAppearanceTheme("custom")) {
            appearanceThemes.custom.button = previousColor;
            buttonColorInput.value = previousColor;
            message.textContent = "Button color rejected: insufficient contrast.";
            return;
        }
        const saved = saveCustomAppearanceColors();
        message.textContent = saved ? "Button color updated and saved." : "Button color updated, but could not be saved.";
    });

    panelColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.panel;
        const selectedColor = panelColorInput.value;

        // Temporarily test the new color.
        appearanceThemes.custom.panel = selectedColor;

        if (validateAppearanceTheme("custom")) {
            applyAppearanceTheme("custom");

            const saved = saveCustomAppearanceColors();

            message.textContent = saved
                ? "Panel color updated and saved."
                : "Panel color updated, but could not be saved.";
        } else {
            // Restore the last valid color.
            appearanceThemes.custom.panel = previousColor;
            panelColorInput.value = previousColor;

            message.textContent =
                "Color rejected: insufficient text contrast.";
        }
    });

    textColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.text;
        const selectedColor = textColorInput.value;

        // Temporarily test the selected text color.
        appearanceThemes.custom.text = selectedColor;

        if (validateAppearanceTheme("custom")) {
            if (applyAppearanceTheme("custom")) {
                const saved = saveCustomAppearanceColors();

                message.textContent = saved
                    ? "Primary text color updated and saved."
                    : "Primary text color updated, but could not be saved.";
            }
        } else {
            // Restore the last valid text color.
            appearanceThemes.custom.text = previousColor;
            textColorInput.value = previousColor;

            message.textContent =
                "Text color rejected: insufficient contrast.";
        }
    });

    mutedColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.muted;
        const selectedColor = mutedColorInput.value;

        // Temporarily test the selected muted text color.
        appearanceThemes.custom.muted = selectedColor;

        // Validate against both panel and page backgrounds.
        if (!validateAppearanceTheme("custom")) {
            appearanceThemes.custom.muted = previousColor;
            mutedColorInput.value = previousColor;

            message.textContent =
                "Muted text color rejected: insufficient contrast.";

            return;
        }

        // Apply the validated color.
        if (!applyAppearanceTheme("custom")) {
            appearanceThemes.custom.muted = previousColor;
            mutedColorInput.value = previousColor;

            message.textContent =
                "Muted text color could not be applied.";

            return;
        }

        const saved = saveCustomAppearanceColors();

        message.textContent = saved
            ? "Muted text color updated and saved."
            : "Muted text color updated, but could not be saved.";

    });

    accentColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.accent;
        const selectedColor = accentColorInput.value;

        // Temporarily test the player's selected accent color.
        appearanceThemes.custom.accent = selectedColor;

        if (!validateAppearanceTheme("custom")) {
            appearanceThemes.custom.accent = previousColor;
            accentColorInput.value = previousColor;

            message.textContent =
                "Accent color rejected: insufficient contrast.";

            return;
        }

        if (!applyAppearanceTheme("custom")) {
            appearanceThemes.custom.accent = previousColor;
            accentColorInput.value = previousColor;

            message.textContent =
                "Accent color could not be applied.";

            return;
        }

        const saved = saveCustomAppearanceColors();

        message.textContent = saved
            ? "Accent color updated and saved."
            : "Accent color updated, but could not be saved.";
    });

    borderColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.border;
        const selectedColor = borderColorInput.value;

        // Temporarily test the selected border color.
        appearanceThemes.custom.border = selectedColor;

        if (!validateAppearanceTheme("custom")) {
            appearanceThemes.custom.border = previousColor;
            borderColorInput.value = previousColor;

            message.textContent =
                "Border color rejected: insufficient contrast.";

            return;
        }

        if (!applyAppearanceTheme("custom")) {
            appearanceThemes.custom.border = previousColor;
            borderColorInput.value = previousColor;

            message.textContent =
                "Border color could not be applied.";

            return;
        }

        const saved = saveCustomAppearanceColors();

        message.textContent = saved
            ? "Border color updated and saved."
            : "Border color updated, but could not be saved.";
    });

    backgroundColorInput.addEventListener("change", function () {
        const previousColor = appearanceThemes.custom.background;
        const selectedColor = backgroundColorInput.value;

        // Test the player's proposed background color.
        appearanceThemes.custom.background = selectedColor;

        const isValid = validateAppearanceTheme("custom");

        if (!isValid) {
            // Reject the proposed color and restore the previous one.
            appearanceThemes.custom.background = previousColor;
            backgroundColorInput.value = previousColor;

            message.textContent =
                "Page background color rejected: insufficient contrast.";

            return;
        }

        // Apply the validated color.
        if (!applyAppearanceTheme("custom")) {
            appearanceThemes.custom.background = previousColor;
            backgroundColorInput.value = previousColor;

            message.textContent =
                "Page background color could not be applied.";

            return;
        }

        // Save only after successful application.
        const saved = saveCustomAppearanceColors();

        message.textContent = saved
            ? "Page background color updated and saved."
            : "Page background updated, but could not be saved.";
    });

    updateCustomSettingsVisibility();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAppearanceSettings);
} else {
    initializeAppearanceSettings();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded",initializeCustomColorSettings);
} else {
    initializeCustomColorSettings();
}


// Part 28: Independent font-size preference, unaffected by color theme changes.
const FONT_SIZE_STORAGE_KEY = "phoenixdestitute-font-size";
const ALLOWED_FONT_SIZES = [100, 125, 150, 200];

function applyFontSizePreference(percent) {
    if (!ALLOWED_FONT_SIZES.includes(percent)) return false;
    document.documentElement.style.fontSize = `${percent}%`;
    return true;
}

function initializeFontSizeSettings() {
    const selector = document.getElementById("font-size-selector");
    const status = document.getElementById("font-size-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(FONT_SIZE_STORAGE_KEY); }
    catch (error) { console.warn("Font preference storage unavailable:", error); }

    const parsed = saved === null ? 100 : Number(saved);
    const initial = ALLOWED_FONT_SIZES.includes(parsed) ? parsed : 100;
    applyFontSizePreference(initial);
    selector.value = String(initial);

    selector.addEventListener("change", () => {
        const selected = Number(selector.value);
        if (!applyFontSizePreference(selected)) {
            status.textContent = "Unsupported font size.";
            return;
        }
        try {
            localStorage.setItem(FONT_SIZE_STORAGE_KEY, String(selected));
            status.textContent = `Text size set to ${selected}% and saved.`;
        } catch (error) {
            status.textContent = `Text size set to ${selected}%, but could not be saved.`;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeFontSizeSettings);
} else {
    initializeFontSizeSettings();
}

// Part 29: Independent line-spacing preference.
const LINE_SPACING_STORAGE_KEY = "phoenixdestitute-line-spacing";
const LINE_SPACING_OPTIONS = Object.freeze({compact: "1.4", comfortable: "1.6", spacious: "1.9"});

function applyLineSpacingPreference(option) {
    if (!Object.hasOwn(LINE_SPACING_OPTIONS, option)) return false;
    document.documentElement.style.setProperty("--body-line-height", LINE_SPACING_OPTIONS[option]);
    return true;
}

function initializeLineSpacingSettings() {
    const selector = document.getElementById("line-spacing-selector");
    const status = document.getElementById("line-spacing-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(LINE_SPACING_STORAGE_KEY); }
    catch (error) { console.warn("Line spacing storage unavailable:", error); }

    const initial = saved !== null && Object.hasOwn(LINE_SPACING_OPTIONS, saved)
        ? saved : "comfortable";
    applyLineSpacingPreference(initial);
    selector.value = initial;

    selector.addEventListener("change", () => {
        const selected = selector.value;
        if (!applyLineSpacingPreference(selected)) {
            status.textContent = "Unsupported line spacing.";
            return;
        }
        try {
            localStorage.setItem(LINE_SPACING_STORAGE_KEY, selected);
            status.textContent = `Line spacing set to ${selected} and saved.`;
        } catch (error) {
            status.textContent = `Line spacing set to ${selected}, but could not be saved.`;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeLineSpacingSettings);
} else {
    initializeLineSpacingSettings();
}

// Part 30: Independent letter-spacing preference.
const LETTER_SPACING_STORAGE_KEY = "phoenixdestitute-letter-spacing";
const LETTER_SPACING_OPTIONS = Object.freeze({normal: "0em", relaxed: "0.03em", wide: "0.06em"});

function applyLetterSpacingPreference(option) {
    if (!Object.hasOwn(LETTER_SPACING_OPTIONS, option)) return false;
    document.documentElement.style.setProperty("--body-letter-spacing", LETTER_SPACING_OPTIONS[option]);
    return true;
}

function initializeLetterSpacingSettings() {
    const selector = document.getElementById("letter-spacing-selector");
    const status = document.getElementById("letter-spacing-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(LETTER_SPACING_STORAGE_KEY); }
    catch (error) { console.warn("Letter spacing storage unavailable:", error); }

    const initial = saved !== null && Object.hasOwn(LETTER_SPACING_OPTIONS, saved)
        ? saved : "normal";
    applyLetterSpacingPreference(initial);
    selector.value = initial;

    selector.addEventListener("change", () => {
        const selected = selector.value;
        if (!applyLetterSpacingPreference(selected)) {
            status.textContent = "Unsupported letter spacing.";
            return;
        }
        try {
            localStorage.setItem(LETTER_SPACING_STORAGE_KEY, selected);
            status.textContent = `Letter spacing set to ${selected} and saved.`;
        } catch (error) {
            status.textContent = `Letter spacing set to ${selected}, but could not be saved.`;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeLetterSpacingSettings);
} else {
    initializeLetterSpacingSettings();
}

// Part 31: Independent word-spacing preference.
const WORD_SPACING_STORAGE_KEY = "phoenixdestitute-word-spacing";
const WORD_SPACING_OPTIONS = Object.freeze({normal: "0em", relaxed: "0.1em", wide: "0.2em"});

function applyWordSpacingPreference(option) {
    if (!Object.hasOwn(WORD_SPACING_OPTIONS, option)) return false;
    document.documentElement.style.setProperty("--body-word-spacing", WORD_SPACING_OPTIONS[option]);
    return true;
}

function initializeWordSpacingSettings() {
    const selector = document.getElementById("word-spacing-selector");
    const status = document.getElementById("word-spacing-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(WORD_SPACING_STORAGE_KEY); }
    catch (error) { console.warn("Word spacing storage unavailable:", error); }

    const initial = saved !== null && Object.hasOwn(WORD_SPACING_OPTIONS, saved)
        ? saved : "normal";
    applyWordSpacingPreference(initial);
    selector.value = initial;

    selector.addEventListener("change", () => {
        const selected = selector.value;
        if (!applyWordSpacingPreference(selected)) {
            status.textContent = "Unsupported word spacing.";
            return;
        }
        try {
            localStorage.setItem(WORD_SPACING_STORAGE_KEY, selected);
            status.textContent = `Word spacing set to ${selected} and saved.`;
        } catch (error) {
            status.textContent = `Word spacing set to ${selected}, but could not be saved.`;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeWordSpacingSettings);
} else {
    initializeWordSpacingSettings();
}

// Part 32: Independent paragraph-spacing preference for game prose.
const PARAGRAPH_SPACING_STORAGE_KEY = "phoenixdestitute-paragraph-spacing";
const PARAGRAPH_SPACING_OPTIONS = Object.freeze({compact: "0.5em", comfortable: "1em", spacious: "1.5em"});

function applyParagraphSpacingPreference(option) {
    if (!Object.hasOwn(PARAGRAPH_SPACING_OPTIONS, option)) return false;
    document.documentElement.style.setProperty("--paragraph-spacing", PARAGRAPH_SPACING_OPTIONS[option]);
    return true;
}

function initializeParagraphSpacingSettings() {
    const selector = document.getElementById("paragraph-spacing-selector");
    const status = document.getElementById("paragraph-spacing-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(PARAGRAPH_SPACING_STORAGE_KEY); }
    catch (error) { console.warn("Paragraph spacing storage unavailable:", error); }

    const initial = saved !== null && Object.hasOwn(PARAGRAPH_SPACING_OPTIONS, saved)
        ? saved : "comfortable";
    applyParagraphSpacingPreference(initial);
    selector.value = initial;

    selector.addEventListener("change", () => {
        const selected = selector.value;
        if (!applyParagraphSpacingPreference(selected)) {
            status.textContent = "Unsupported paragraph spacing.";
            return;
        }
        try {
            localStorage.setItem(PARAGRAPH_SPACING_STORAGE_KEY, selected);
            status.textContent = `Paragraph spacing set to ${selected} and saved.`;
        } catch (error) {
            status.textContent = `Paragraph spacing set to ${selected}, but could not be saved.`;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeParagraphSpacingSettings);
} else {
    initializeParagraphSpacingSettings();
}

// Part 33: Independent font-family preference; no remote font downloads.
const FONT_FAMILY_STORAGE_KEY = "phoenixdestitute-font-family";
const FONT_FAMILY_OPTIONS = Object.freeze({
    sans: 'Arial, Helvetica, sans-serif',
    serif: 'Georgia, "Times New Roman", serif',
    mono: '"Courier New", Courier, monospace'
});

function applyFontFamilyPreference(option) {
    if (!Object.hasOwn(FONT_FAMILY_OPTIONS, option)) return false;
    document.documentElement.style.setProperty("--body-font-family", FONT_FAMILY_OPTIONS[option]);
    return true;
}

function initializeFontFamilySettings() {
    const selector = document.getElementById("font-family-selector");
    const status = document.getElementById("font-family-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(FONT_FAMILY_STORAGE_KEY); }
    catch (error) { console.warn("Font family storage unavailable:", error); }

    const initial = saved !== null && Object.hasOwn(FONT_FAMILY_OPTIONS, saved)
        ? saved : "sans";
    applyFontFamilyPreference(initial);
    selector.value = initial;

    selector.addEventListener("change", () => {
        const selected = selector.value;
        if (!applyFontFamilyPreference(selected)) {
            status.textContent = "Unsupported font style.";
            return;
        }
        try {
            localStorage.setItem(FONT_FAMILY_STORAGE_KEY, selected);
            status.textContent = `Font style set to ${selector.selectedOptions[0].textContent} and saved.`;
        } catch (error) {
            status.textContent = `Font style changed, but could not be saved.`;
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeFontFamilySettings);
} else {
    initializeFontFamilySettings();
}

// Part 34: Reading width preference applies to narrative content only.
const READING_WIDTH_STORAGE_KEY = "phoenixdestitute-reading-width";
const READING_WIDTH_OPTIONS = Object.freeze({ narrow: "45ch", standard: "65ch", wide: "85ch" });

function applyReadingWidthPreference(option) {
    if (!Object.hasOwn(READING_WIDTH_OPTIONS, option)) return false;
    document.documentElement.style.setProperty("--reading-width", READING_WIDTH_OPTIONS[option]);
    return true;
}

function initializeReadingWidthSettings() {
    const selector = document.getElementById("reading-width-selector");
    const status = document.getElementById("reading-width-message");
    if (!selector || !status) return;

    let saved = null;
    try { saved = localStorage.getItem(READING_WIDTH_STORAGE_KEY); }
    catch (error) { console.warn("Reading width storage unavailable:", error); }

    const initial = saved !== null && Object.hasOwn(READING_WIDTH_OPTIONS, saved)
        ? saved : "standard";
    applyReadingWidthPreference(initial);
    selector.value = initial;

    selector.addEventListener("change", () => {
        const selected = selector.value;
        if (!applyReadingWidthPreference(selected)) {
            status.textContent = "Unsupported reading width.";
            return;
        }
        try {
            localStorage.setItem(READING_WIDTH_STORAGE_KEY, selected);
            status.textContent = `Reading width set to ${selector.selectedOptions[0].textContent} and saved.`;
        } catch (error) {
            status.textContent = "Reading width changed, but could not be saved.";
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeReadingWidthSettings);
} else {
    initializeReadingWidthSettings();
}


// Part 35: Restore only the seven readability preferences, never theme colors.
const READABILITY_DEFAULTS = Object.freeze([
    { key: FONT_SIZE_STORAGE_KEY, selector: "font-size-selector", value: "100", apply: () => applyFontSizePreference(100) },
    { key: LINE_SPACING_STORAGE_KEY, selector: "line-spacing-selector", value: "comfortable", apply: () => applyLineSpacingPreference("comfortable") },
    { key: LETTER_SPACING_STORAGE_KEY, selector: "letter-spacing-selector", value: "normal", apply: () => applyLetterSpacingPreference("normal") },
    { key: WORD_SPACING_STORAGE_KEY, selector: "word-spacing-selector", value: "normal", apply: () => applyWordSpacingPreference("normal") },
    { key: PARAGRAPH_SPACING_STORAGE_KEY, selector: "paragraph-spacing-selector", value: "comfortable", apply: () => applyParagraphSpacingPreference("comfortable") },
    { key: FONT_FAMILY_STORAGE_KEY, selector: "font-family-selector", value: "sans", apply: () => applyFontFamilyPreference("sans") },
    { key: READING_WIDTH_STORAGE_KEY, selector: "reading-width-selector", value: "standard", apply: () => applyReadingWidthPreference("standard") }
]);

function initializeReadabilityReset() {
    const button = document.getElementById("reset-readability-button");
    const status = document.getElementById("readability-reset-message");
    if (!button || !status) return;
    button.addEventListener("click", () => {
        if (!window.confirm("Restore all seven readability settings to defaults? Your color theme and custom colors will be kept.")) return;
        let storageFailed = false;
        for (const setting of READABILITY_DEFAULTS) {
            setting.apply();
            const selector = document.getElementById(setting.selector);
            if (selector) selector.value = setting.value;
            try { localStorage.removeItem(setting.key); }
            catch (error) { storageFailed = true; console.warn("Could not clear readability preference:", setting.key, error); }
            const message = document.getElementById(setting.selector.replace("-selector", "-message"));
            if (message) message.textContent = "";
        }
        status.textContent = storageFailed
            ? "Readability defaults restored for this page, but some settings could not be cleared from storage."
            : "All seven readability settings restored to defaults. Your colors are unchanged.";
        button.focus();
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeReadabilityReset);
} else {
    initializeReadabilityReset();
}


// Part 36: Restore the original palette without touching readability preferences.
// Keep this independent of the emergency fallback and the other preset palettes.
const DEFAULT_CUSTOM_COLORS = Object.freeze({
    background: "#111820",
    panel: "#202d3a",
    border: "#718298",
    text: "#f1f5f9",
    muted: "#c0ccd9",
    accent: "#e5c78e",
    button: "#b5c8db"
});

function initializeColorReset() {
    const button = document.getElementById("reset-colors-button");
    const status = document.getElementById("color-reset-message");
    const selector = document.getElementById("theme-selector");
    if (!button || !status || !selector) return;

    button.addEventListener("click", () => {
        if (!window.confirm("Restore the Midnight theme and all seven Custom colors to their defaults? Your readability settings will be kept.")) return;

        // Restore every custom field together so contrast checks see a valid palette.
        Object.assign(appearanceThemes.custom, DEFAULT_CUSTOM_COLORS);
        if (!applyAppearanceTheme("midnight")) {
            status.textContent = "Could not restore the default color theme.";
            return;
        }

        selector.value = "midnight";
        selector.dataset.activeTheme = "midnight";
        const customSettings = document.getElementById("custom-color-settings");
        if (customSettings) customSettings.hidden = true;

        // Update hidden color inputs and swatches without dispatching change
        // events (which would unnecessarily re-save custom colors).
        for (const [key, color] of Object.entries(DEFAULT_CUSTOM_COLORS)) {
            const input = document.getElementById(`custom-${key}-color`);
            if (input) input.value = color;
            const swatch = document.getElementById(`${key}-color-swatch`);
            if (swatch) swatch.style.backgroundColor = color;
        }
        const customMessage = document.getElementById("custom-color-message");
        if (customMessage) customMessage.textContent = "";

        let storageFailed = false;
        try { localStorage.removeItem("phoenixdestitute-custom-colors"); }
        catch (error) { storageFailed = true; console.warn("Unable to clear custom colors:", error); }
        try { localStorage.setItem("phoenixdestitute-theme", "midnight"); }
        catch (error) { storageFailed = true; console.warn("Unable to save default theme:", error); }

        status.textContent = storageFailed
            ? "Default colors restored for this page, but some preferences could not be saved."
            : "Midnight theme and all seven Custom colors restored to defaults. Readability settings are unchanged.";
        button.focus();
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeColorReset);
} else {
    initializeColorReset();
}


// Part 37: Export the current live appearance state, without modifying preferences.
// Versioned, structured JSON will support a separately validated import feature later.
function buildAppearanceBackup() {
    const themeSelector = document.getElementById("theme-selector");
    const theme = themeSelector && Object.hasOwn(appearanceThemes, themeSelector.value)
        ? themeSelector.value : "midnight";
    const colors = {};
    for (const key of Object.keys(DEFAULT_CUSTOM_COLORS)) {
        colors[key] = appearanceThemes.custom[key];
    }
    const readability = {};
    for (const setting of READABILITY_DEFAULTS) {
        const selector = document.getElementById(setting.selector);
        readability[setting.key.replace("phoenixdestitute-", "")] = selector ? selector.value : setting.value;
    }
    return {
        format: "phoenixdestitute-appearance",
        version: 1,
        theme,
        customColors: colors,
        readability
    };
}

function initializeAppearanceExport() {
    const button = document.getElementById("export-appearance-button");
    const status = document.getElementById("appearance-export-message");
    if (!button || !status) return;
    button.addEventListener("click", () => {
        let url;
        try {
            const json = JSON.stringify(buildAppearanceBackup(), null, 2) + "\n";
            const blob = new Blob([json], { type: "application/json" });
            url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = "phoenixdestitute-appearance-backup.json";
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            status.textContent = "Appearance backup prepared. Check your browser downloads to save the JSON file.";
        } catch (error) {
            console.error("Unable to export appearance settings:", error);
            status.textContent = "Could not create the appearance backup. Your settings are unchanged.";
        } finally {
            if (url) window.setTimeout(() => URL.revokeObjectURL(url), 1000);
            button.focus();
        }
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAppearanceExport);
} else {
    initializeAppearanceExport();
}


// Part 38: Validate an entire appearance backup before changing any preference.
const APPEARANCE_BACKUP_MAX_BYTES = 65536;
const APPEARANCE_BACKUP_COLOR_KEYS = Object.freeze(Object.keys(DEFAULT_CUSTOM_COLORS));

function validateAppearanceBackup(data) {
    const isRecord = value => value !== null && typeof value === "object" && !Array.isArray(value);
    if (!isRecord(data) || data.format !== "phoenixdestitute-appearance" || data.version !== 1) {
        throw new Error("This is not a supported PhoenixDestitute appearance backup (version 1).");
    }
    if (!Object.hasOwn(appearanceThemes, data.theme) || data.theme === "fallback") {
        throw new Error("The backup contains an unknown color theme.");
    }
    if (!isRecord(data.customColors) || !isRecord(data.readability)) {
        throw new Error("The backup is missing color or readability settings.");
    }
    const colorKeys = Object.keys(data.customColors);
    if (colorKeys.length !== APPEARANCE_BACKUP_COLOR_KEYS.length ||
        !APPEARANCE_BACKUP_COLOR_KEYS.every(key => Object.hasOwn(data.customColors, key) &&
            typeof data.customColors[key] === "string" && /^#[0-9a-fA-F]{6}$/.test(data.customColors[key]))) {
        throw new Error("The backup must contain all seven valid six-digit Custom colors.");
    }
    const expectedKeys = READABILITY_DEFAULTS.map(setting => setting.key.replace("phoenixdestitute-", ""));
    if (Object.keys(data.readability).length !== expectedKeys.length ||
        !expectedKeys.every(key => Object.hasOwn(data.readability, key) && typeof data.readability[key] === "string")) {
        throw new Error("The backup must contain all seven readability preferences.");
    }
    const allowed = {
        "font-size": ["100", "125", "150", "200"],
        "line-spacing": Object.keys(LINE_SPACING_OPTIONS),
        "letter-spacing": Object.keys(LETTER_SPACING_OPTIONS),
        "word-spacing": Object.keys(WORD_SPACING_OPTIONS),
        "paragraph-spacing": Object.keys(PARAGRAPH_SPACING_OPTIONS),
        "font-family": Object.keys(FONT_FAMILY_OPTIONS),
        "reading-width": Object.keys(READING_WIDTH_OPTIONS)
    };
    for (const key of expectedKeys) {
        if (!allowed[key].includes(data.readability[key])) {
            throw new Error("Invalid readability preference: " + key + ".");
        }
    }
    // Validate the imported palette as a whole, even if a preset is selected.
    // Restore the live palette immediately after checking, including on error.
    const previous = { ...appearanceThemes.custom };
    let valid = false;
    try {
        Object.assign(appearanceThemes.custom, data.customColors);
        valid = validateAppearanceTheme("custom");
    } finally {
        Object.assign(appearanceThemes.custom, previous);
    }
    if (!valid) throw new Error("The backup's Custom colors do not meet contrast requirements.");
    return {
        theme: data.theme,
        customColors: Object.fromEntries(APPEARANCE_BACKUP_COLOR_KEYS.map(key => [key, data.customColors[key]])),
        readability: Object.fromEntries(expectedKeys.map(key => [key, data.readability[key]]))
    };
}

function applyImportedAppearanceBackup(backup) {
    const updates = [
        ["phoenixdestitute-theme", backup.theme],
        ["phoenixdestitute-custom-colors", JSON.stringify(backup.customColors)],
        ...READABILITY_DEFAULTS.map(setting => [setting.key, backup.readability[setting.key.replace("phoenixdestitute-", "")]])
    ];
    // Write all keys before touching the page. If storage fails, roll back
    // anything written so far and leave the live UI unchanged.
    const originals = new Map();
    try {
        for (const [key] of updates) originals.set(key, localStorage.getItem(key));
        for (const [key, value] of updates) localStorage.setItem(key, value);
    } catch (error) {
        for (const [key, value] of originals) {
            try { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value); }
            catch (rollbackError) { console.error("Could not restore saved setting:", key, rollbackError); }
        }
        throw new Error("Unable to save the imported settings. Your current page settings are unchanged.");
    }

    Object.assign(appearanceThemes.custom, backup.customColors);
    applyAppearanceTheme(backup.theme);
    const themeSelector = document.getElementById("theme-selector");
    if (themeSelector) {
        themeSelector.value = backup.theme;
        themeSelector.dataset.activeTheme = backup.theme;
    }
    const customSettings = document.getElementById("custom-color-settings");
    if (customSettings) customSettings.hidden = backup.theme !== "custom";
    for (const [key, color] of Object.entries(backup.customColors)) {
        const input = document.getElementById(`custom-${key}-color`);
        const swatch = document.getElementById(`${key}-color-swatch`);
        if (input) input.value = color;
        if (swatch) swatch.style.backgroundColor = color;
    }
    for (const setting of READABILITY_DEFAULTS) {
        const value = backup.readability[setting.key.replace("phoenixdestitute-", "")];
        const selector = document.getElementById(setting.selector);
        if (selector) selector.value = value;
        // Use the same code paths as the original preference controls.
        switch (setting.key) {
            case FONT_SIZE_STORAGE_KEY: applyFontSizePreference(Number(value)); break;
            case LINE_SPACING_STORAGE_KEY: applyLineSpacingPreference(value); break;
            case LETTER_SPACING_STORAGE_KEY: applyLetterSpacingPreference(value); break;
            case WORD_SPACING_STORAGE_KEY: applyWordSpacingPreference(value); break;
            case PARAGRAPH_SPACING_STORAGE_KEY: applyParagraphSpacingPreference(value); break;
            case FONT_FAMILY_STORAGE_KEY: applyFontFamilyPreference(value); break;
            case READING_WIDTH_STORAGE_KEY: applyReadingWidthPreference(value); break;
        }
    }
    // Part 45 fix: Import, Undo Import and Reset All use this shared application
    // path. Refresh only after every saved preference and control is updated.
    refreshLiveAppearanceSummary();
}

// Part 40: Compare against live settings, not stale values in a previous export.
// The comparison is read-only and never writes to localStorage.
function currentAppearanceForComparison() {
    const themeSelector = document.getElementById("theme-selector");
    const theme = themeSelector?.value || localStorage.getItem("phoenixdestitute-theme") || "midnight";
    const customColors = {};
    for (const key of APPEARANCE_BACKUP_COLOR_KEYS) {
        const input = document.getElementById(`custom-${key}-color`);
        customColors[key] = input?.value || appearanceThemes.custom[key];
    }
    const readability = {};
    for (const setting of READABILITY_DEFAULTS) {
        const key = setting.key.replace("phoenixdestitute-", "");
        const selector = document.getElementById(setting.selector);
        readability[key] = selector?.value || localStorage.getItem(setting.key) || String(setting.defaultValue);
    }
    return { theme, customColors, readability };
}

// Part 39: Render validated data using textContent, never imported HTML.
function showAppearanceImportPreview(backup) {
    const dialog = document.getElementById("appearance-import-preview-dialog");
    const content = document.getElementById("appearance-import-preview-content");
    if (!dialog || !content || typeof dialog.showModal !== "function") {
        throw new Error("The appearance preview is unavailable. No settings were changed.");
    }
    content.replaceChildren();
    const current = currentAppearanceForComparison();
    const differences = {
        theme: current.theme !== backup.theme,
        colors: Object.fromEntries(APPEARANCE_BACKUP_COLOR_KEYS.map(key => [key,
            current.customColors[key].toLowerCase() !== backup.customColors[key].toLowerCase()])),
        readability: Object.fromEntries(READABILITY_DEFAULTS.map(setting => {
            const key = setting.key.replace("phoenixdestitute-", "");
            return [key, current.readability[key] !== backup.readability[key]];
        }))
    };
    const changedCount = Number(differences.theme) +
        Object.values(differences.colors).filter(Boolean).length +
        Object.values(differences.readability).filter(Boolean).length;
    const summary = document.createElement("p");
    summary.className = "appearance-import-change-summary";
    summary.setAttribute("role", "status");
    summary.textContent = changedCount === 0
        ? "No differences found. Importing will keep your current appearance."
        : `${changedCount} of 15 settings differ from your current appearance. Changed values are marked below.`;
    content.appendChild(summary);
    const addSection = title => {
        const heading = document.createElement("h3");
        heading.textContent = title;
        content.appendChild(heading);
        const list = document.createElement("dl");
        list.className = "appearance-import-preview-list";
        content.appendChild(list);
        return list;
    };
    const addEntry = (list, label, value, swatch = false, changed = false, previous = "") => {
        const term = document.createElement("dt");
        term.textContent = label;
        const definition = document.createElement("dd");
        if (swatch) {
            const chip = document.createElement("span");
            chip.className = "appearance-import-preview-swatch";
            chip.style.backgroundColor = value;
            chip.setAttribute("aria-hidden", "true");
            definition.appendChild(chip);
        }
        definition.appendChild(document.createTextNode(value));
        if (changed) {
            const note = document.createElement("span");
            note.className = "appearance-import-change-note";
            note.textContent = `Changed from ${previous}`;
            definition.appendChild(note);
            term.classList.add("appearance-import-changed");
        }
        list.append(term, definition);
    };
    const themeNames = { midnight: "Midnight", daylight: "Daylight", highContrast: "High Contrast", custom: "Custom" };
    const themeList = addSection("Selected theme");
    addEntry(themeList, "Theme", themeNames[backup.theme] || backup.theme, false, differences.theme, themeNames[current.theme] || current.theme);
    const colors = addSection("Seven Custom colors");
    const colorLabels = { background: "Page background", panel: "Panel background", border: "Border", text: "Text", muted: "Muted text", accent: "Accent", button: "Button background" };
    for (const key of APPEARANCE_BACKUP_COLOR_KEYS) addEntry(colors, colorLabels[key] || key, backup.customColors[key], true, differences.colors[key], current.customColors[key]);
    const readability = addSection("Seven readability preferences");
    const readableLabels = { "font-size": "Font size", "font-family": "Font style", "line-spacing": "Line spacing", "letter-spacing": "Letter spacing", "word-spacing": "Word spacing", "paragraph-spacing": "Paragraph spacing", "reading-width": "Reading width" };
    const optionLabels = {
        "font-size": { "100": "Standard (100%)", "125": "Large (125%)", "150": "Extra Large (150%)", "200": "Maximum (200%)" },
        "font-family": { sans: "Sans Serif", serif: "Serif", monospace: "Monospace" }
    };
    for (const setting of READABILITY_DEFAULTS) {
        const key = setting.key.replace("phoenixdestitute-", "");
        const value = backup.readability[key];
        addEntry(readability, readableLabels[key] || key, optionLabels[key]?.[value] || value, false, differences.readability[key], optionLabels[key]?.[current.readability[key]] || current.readability[key]);
    }
    return new Promise(resolve => {
        const onClose = () => {
            dialog.removeEventListener("close", onClose);
            resolve(dialog.returnValue === "import");
        };
        dialog.addEventListener("close", onClose);
        dialog.returnValue = "cancel";
        try { dialog.showModal(); }
        catch (error) { dialog.removeEventListener("close", onClose); resolve(false); }
    });
}

// Part 41: A single in-memory undo snapshot, captured only after import confirmation.
// It deliberately expires on page refresh and is never exported or persisted.
let previousAppearanceBeforeImport = null;

// Firefox can restore dynamic button.disabled state on F5 or history navigation.
// The undo snapshot is deliberately memory-only, so always reflect its actual
// availability instead of trusting the browser-restored DOM property.
function synchronizeAppearanceImportUndoButton() {
    const undo = document.getElementById("undo-appearance-import-button");
    if (undo) undo.disabled = previousAppearanceBeforeImport === null;
}

// pageshow also runs when a page is restored from the back-forward cache.
window.addEventListener("pageshow", synchronizeAppearanceImportUndoButton);

function initializeAppearanceImportUndo() {
    const undo = document.getElementById("undo-appearance-import-button");
    const status = document.getElementById("undo-appearance-import-message");
    if (!undo || !status) return;
    synchronizeAppearanceImportUndoButton();
    undo.addEventListener("click", () => {
        if (!previousAppearanceBeforeImport) return;
        try {
            const snapshot = validateAppearanceBackup(previousAppearanceBeforeImport);
            applyImportedAppearanceBackup(snapshot);
            previousAppearanceBeforeImport = null;
            synchronizeAppearanceImportUndoButton();
            status.textContent = "Previous appearance restored. The undo option is now cleared.";
            const importStatus = document.getElementById("appearance-import-message");
            if (importStatus) importStatus.textContent = "Last import undone. Your previous settings are restored.";
        } catch (error) {
            console.error("Unable to undo appearance import:", error);
            status.textContent = "Undo could not be completed. The undo option remains available.";
        }
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAppearanceImportUndo);
} else {
    initializeAppearanceImportUndo();
}

function initializeAppearanceImport() {
    const button = document.getElementById("import-appearance-button");
    const input = document.getElementById("appearance-import-file");
    const status = document.getElementById("appearance-import-message");
    if (!button || !input || !status) return;
    button.addEventListener("click", async () => {
        const file = input.files && input.files[0];
        if (!file) { status.textContent = "Choose a JSON backup file first."; return; }
        if (file.size > APPEARANCE_BACKUP_MAX_BYTES) {
            status.textContent = "Backup file is too large (maximum 64 KB). No settings were changed.";
            return;
        }
        button.disabled = true;
        try {
            const data = JSON.parse(await file.text());
            const backup = validateAppearanceBackup(data);
            if (!await showAppearanceImportPreview(backup)) {
                status.textContent = "Import canceled. Your settings are unchanged.";
                return;
            }
            // Capture the pre-import state only after validation and confirmation.
            // Do not replace an existing undo snapshot if the import fails.
            const beforeImport = buildAppearanceBackup();
            applyImportedAppearanceBackup(backup);
            previousAppearanceBeforeImport = beforeImport;
            const undoButton = document.getElementById("undo-appearance-import-button");
            const undoStatus = document.getElementById("undo-appearance-import-message");
            synchronizeAppearanceImportUndoButton();
            if (undoStatus) undoStatus.textContent = "You can undo this import until the page is refreshed or another import succeeds.";
            status.textContent = "Appearance backup imported. All 14 preferences restored and saved.";
            input.value = "";
        } catch (error) {
            console.warn("Appearance import rejected:", error);
            status.textContent = "Import failed: " + (error instanceof SyntaxError ? "Invalid JSON file." : error.message) + " No settings were changed on this page.";
        } finally {
            button.disabled = false;
            button.focus();
        }
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAppearanceImport);
} else {
    initializeAppearanceImport();
}


// Part 42: Copy a human-readable snapshot without changing appearance settings.
function formatAppearanceSummary() {
    const backup = buildAppearanceBackup();
    const themeLabels = { midnight: "Midnight", daylight: "Daylight", highContrast: "High Contrast", custom: "Custom" };
    const colorLabels = {
        background: "Page Background", panel: "Panel Background", border: "Border",
        text: "Primary Text", muted: "Muted Text", accent: "Accent", button: "Button Background"
    };
    const readabilityLabels = {
        "font-size": "Font Size", "font-family": "Font Style", "line-spacing": "Line Spacing",
        "letter-spacing": "Letter Spacing", "word-spacing": "Word Spacing",
        "paragraph-spacing": "Paragraph Spacing", "reading-width": "Reading Width"
    };
    const lines = ["PhoenixDestitute Appearance Summary", "", "Selected theme: " + (themeLabels[backup.theme] || backup.theme), "", "Custom colors:"];
    for (const [key, value] of Object.entries(backup.customColors)) {
        lines.push("  " + (colorLabels[key] || key) + ": " + value);
    }
    lines.push("", "Readability preferences:");
    for (const [key, value] of Object.entries(backup.readability)) {
        lines.push("  " + (readabilityLabels[key] || key) + ": " + value);
    }
    return lines.join("\n");
}

function initializeAppearanceSummaryCopy() {
    const button = document.getElementById("copy-appearance-summary-button");
    const status = document.getElementById("appearance-copy-message");
    if (!button || !status) return;
    button.addEventListener("click", async () => {
        try {
            if (!navigator.clipboard || !navigator.clipboard.writeText) {
                throw new Error("Clipboard access is unavailable");
            }
            await navigator.clipboard.writeText(formatAppearanceSummary());
            status.textContent = "Appearance summary copied to clipboard. No settings were changed.";
        } catch (error) {
            console.warn("Unable to copy appearance summary:", error);
            status.textContent = "Could not copy the summary. Clipboard permission or a secure connection may be required. Your settings are unchanged.";
        }
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAppearanceSummaryCopy);
} else {
    initializeAppearanceSummaryCopy();
}


// Part 43: Save the readable Part 42 summary as a plain-text download.
// This does not alter preferences or replace the JSON backup format.
function initializeAppearanceSummaryDownload() {
    const button = document.getElementById("download-appearance-summary-button");
    const status = document.getElementById("appearance-download-message");
    if (!button || !status) return;
    button.addEventListener("click", () => {
        let url;
        try {
            const summary = formatAppearanceSummary() + "\n";
            const blob = new Blob([summary], { type: "text/plain;charset=utf-8" });
            url = URL.createObjectURL(blob);
            const anchor = document.createElement("a");
            anchor.href = url;
            anchor.download = "phoenixdestitute-appearance-summary.txt";
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            status.textContent = "Appearance summary prepared. Check your downloads for the text file. Your settings are unchanged.";
        } catch (error) {
            console.error("Unable to download appearance summary:", error);
            status.textContent = "Could not prepare the appearance summary text file. Your settings are unchanged.";
        } finally {
            if (url) window.setTimeout(() => URL.revokeObjectURL(url), 1000);
            button.focus();
        }
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAppearanceSummaryDownload);
} else {
    initializeAppearanceSummaryDownload();
}


// Part 44: One confirmed reset for the entire appearance, using the existing
// transactional import application path. Never call the individual reset buttons:
// doing so would show multiple confirmation prompts and risk partial updates.
function initializeFullAppearanceReset() {
    const button = document.getElementById("reset-all-appearance-button");
    const status = document.getElementById("appearance-reset-all-message");
    if (!button || !status) return;
    button.addEventListener("click", () => {
        if (!window.confirm("Restore the Midnight theme, all seven Custom colors, and all seven readability preferences to defaults? Export a backup first if you want to keep your current settings.")) return;
        const defaults = {
            theme: "midnight",
            customColors: { ...DEFAULT_CUSTOM_COLORS },
            readability: Object.fromEntries(READABILITY_DEFAULTS.map(setting => [
                setting.key.replace("phoenixdestitute-", ""), setting.value
            ]))
        };
        try {
            applyImportedAppearanceBackup(defaults);
            // A pending import undo must not silently overwrite a deliberate full reset.
            previousAppearanceBeforeImport = null;
            const undo = document.getElementById("undo-appearance-import-button");
            synchronizeAppearanceImportUndoButton();
            const undoStatus = document.getElementById("undo-appearance-import-message");
            if (undoStatus) undoStatus.textContent = "Import undo cleared by the full appearance reset.";
            for (const id of ["readability-reset-message", "color-reset-message", "custom-color-message"]) {
                const message = document.getElementById(id);
                if (message) message.textContent = "";
            }
            status.textContent = "All appearance defaults restored and saved. Your backup files are unchanged.";
        } catch (error) {
            console.error("Unable to reset all appearance settings:", error);
            status.textContent = "Could not save the full reset. Your current page appearance was not changed.";
        }
        button.focus();
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeFullAppearanceReset);
} else {
    initializeFullAppearanceReset();
}


// Part 45: Show the same source-of-truth summary used by Copy and Download.
// Part 50: Count differences from defaults without writing to storage.
// The theme selection is displayed separately; the count covers 7 custom
// palette values and 7 readability preferences (14 total).
function refreshAppearanceCustomizationStatus() {
    const status = document.getElementById("appearance-customization-status");
    if (!status) return;
    const current = currentAppearanceForComparison();
    const changedColors = Object.keys(DEFAULT_CUSTOM_COLORS).filter(key =>
        String(current.customColors[key]).toLowerCase() !== DEFAULT_CUSTOM_COLORS[key].toLowerCase()
    ).length;
    const changedReadability = READABILITY_DEFAULTS.filter(setting => {
        const key = setting.key.replace("phoenixdestitute-", "");
        return String(current.readability[key]) !== String(setting.value);
    }).length;
    const total = changedColors + changedReadability;
    status.textContent = `Customized preferences: ${total} of 14 (${changedColors} colors, ${changedReadability} readability). Selected theme: ${current.theme}.`;
}

function refreshLiveAppearanceSummary() {
    const preview = document.getElementById("appearance-live-summary-text");
    if (preview) preview.textContent = formatAppearanceSummary();
    refreshAppearanceCustomizationStatus();
}

function initializeLiveAppearanceSummary() {
    const preview = document.getElementById("appearance-live-summary-text");
    if (!preview) return;
    // Part 47: Persist only the summary disclosure state, not appearance settings.
    const details = document.getElementById("appearance-live-summary-details");
    const summaryStateKey = "phoenix-appearance-live-summary-open";
    const displayStatus = document.getElementById("appearance-summary-display-status");
    const updateDisplayStatus = () => {
        if (details && displayStatus) displayStatus.textContent =
            "Summary display: " + (details.open ? "Expanded" : "Collapsed");
    };
    if (details) {
        try {
            const stored = window.localStorage.getItem(summaryStateKey);
            if (stored === "true" || stored === "false") details.open = stored === "true";
        } catch (_) { /* Storage unavailable: default to expanded. */ }
        updateDisplayStatus();
        details.addEventListener("toggle", () => {
            updateDisplayStatus();
            try { window.localStorage.setItem(summaryStateKey, String(details.open)); }
            catch (_) { /* Keep disclosure functional without storage. */ }
        });
    }
    // Part 48: Reset the disclosure preference without touching appearance values.
    const resetSummaryButton = document.getElementById("reset-summary-display-button");
    const resetSummaryMessage = document.getElementById("reset-summary-display-message");
    if (details && resetSummaryButton) {
        resetSummaryButton.addEventListener("click", () => {
            details.open = true;
            updateDisplayStatus();
            try { window.localStorage.setItem(summaryStateKey, "true"); }
            catch (_) { /* Still expand the summary when storage is unavailable. */ }
            if (resetSummaryMessage) resetSummaryMessage.textContent =
                "Live Appearance Summary expanded. Appearance settings were not changed.";
        });
    }
    const refresh = refreshLiveAppearanceSummary;
    refresh();
    // Preferences change through selects, color picker controls, imports and resets.
    document.addEventListener("change", () => window.setTimeout(refresh, 0));
    document.addEventListener("input", () => window.setTimeout(refresh, 0));
    document.addEventListener("click", event => {
        if (event.target.closest("button")) window.setTimeout(refresh, 0);
    });
}
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeLiveAppearanceSummary);
} else {
    initializeLiveAppearanceSummary();
}
