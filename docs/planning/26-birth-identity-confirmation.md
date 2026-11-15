# Phase 2P — Birth identity, visual choices, and confirmation

## User request

The user requested adding name, gender, looks, and final confirmation to the birth-first React UI. The preceding stat-draft UI was pushed at `2f802d3`.

When asked about free-text identity/cosmetics, the user chose **“Define preset choices first”**. After reviewing the proposed presets, the user approved them with **“Yes. make sure every color option has an appropriate color visual and hair length has a hair length visual on the choice.”** This authorizes the identity, appearance, and confirmation implementation, including visuals. No commit/push or deployment is authorized.

## Implemented choices

- Name: player-entered text, up to the existing 100-character name limit.
- Gender: Male, Female, Nonbinary, Custom.
- Skin tone: Very fair, Fair, Light brown, Medium brown, Dark brown, Very dark.
- Eye color: Brown, Hazel, Green, Blue, Gray, Amber.
- Hair color: Black, Dark brown, Light brown, Blond, Red, White.
- Hair length: Bald, Short, Medium, Long, each with a silhouette illustration.
- Hair texture: Straight, Wavy, Curly, Coily, chosen separately from length.

To make the requested length visuals clear, the assistant stated the low-risk implementation assumption of separate Bald/Short/Medium/Long length choices and straight/wavy/curly/coily texture choices before coding. Illustrations are length guides and explicitly do not preview texture. They adopt the selected skin and hair colors; labels and native radio selection remain visible independently of color. Every skin and hair color has a swatch; every eye color has a colored iris illustration. The same visuals appear in review and confirmed summaries. These are code-native SVG/CSS assets, with no external images or image-generation dependency.

Choosing Bald clears and hides hair color and texture, and Django rejects irrelevant choices rather than silently preserving them. Custom gender reveals a player-written label (40 characters maximum); other gender presets require an empty custom label. Names use the existing 100-character limit. Choices are cosmetic and grant no stat bonuses; no pronouns, sex-based rules, attraction scores, or wellbeing formula are inferred.

## Implementation, step by step

1. **Django owns the catalog.** `birth_identity.py` defines preset IDs, labels, representative hex colors, exact identity fields, partial/complete validation, and the existing full ×10 birth-resource calculation. Draft responses include this catalog; React does not maintain a separate set of allowed choices. No color choice is a numeric gameplay modifier.
2. **Extend existing drafts additively.** Migration 0017 adds a default-empty identity JSON field. Existing rolls, locks, revisions, and ownership are retained. Partial identity edits can be explicitly saved, but only complete valid identities can be confirmed. Server trimming, length/type/control-character validation, preset membership, and dependent-field rules apply. Saving identical normalized choices is a no-op; changed choices rotate the shared draft revision without rolling stats.
3. **Save before reviewing.** React keeps edits in memory until **Save identity and looks**. Unsaved edits disable reroll/lock/review actions, preventing accidental loss or confirmation of different values. Reload asks before discarding unsaved edits. The review dialog displays saved identity/visuals, all eight stats, and full Health/Mana/Stamina previews; Cancel/Escape leaves the draft unchanged.
4. **Confirm atomically.** `confirm_birth` locks the session/draft, checks the reviewed revision and complete identity, creates Player/Legacy/Character/initial Playthrough through the existing foundation, then stores a `BirthRecord`. Session activation is encoded/saved in the same database transaction. Any record/activation failure rolls back the entire birth. The API synchronizes its session cache with this committed state.
5. **Keep a permanent birth snapshot.** `BirthRecord` has a protected one-to-one Playthrough relationship, unique source draft UUID, source revision, copied identity, eight birth stats, copied full initial resource values, and confirmation timestamp. It has no cascading Session/draft foreign key, so session cleanup does not erase the born character or snapshot. JSON is used here as an immutable-by-service snapshot, following the project's historical snapshot pattern; it is not a new mutable progression-stat system.
6. **Freeze and resume.** Confirmed reads return the birth snapshot and Character/Playthrough IDs. Identity edits, locks, and rerolls reject after confirmation. Retrying confirmation with the same reviewed revision returns the identical birth (200) rather than creating another (201 initially). A lost confirmation response is recovered with GET, never an automatic duplicate POST. The UI displays the named newborn, permanent Character ID, confirmed appearance, and starting values.

## API changes

- Existing draft GET/create/lock/reroll responses additionally contain `identity`, `identity_options`, `identity_complete`, `confirmation_blocked_reason`, and nullable `birth`. Existing fields retain their meanings.
- `POST /api/creation/stats/identity/`: exactly `revision` and `identity`; saves complete field selections, including empty partial values. Returns the revised draft.
- `POST /api/creation/stats/confirm/`: exactly `revision`; copies only server-owned saved choices and stats. Returns 201 for a new birth, 200 for an identical retry.
- Existing ownership/account/CSRF protections remain. Unsupported accounts return 403; missing/expired drafts 404; malformed/unexpected fields 400; invalid/incomplete/stale/frozen/conflicting state 409. No public owner/draft selector is accepted.

## Compatibility and limits

Confirmation refuses to replace an existing local character in the session; its active identity and saves remain unchanged. React explains the conflict and disables Review birth. A separate browser profile/private window can start a separate story; a destructive reset or old-character conversion is not provided. Draft preparation remains compatible with old sessions.

Migration 0017 adds only the draft identity field and BirthRecord table; it backfills no births or identity values onto old characters. Backup: `django/db.phase2p-birth-backup.sqlite3`, verified with SQLite integrity_check. The local migration is applied. All pre-existing game-table values (including existing draft rolls/locks) were compared before/after and preserved; no local test birth was created.

Appearance/history evolution, age progression, training, dynamic Condition, resource spending/recovery, and Regression/New Life birth rules remain future systems. The permanent snapshot records birth/age-zero values and does not pretend to implement those progression rules. Anonymous session expiry still loses browser access unless a future recovery/account feature is added; the birth itself is retained. Direct ORM edits bypass service immutability, as with earlier snapshots. SQLite contention is not load-tested; transactions and source/playthrough uniqueness prevent duplicate committed birth records.

## Verification

- 21 new Django tests; **275 total Django tests pass, none skipped**. Covers preset/identity validation, no-op edits, partial saves, custom/bald dependencies, stale revisions, atomic rollback including session activation, idempotent/lost-response recovery, post-confirmation freeze, permanent retention after cleanup, existing-save protection, ownership/expiry/CSRF/account/method/body guards, and birth snapshot consistency.
- **21 browser tests pass**, including seven new live Django scenarios for all color/length visuals, saved choices, review/cancel, confirmation/retry/refresh, bald/custom gender, stale review, lost response, existing-character conflict, and mobile 200% text/keyboard access. Browser integration uses a migrated temporary database.
- All 6 appearance settings tests pass; production build succeeds. Django check has no issues; migration drift check has no changes.
- Desktop visual-choice and mobile-review screenshots inspected. No `legacy_game/` or original Django prototype/static frontend edits. No commit or push.
