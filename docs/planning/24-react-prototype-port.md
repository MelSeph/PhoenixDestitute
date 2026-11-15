# React prototype port — 2026-11-15

## Authorization and scope

After Phase 2O was committed/pushed at `e7a31b7`, the user requested: “create the new UI from what I was working on in the django/game/templates/prototype.html, just recode it for react and put that in the react folder.” The actual source is `django/game/templates/game/prototype.html`, with `appearance.js`, `color-picker.js`, `player-api.js`, and `prototype.css` under Django static files.

This explicitly supersedes the earlier no-React-work boundary for this UI port. The existing prototype and Django code remain intact; `legacy_game/` remains read-only. No new backend rules, birth confirmation, inventory/equipment UI, deployment, commit, or push are included.

## Implementation, step by step

1. Added a standalone React/Vite app in `react/`, with a locked npm dependency tree and development/build/test commands. Node was absent from PATH; a portable Node 24 LTS runtime was downloaded to the system temporary directory for validation. No machine-wide installation or PATH change was made.
2. Converted prototype behavior to React state/components rather than mounting the original DOM-mutating scripts. Retained the panel design, default-closed Options disclosure, theme palettes, seven custom colors, HSL/hex/preset picker, and seven independent readability settings. Repeated preview/help blocks are consolidated into a responsive control grid and one narrative preview.
3. Retained contrast thresholds, readable button labels, separate color/readability/all resets, JSON backups, import validation/review, changed-value labels, one-level import undo, clipboard/text summaries, live summary/disclosure persistence, and the 14-preference customization count. Native modal dialogs also restore focus, handle Escape, and wrap Tab navigation.
4. Kept the version-1 appearance backup format and existing preference keys. The prototype CSS's initial palette differs from its active JavaScript palette; this was raised in commentary, and the active JavaScript palette was used as the source of truth. Browser storage remains origin-specific, so transfer preferences between Django and Vite using JSON export/import. No game-save data is accessed by appearance storage.
5. Kept the prototype's real Character API. React reads `/api/player/`; explicit Create initializes the existing CSRF cookie via `/prototype/`, then posts to `/api/player/create/`. No automatic character creation, local stat rolling, or new birth rules are introduced. The old Create action is still the compatibility flow, not newborn confirmation.
6. Configured Vite on `127.0.0.1:5173` to proxy API and CSRF bootstrap requests to Django on port 8000. An actual integration test caught the string-form proxy changing Host and causing a CSRF Origin rejection. Explicit `changeOrigin: false` fixes this while preserving Django's CSRF protection and avoiding backend/CORS changes.

## Verification

- `npm test`: 6 passing settings tests, including prototype backup compatibility, palette validation, malformed imports, persistence rollback, and unavailable/corrupt storage.
- `npm run test:browser`: 7 passing Edge browser checks, including desktop/mobile UI, 200% text without page overflow, modal keyboard navigation, state persistence, independent resets, import review/cancel/confirm/undo, downloads, API errors, and real Django session/CSRF creation/reload.
- Integration tests start the existing Django application with a newly migrated temporary database. The working SQLite database is not used or modified.
- `npm run build`: production output generated successfully in ignored `react/dist/`.
- `python manage.py test game`: all 254 existing Django tests pass, none skipped.
- Desktop/mobile screenshots generated under ignored `react/test-results/`; desktop visually inspected.

Run instructions and a component guide are in [react/README.md](../../react/README.md). Production proxy/hosting configuration is deliberately deferred; Vite's static preview does not supply the development API proxy. This is a local repository implementation, using the Sites skill's local-only workflow, with no hosting registration or publication.
