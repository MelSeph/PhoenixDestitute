# PhoenixDestitute React UI

React port of `django/game/templates/game/prototype.html` and its appearance controls. The original template, scripts, Django endpoints, and `legacy_game/` are unchanged.

## Run locally

Install Node.js LTS (22.12 or newer; Node 24 LTS was used for validation) from [Node.js](https://nodejs.org/en/download). Python and the dependencies from `django/requirements.txt` are required for the backend.

Start Django in one terminal from the repository root:

```powershell
cd django
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Start React in a second terminal:

```powershell
cd react
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. Use that hostname consistently so browser cookies stay associated with the same host. The Vite development server proxies `/api/` and the CSRF initialization request `/prototype/` to Django on port 8000. It preserves the original Host header, allowing Django's normal Origin/CSRF checks to pass without CORS or security-setting changes.

If using the temporary Node runtime downloaded during development on this machine, add it to the current PowerShell session before running npm:

```powershell
$env:Path = (Join-Path $env:TEMP 'phoenix-react-node/node-v24.22.3-win-x64') + ';' + $env:Path
```

That temporary runtime is outside the repository and may be removed by Windows. Installing Node LTS is the durable setup.

## What was ported

- Responsive panels and the closed-by-default Options disclosure.
- Midnight, Daylight, High Contrast, and Custom themes; seven custom colors.
- Color dialog with HSL sliders, hex entry, presets, contrast validation, Escape/cancel, and keyboard focus management.
- Seven independent readability preferences, a narrative preview, and separate readability/color/all resets.
- JSON backup/export, validated import review with changed values, one-level import undo, clipboard/text summary, live summary, remembered summary disclosure, and customization count.
- Existing session-owned Character reads and explicit creation through Django. There are no client-side character rolls or fabricated backend records.

The active JavaScript theme palette is used instead of the prototype stylesheet's different pre-initialization colors. Repeated preview/help blocks are consolidated into a responsive settings grid and one narrative preview. The automatic contrast fallback uses High Contrast. Custom colors must meet the original text and control contrast thresholds before they are applied.

The version-1 `phoenixdestitute-appearance` JSON backup format and existing preference key names are retained. Browser localStorage is scoped by origin (including port), so export from the Django prototype and import into React to transfer preferences. Session cookies are not scoped by port; using the same hostname allows the existing local character session to continue. Appearance backups contain no game saves or session credentials.

Birth stat drafts, name/gender/appearance selection, final birth confirmation, inventory, training, and equipment screens are future integrations. The Character panel intentionally retains the prototype's existing local-character API; clicking Create does not confirm a newborn from a birth stat draft.

## Code guide

1. `src/main.jsx` mounts React into `index.html`.
2. `src/App.jsx` owns appearance state and renders settings. Changing state updates the UI rather than manually editing DOM nodes.
3. `src/appearance.js` contains palette validation, backup compatibility, persistence, and CSS-variable application. Appearance preferences stay in the browser.
4. `src/ColorPicker.jsx` and `src/Dialog.jsx` handle temporary color selection and accessible modal behavior.
5. `src/CharacterPanel.jsx` fetches Django data. Django owns character identity, session ownership, and writes.
6. `src/styles.css` retains the prototype's visual language with responsive controls and reduced-motion support.

## Verify

```powershell
npm test
npm run build
npm run test:browser
```

Browser tests use installed Microsoft Edge by default. For another environment, change `channel: 'msedge'` in `playwright.config.js` to an installed supported browser, or remove the channel and install Playwright Chromium with `npx playwright install chromium`.

Browser tests require ports 8000 and 5173 to be free. They start Django using `tests/django_server.py` with a freshly migrated temporary database, plus Vite. They do not use or modify `django/db.sqlite3`. The live integration check creates a disposable local character and verifies real CSRF/session behavior through the proxy; other browser scenarios mock API responses. Servers stop at the end of the test run. Screenshots and failure artifacts go in ignored `test-results/`.

Verified: 6 settings tests, 7 browser tests, production build, and all 254 existing Django tests. Node 24.22.3, React 19.3.1, Vite 7.3.8; exact dependencies are locked in `package-lock.json`.

`npm run build` outputs ignored `dist/` files. `npm run preview` serves a static build for inspection; it does not include the development proxy. Production hosting must serve the React build and forward `/api/` and `/prototype/` to Django on the same origin. Deployment is not configured in this port.
