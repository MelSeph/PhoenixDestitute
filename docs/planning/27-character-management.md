# Phase 2Q — Local character loading and deletion

## Authorization and behavior

The user requested **“Add a way to load and delete characters”** after Phase 2P was pushed at `18d6c7f`. The implementation plan was stated before coding: session-owned character roster with Load/New character/Delete, typed-name deletion confirmation, and logical deletion that retains protected history. No user's character is deleted during development or tests against the working database.

Each list entry represents a saved story (Player and Legacy) and its current Character/active Playthrough. This avoids inventing separate save slots for historical lives. Loading selects the existing story; it neither creates another life nor invokes Regression. New character makes room for another independent story while keeping existing entries loadable. Accounts, cross-browser recovery, permanent purging, and restore/undo-delete are outside this milestone.

## Step-by-step implementation

1. **Store ownership on the server.** Migration 0018 creates `LocalCharacter`: opaque UUID, Session foreign key, protected one-to-one Player relationship, creation timestamp, and nullable deletion timestamp. A browser cannot submit its owner/session ID. New birth confirmation creates its roster row in the same transaction as the birth. Unique Player ownership prevents reassignment between sessions.
2. **Adopt existing local sessions safely.** Listing may register the anonymous Player already referenced by that valid session's trusted `active_player_id`. It does not scan/adopt unrelated database characters. An already-owned or deleted Player is never reassigned or revived. This lets the character created before migration 0018 appear when its existing browser session refreshes. Empty/expired anonymous GETs create no sessions or game entities.
3. **Load through the existing session.** Load verifies the UUID against nondeleted rows belonging to the current session, then transactionally changes `active_player_id`. Existing save/inventory/settings/thermal APIs consequently operate on the selected story. A confirmed birth is read directly from BirthRecord, without reconstructing its removed draft, rerolling, or changing history. Older lives without a birth profile show existing name/level/experience instead of fabricated newborn values.
4. **Keep one unfinished draft.** New character clears the current selection and removes only an obsolete confirmed draft; the permanent birth remains. If an unfinished draft exists, it is resumed unchanged. New does not automatically roll stats. Switching to saved characters preserves an unfinished draft until New character returns to it. The roster still permits multiple confirmed independent stories.
5. **Delete deliberately.** The dialog states that deletion removes play access while retaining history internally, offers Cancel/Escape, and requires the exact displayed name. The service rechecks ownership and name before setting `deleted_at`. Deleted entries disappear and cannot be loaded; repeat requests are idempotent. Deleting the selected character clears selection and any obsolete confirmed temporary draft while preserving an unfinished draft. Deleting an inactive entry leaves the selected story intact. Births, saves, items, enchantments, and historical references are retained; no protected foreign keys or lifecycle rules are weakened.
6. **Enforce deletion on older APIs too.** The shared `_session_player` guard rejects a deleted roster entry or one owned by another session, even if a stale active ID remains in a request/session. Existing player/save/inventory/settings/thermal handlers continue through this guard. Internal lifecycle functions remain backend-only; this milestone adds no death/progression controls.
7. **Coordinate React actions.** `CharacterManager.jsx` adds the list, IDs to distinguish matching names, Load/New/Delete, typed confirmation, and Reload characters. It coordinates pending writes and unsaved identity edits with BirthCreationPanel. Failed/uncertain actions require a read to recover rather than automatic retries. A loaded newborn stays read-only; its reload uses the selected-character endpoint. Loading/unloading and server session caches remain consistent with transactional writes.

## Endpoints

| Endpoint | Method/body | Behavior |
|---|---|---|
| `/api/characters/` | GET | Session-owned nondeleted list and current loaded view |
| `/api/characters/current/` | GET | Existing selected birth snapshot or older-character metadata; 404 if unavailable |
| `/api/characters/load/` | POST `{character_id}` | Select an owned saved story |
| `/api/characters/new/` | POST `{}` | Enter creation/resume unfinished draft; explicit action may initialize a session |
| `/api/characters/delete/` | POST `{character_id, confirmation_name}` | Logical deletion after exact-name validation |

Writes retain CSRF protection and exact JSON-field validation. Authenticated account management is unsupported (403). Missing/expired/foreign/deleted load targets return the same 404; invalid confirmation returns 409. GET cannot select an arbitrary owner. These APIs return an opaque roster UUID separately from the permanent Character ID shown in the UI.

## Data and limits

Migration 0018 adds only the roster table. Backup `django/db.phase2q-character-roster-backup.sqlite3` was verified with SQLite integrity_check; all pre-existing game rows were compared before/after and preserved. No local births or deletions were performed. Ownership adoption happens lazily when the existing session lists its characters, not through a global backfill.

Deleting is intentionally logical, not a permanent purge of protected records, and the UI explicitly explains that. No restore action is supplied. Session expiry/cookie loss still removes anonymous access; no account/cross-browser recovery is inferred. Session cleanup may remove ownership rows while permanent characters/history remain. Gameplay beyond birth, training/aging, and resource progression remain deferred. SQLite contention across multiple processes is not load-tested; mutation transactions and ownership/uniqueness constraints are verified.

## Verification

- **296 Django tests pass, none skipped** (275 existing + 21 roster tests). Covers ownership/adoption/isolation, multiple births, selected save data, direct birth loading without draft recreation, draft preservation, older characters, active/inactive deletion, idempotence, history retention, name validation, legacy guards, expiry/accounts/CSRF/method/body guards, and atomic rollback.
- **29 browser tests pass** across the existing 21 cases and 8 character-management cases: two-character switching/reload, cancellation and typed deletion, inactive deletion, unfinished-draft resumption, foreign-session access rejection, lost-response recovery, mobile 200% text/keyboard behavior, and older-character loading.
- All 6 settings tests and the production build pass. Django check: no issues; migration drift check: no changes.
- Test actions use only migrated temporary databases. The working database's existing characters/saves were preserved. Character-list screenshot captured for visual inspection. No original Django prototype/static or `legacy_game/` edits. No commit/push or deployment performed.
