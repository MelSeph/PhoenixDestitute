# PhoenixDestitute React UI

React UI based on `django/game/templates/game/prototype.html`, with birth-first stat selection and its appearance controls. The original template, scripts, Django endpoints, and `legacy_game/` are unchanged.

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

The game cookie persists across normal browser restarts (Django's 14-day lifetime). Admin uses a separate cookie so admin login/logout cannot rotate or delete game ownership. After upgrading, admin may require signing in again. Keep using the same browser profile/hostname; clearing or expiring cookies still loses anonymous access. An old shared staff login is separated automatically while preserving only its proven game selection. No unrelated database characters are exposed for recovery.

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
- Session-owned birth stat drafts through Django: eight base attributes, unlimited explicit rerolls, up to three freely switchable locks, and server-provided full Health/Mana/Stamina previews. Loading or refreshing reads the saved draft; first-time rolling requires an explicit click.
- Name and gender selection; skin/eye/hair presets with labeled color visuals, and illustrated Bald/Short/Medium/Long hair-length choices. Texture is selected separately. The catalog and color values come from Django.
- Explicit identity save, complete birth review, final confirmation, and a permanent newborn summary with the Character ID. Gender/looks grant no stat bonuses.
- A **Your characters** list with Load, New character, and typed-name Delete. Multiple saved stories remain selectable in the same browser session; unfinished drafts are preserved while switching.

The active JavaScript theme palette is used instead of the prototype stylesheet's different pre-initialization colors. Repeated preview/help blocks are consolidated into a responsive settings grid and one narrative preview. The automatic contrast fallback uses High Contrast. Custom colors must meet the original text and control contrast thresholds before they are applied.

The version-1 `phoenixdestitute-appearance` JSON backup format and existing preference key names are retained. Browser localStorage is scoped by origin (including port), so export from the Django prototype and import into React to transfer preferences. Session cookies are not scoped by port; using the same hostname retains session ownership. Appearance backups contain no game saves, birth drafts, or session credentials.

The opening panel uses `/api/creation/stats/`, `/api/creation/stats/locks/`, `/api/creation/stats/reroll/`, `/api/creation/stats/identity/`, and `/api/creation/stats/confirm/`. It never calls the old local-character creation endpoint. Only final confirmation creates a permanent Player/Character/initial life through Django. Existing characters/saves remain intact; use **New character** to leave the current selection and start a separate story without replacing it. If an unfinished draft exists, New character resumes it rather than discarding its rolls or identity.

**Load** selects that saved story for the existing backend APIs and resumes its confirmed birth snapshot without rolling or recreating the draft. Selection survives refresh. Older saved characters display their existing name/level/experience; the UI does not invent birth stats. Entries are scoped to the server-owned session, and Character IDs distinguish identical names.

**Delete** opens a dialog requiring the exact character name. Cancellation leaves it intact. Confirmation permanently purges the selected story's Player, Legacy, playable characters, all lives, birth records, saves, owned items/enchantments/equipment reservations, death history, settings, and roster entry. Other stories, accounts, shared equipment definitions, and unrelated unfinished drafts are preserved. There is no retained tombstone or restore action. Cross-story protected references cause an atomic rejection instead of deleting another story. Deleting the current character returns to creation; deleting another leaves the current story selected. Failed/uncertain requests require Reload characters instead of automatic retries. A repeated delete returns 404 because its record no longer exists. This action creates no recovery copy and does not alter existing external database backups. Anonymous access still depends on retaining the session cookie; account recovery is not implemented.

To create a character: roll starting attributes, choose a name/gender/looks, select **Save identity and looks**, adjust your rolls/locks if desired, then **Review birth** and **Confirm birth**. Unsaved identity edits must be saved before rolling/reviewing; Reload asks before discarding them. Review shows all saved appearance choices and server-rolled stats before anything becomes permanent. Bald clears and hides hair color/texture. Custom gender reveals a label field.

After confirmation, creation edits/rerolls are frozen and refresh resumes the same named newborn. Confirmation retries return the same birth rather than creating another. The permanent birth snapshot survives draft/session cleanup, but anonymous browser access still depends on retaining the session cookie; account recovery is not implemented. Stats/resources shown are the birth snapshot, not an implemented training/progression state. All rolls and resource previews come from Django: Health = Strength ×10, Mana = Intelligence ×10, and Stamina = Endurance ×10, starting full.

Inventory, equipment screens, training, age progression, dynamic wellbeing/Condition, and later-life birth rules remain future integrations. The newborn summary states that training/aging are unavailable. No attraction metric is implemented.

Only one draft request can run at a time. Changed-lock/reroll writes send the last server revision. A 409 triggers a safe GET to refresh the draft without replaying the rejected action. A lost/failed write response disables mutations until Reload draft succeeds, preventing an automatic duplicate roll. A 404 returns to explicit creation; other load failures do not create a replacement draft. Lock checkboxes display their saved state after the server acknowledges the change.

## Code guide

1. `src/main.jsx` mounts React into `index.html`.
2. `src/App.jsx` owns appearance state and renders settings. Changing state updates the UI rather than manually editing DOM nodes.
3. `src/appearance.js` contains palette validation, backup compatibility, persistence, and CSS-variable application. Appearance preferences stay in the browser.
4. `src/ColorPicker.jsx` and `src/Dialog.jsx` handle temporary color selection and accessible modal behavior.
5. `src/BirthCreationPanel.jsx` reads/updates the session-owned draft and coordinates final review/confirmation. `src/BirthAppearance.jsx` renders the identity form, swatches/iris visuals, SVG length illustrations, and saved appearance summaries. Django owns presets, validation, rolls, resources, revisions, and permanent confirmation. Birth data never enters appearance backups/localStorage.
6. `src/styles.css` retains the prototype's visual language with responsive controls and reduced-motion support.
7. `src/CharacterManager.jsx` coordinates player account access, the saved-character list, selection, new creation, deletion, and unsaved-edit/pending-request guards. `/api/account/` handles account state/actions; `/api/characters/` and its `current/`, `load/`, `new/`, `delete/`, and `recover/` routes enforce ownership in Django.

### Recovering an orphaned character

In Django admin, open **Players**, select exactly one unrostered player, choose **Issue one-use recovery code for one orphaned character**, and click **Go**. A superuser must perform this action. Copy the code from the one-time admin message. In the target browser, open **Recover a saved character** in the character list and submit it. If signed in, the recovered character is attached to the account; otherwise it belongs to that browser. The code expires after 24 hours; issuing another code for that player invalidates earlier unused codes. The raw code is not stored in the database.

### Player accounts

Use **Player account** above the character list to create a username/password account or sign in. Registration/sign-in moves characters and an unfinished creation draft owned by that browser to the account before Django rotates its session key. Other signed-in browsers can then see the same account roster, load a character, and continue its server-side saves. Each browser's active character selection remains independent. Sign out keeps account-owned characters and drafts on the account. Password reset/email verification are not configured yet.

## Verify

```powershell
npm test
npm run build
npm run test:browser
```

Browser tests use installed Microsoft Edge by default. For another environment, change `channel: 'msedge'` in `playwright.config.js` to an installed supported browser, or remove the channel and install Playwright Chromium with `npx playwright install chromium`.

Browser tests require ports 8000 and 5173 to be free. They start Django using `tests/django_server.py` with a freshly migrated temporary database, plus Vite. They do not use or modify `django/db.sqlite3`. Live integration checks cover birth drafts/identity/visuals, locks/rerolls/resources, final review/confirmation, retries/lost responses, real CSRF/session behavior, and protection of older characters. Other scenarios mock API responses. Servers stop at the end of the test run. Screenshots and failure artifacts go in ignored `test-results/`.

Verified: 6 settings tests, 32 browser tests, production build, and all 322 Django tests. Node 24.22.3, React 19.3.1, Vite 7.3.8; exact dependencies are locked in `package-lock.json`.

`npm run build` outputs ignored `dist/` files. `npm run preview` serves a static build for inspection; it does not include the development proxy. Production hosting must serve the React build and forward `/api/` and `/prototype/` to Django on the same origin. Deployment is not configured in this port.
