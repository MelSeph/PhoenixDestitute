# Phase 2G — Browser inventory integration

Approved 2026-11-15: user said “make it so” after reviewing the versioned bridge proposal and compatibility risks. Do not commit or push without separate approval. `legacy_game/` remains read-only.

## What the source actually represents

- Django-hosted `equipment.js` defines shared catalog objects, `equipArray`, and `equippedItems`. Starting gear and shop purchases push catalog references into this array. Mage staves can occupy both hands as one item.
- `playerInfo` holds the worn equipment names by body position. The array name alone does not establish placement: potions are also pushed into it, but combat decrements `playerStats.num*Potions` without removing those references.
- The pre-2G browser snapshot saves equipment names, stats, materials, gathering counters, and buildings. It does not serialize equipment-instance properties. Properties omitted by those old saves cannot be recovered.
- Crafting uses separate `creationStats` and `itemCreated` state; there is no complete generic carried-slot or world-storage UI. Do not infer carried gear from ambiguous leftover array entries or automatically convert material counters.
- Phase 2F snapshots only relational carried slots. Regression moves those original rows, leaving worn and world-stored items behind. It is still a backend-only operation.

## Step-by-step Django explanation

1. **Add a column, preserve existing rows.** Migration `0008_browser_inventory_identity` adds nullable, unique `InventoryItem.client_token`. The database primary key remains the item identity. The browser supplies a UUID before its first save, so a lost HTTP response does not require inventing another identity. NULL marks pre-existing backend-only records that this bridge must leave alone.
2. **Read the current life through the session.** Existing session/CSRF boundaries remain. Load responses add the playthrough ID and saved timestamp. An unsaved-life 404 includes its current ID; no predecessor JSON is returned. Fresh browser state must load an existing save before overwriting it.
3. **Convert deliberately on save.** Loading an old save changes browser memory only. Equipment names resolve through an immutable-key catalog map and original default property copies. Actual body positions determine worn gear, including two-handed items. Potion counters determine carried quantities. Ambiguous, duplicated, or missing equipment and unknown names refuse conversion without changing the saved data. First conversion includes the original save timestamp to detect another tab's changes.
4. **Keep the full instance payload.** Version 1 entries include `id`, `token`, `definition_key`, `kind`, `quantity`, `location`, `slot`, and `properties`. The latter preserves nested custom fields, upgrade values, durability, and the list of occupied equipment positions. Two equipment instances may share a definition without sharing identity. The browser supports one catalog-backed worn instance per definition; additional explicit carried/stored instances are retained separately with their own properties.
5. **Reconcile inside one transaction.** `save_active_playthrough` locks the Player, identifies the active life, and calls `browser_inventory.reconcile`. It validates the entire request before writing. Existing tokens update their original rows; new tokens create rows; omitted managed entries are removed only when no death history protects them. Managed carried slots are cleared transactionally before reassignment so swaps do not violate the unique-slot constraint. Unmanaged items and occupied slots remain protected.
6. **Save the two JSON records together.** The canonical inventory, including database IDs and a new revision token, goes into both `PlaythroughSave` and the compatibility `GameSave`. A validation failure rolls the whole operation back. Repeated successful saves reuse rows. A retry with an obsolete revision returns 409 and asks for reload; it does not duplicate items. Converted saves reject name-only writes from older clients. Old-format saves remain supported until conversion.
7. **Restore without applying bonuses again.** Active loads overlay current relational managed items on the JSON payload without writing the stored snapshot. The browser validates inventory, materials, counters, and buildings before applying changes. It keeps existing array/catalog references needed by legacy comparisons, replaces item properties, restores saved stats directly, and derives potion counters from carried relational stacks. Acquisition hooks assign a fresh token when the legacy array receives new equipment. Unknown top-level saved fields survive the next save.

## Compatibility limits

- Materials, crafting progress, ammunition counters, and world simulation are not newly normalized. Existing saved counters remain in JSON. No new inventory UI, combat death hook, or public life-transition endpoint is introduced.
- Explicit carried/stored entries round-trip, but there is no new browser UI for moving equipment between these locations. Unknown carried consumables are retained as explicit records rather than discarded as legacy potions.
- Missing old instance properties cannot be reconstructed from names. Legacy conversion uses original catalog defaults, never mutated properties from a previously loaded instance.
- Existing legacy shop/crafting array-management bugs are not repaired here. If they produce contradictory equipment data, the bridge refuses to guess. The notification explains the problem and preserves the saved game.
- Snapshot-linked rows cannot be deleted. Consuming the last unit or removing such a row returns a conflict; disposal/retirement semantics and a complete death/resurrection browser flow remain future work. Other post-death changes continue to make Phase 2F's stale-snapshot validation reject Regression.
- A newly regressed life still has no JSON save. Its transferred managed rows cannot be erased by an empty initial bridge save. Restoring the new life's full gameplay state remains a prerequisite for a future transition UI.
- Revisions protect participating save callers. Direct ORM writes bypass the service contract. SQLite does not provide PostgreSQL-style row locks; database constraints and transactions remain the local persistence safeguards, and multi-process contention behavior has not been load-tested.
- Browser identity generation requires `crypto.randomUUID()` in a secure context (localhost is suitable for local Django development).

## Validation and local database

- Original baseline re-run before new tests: 60 Django tests passed.
- Final full suite: **76 tests passed, none skipped**, including all original tests and the 17 browser checks. System checks passed, no pending model changes detected, and migrations 0001–0008 are applied.
- New coverage: 15 Django service/API tests and one real Chromium test executing 17 browser checks. This exercises repeated save/load, custom properties, duplicate rejection, distinct same-definition instances, slot swaps, rollback, old-format compatibility, stale first conversion, cross-life/foreign identities, snapshot protection, and Regression.
- JavaScript tests use installed Edge/Chrome in headless mode without npm dependencies. On other systems set `BROWSER_BINARY` to a Chromium executable. Missing browsers produce an explicit skipped test. Restricted Windows sandboxes may require permission to launch Chromium subprocesses; do not disable its sandbox as a workaround.
- SQLite backup created before migration: `django/db.phase2g-backup.sqlite3`. Migration 0008 applied locally; no inventory data conversion was performed on the working database.
- Run from `django/`: `python manage.py test game`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py showmigrations game`.
