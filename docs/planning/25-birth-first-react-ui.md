# Birth-first React UI — 2026-11-15

## Authorization and boundaries

The user requested “Have new UI use birth-first creation” after the prototype port was pushed at `bf07b35`. This authorizes connecting the opening React panel to the existing Phase 2O stat-draft API. The scope was stated before implementation: eight starting attributes, rerolls/locks, derived resource previews, persistence, and safe recovery. Name/gender/looks choices and final birth confirmation have no backend contract yet and remain explicitly unavailable. No birth storage/rules are invented in the browser.

The old React Character panel is replaced, including its Create local character action. The old Django API and prototype are unchanged for compatibility. No migrations, save conversions, birth confirmations, or `legacy_game/` edits. Existing characters/saves are preserved; preparing a draft in their session does not replace them. Commit/push and deployment remain separate.

## Step-by-step implementation

1. `App.jsx` renders `BirthCreationPanel.jsx` in the existing panel design. Read-only initial GET resumes a saved session draft. A missing draft offers **Roll starting attributes**; that explicit POST creates or resumes the server draft. Refresh does not roll or create anything.
2. The eight server-returned attributes are shown with labeled lock checkboxes. At three active locks, remaining unchecked controls are disabled; checked controls remain available to unlock. A lock action sends the entire intended selection and the last server revision. Checkboxes reflect saved state after acknowledgement, without pretending a failed write succeeded.
3. **Reroll unlocked attributes** sends only the last revision. Rolls, limits, and validation remain in Django; the UI has no RNG, point budget, or reroll counter/cost. A synchronous request guard and disabled controls prevent rapid double-clicks/overlapping actions.
4. Health/Mana/Stamina current/maximum previews are displayed directly from the response, with the agreed parent ×10 explanation. They cannot be independently locked or edited. Baseline Condition is labeled separately; no dynamic wellbeing formula or newborn attraction metric is introduced.
5. All POSTs retain CSRF protection, initializing its cookie through the existing proxied prototype page when necessary. A 409 is followed by a GET and a visible review message, without replaying the rejected write. Lost/failed responses disable mutations until a successful manual Reload draft; a possibly saved reroll is never automatically repeated. A missing/expired draft returns to explicit creation. Account/other errors show the server message instead of creating fallback data.
6. Drafts live only in Django's session-owned storage, not in React appearance backups/localStorage. No permanent Character ID is displayed for a draft. The UI clearly states that name, gender, looks, and final birth confirmation are not yet available.

## Verification

- `npm test`: all 6 existing settings tests pass.
- `npm run test:browser`: 14 browser tests pass. Covers appearance controls, explicit birth start and CSRF, server-driven values, lock limits/switching, unlimited rerolls and repeated-value responses, immediate duplicate-click protection, stale revision recovery, lost-response recovery, missing/expired/account errors, refresh persistence, and 375px mobile layout at 200% text.
- Two live integration cases run against the existing Django app with a migrated temporary database: birth creation/locks/reroll/reload and unchanged old-character session coexistence. The new UI makes no old Player API calls. The working database is untouched.
- `python manage.py test game`: all 254 Django tests pass, none skipped.
- `npm run build`: production build succeeds. No new dependencies or migration changes.
- Birth desktop/mobile screenshots captured in ignored test artifacts; desktop visually inspected.

The remaining creation work is to agree and implement identity/appearance choices and permanent birth confirmation before this draft can become a playable newborn. See [22-birth-first-character-creation.md](22-birth-first-character-creation.md) for open rules and [react/README.md](../../react/README.md) for run instructions.
