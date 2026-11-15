# Phase 2H — Backend inventory operations

## Direction and authorization

After Phase 2G, the user clarified that the backend should win over inconsistencies in the legacy browser game. The proposed legacy shop/crafting repair milestone was withdrawn. The user supplied the Django frontend prototype and a future React preference as context, explicitly rejecting a frontend scope change. The subsequent “proceed” authorizes the backend inventory-operations work. No frontend migration or legacy repair is included; commit/push requires separate approval.

Equipment commands remain pending clarification: no approved backend body-slot catalog or equipment-stat calculation exists. The user has been asked whether to defer equip/unequip or define those rules first. No default answer has been assumed.

## Implemented first increment

1. `GET /api/inventory/` reads **all relational items** belonging to the session player's active life. This includes NULL-token backend records that the Phase 2G browser bridge deliberately leaves unmanaged. An empty inventory is valid even if the life has no JSON save. Reads neither import legacy JSON nor create saves.
2. `POST /api/inventory/move/` accepts exactly `playthrough_id`, `revision`, `item_id`, `location`, and `slot`. It moves an existing item or whole stack between carried slots and abstract storage. It cannot create items, edit quantities/properties, split/merge stacks, or equip/unequip. Storage has no containers or travel/access rules in the current model; this is abstract placement, not a complete world-storage mechanic.
3. Django verifies active-life ownership, the expected life and inventory revision, an available nonnegative carried slot, or a NULL slot for storage. It rejects equipped source items and destinations. Existing database constraints remain; no new slot capacity or stack limit is invented.
4. A transaction locks the Player using the same coordination convention as save/lifecycle services. Only `location` and `slot` change on the original item row. Its ID, client token, properties, quantity, and life stay intact. Exact no-op commands return the same state; retries after a successful change require reloading the revision.
5. The inventory revision hashes the life, ordered relational item data, and current saved timestamp. It detects placement/property changes and save writes without adding a schema field. This revision is distinct from the Phase 2G browser-save revision.
6. If a versioned browser save exists, movement refreshes its managed item payload and rotates its browser revision, writing both `PlaythroughSave` and `GameSave` atomically. An old browser snapshot cannot undo the command. Unconverted legacy JSON is left untouched; an unsaved life remains unsaved. Historical saves are never written.

## API and boundaries

- Both endpoints reuse session-only local-player ownership. Missing local session returns 404; account save access remains unsupported (403). CSRF protection and method restrictions remain active.
- Malformed JSON and unexpected/missing command fields return 400. Ownership/life/revision/placement conflicts return 409 with an explanation. Successful responses contain `success` and the complete updated `inventory`.
- Death snapshots remain immutable. As in Phase 2F, movement after capture makes changed carried state fail the existing Regression validation; this increment does not define a death freeze/resurrection resolution policy.
- The Phase 2G full-payload save API remains a compatibility interface that accepts browser-provided inventory. This increment provides narrow validated commands for a future backend-driven frontend; it does not yet retire that compatibility API or make every acquisition/stat change backend-authoritative.
- SQLite does not provide PostgreSQL-style row locking. Constraints, transactions, and revision checks are covered here; concurrent multi-process load testing remains outside this increment.
- No templates, frontend scripts, `legacy_game/`, models, migrations, or production item data are modified.

## Verification

Fourteen new service/API tests cover reads without saves, full-stack movement, identity/properties, collisions, invalid placements, equipped-item rejection, stale requests, other owners/historical lives, JSON compatibility, rollback, unchanged death history, HTTP methods, and CSRF. Run `python manage.py test game`, `python manage.py check`, and `python manage.py makemigrations --check --dry-run` from `django/`.

Local results: all **90 Django tests passed**, with none skipped, including the existing headless Chromium checks. System checks passed, no pending model changes were detected, and `git diff --check` passed. No commit or push performed.

## Equipment questions still open

Equip/unequip requires approved body-position definitions, item eligibility (including multiple occupied positions), conflict handling, the authoritative source of base stats and bonuses, and treatment of current health/resources when maximum values change. Legacy names and stat code will not silently become the new rules.
