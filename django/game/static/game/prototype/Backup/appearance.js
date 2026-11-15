
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
        accent: "#e5c78e"
    },

    daylight: {
        background: "#f1f4f8",
        panel: "#ffffff",
        border: "#64748b",
        text: "#182536",
        muted: "#45546a",
        accent: "#234f85"
    },

    highContrast: {
        background: "#000000",
        panel: "#000000",
        border: "#ffffff",
        text: "#ffffff",
        muted: "#ffffff",
        accent: "#ffff00"
    },

    custom: {
        background: "#111820",
        panel: "#202d3a",
        border: "#718298",
        text: "#f1f5f9",
        muted: "#c0ccd9",
        accent: "#e5c78e"
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
    accent: "#ffff00"
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

    return allPassed;
}

function saveCustomAppearanceColors() {
    const customColors = {
        panel: appearanceThemes.custom.panel,
        text: appearanceThemes.custom.text,
        muted: appearanceThemes.custom.muted,
        accent: appearanceThemes.custom.accent,
        border: appearanceThemes.custom.border,
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
            parsedColors.background !== undefined && 
            (
                typeof parsedColors.background !== "string" ||
                !validHexColor.test(parsedColors.background)
            )
        ) {
            console.warn("Invalid saved page background color.");
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
    const backgroundColorInput = document.getElementById("custom-background-color");
    const message = document.getElementById("custom-color-message");

    if (!themeSelector || !customSettings || !panelColorInput || !textColorInput || !mutedColorInput || !accentColorInput || !borderColorInput || !backgroundColorInput || !message) {
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
            backgroundColorInput.value = appearanceThemes.custom.background;
        }
    }

    themeSelector.addEventListener(
        "change",
        updateCustomSettingsVisibility
    );

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
