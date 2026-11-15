# Planning validation — honest status

| Check | Status | Evidence or missing work |
|---|---|---|
| Approved handbook structure | **Passed** | 12 requested numbered `.md` documents created. |
| Original legacy-game file inventory | **First-pass complete** | 30 legacy source/assets/changelog files inventoried against ZIP entries; detailed per-variable reads/writes not yet exhaustive. |
| Script loading comparison | **Checked** | 22 `<script src>` references identified in `legacy_game/index.html`; `updatepotions.js` not directly referenced. |
| Every ZIP file accounted for | **Listed by category; partial review** | Legacy files plus existing Django project files and caches; empty React folder noted. Django code not line-by-line analyzed. |
| Every app/model has exactly one owner | **Not attempted** | No models or app boundaries approved. |
| No circular app dependencies | **Not attempted** | No dependency graph approved. |
| Every claim backed by source | **In progress** | Inventory names source files; detailed statement-by-statement provenance still needs work. |
| Full start-to-finish gameplay trace | **Not passed** | Partial flow documented only; branching remains. |
| Original game files left untouched | **Passed for produced artifact** | Files were read from ZIP; output contains only approved `CLAUDE.md` copy and planning Markdown documents. |

Do not convert a partial check into a passed check without doing the work.

## Django snapshot audit — 2026-11-15

**Scope:** examined Django entries from the user's `PhoenixDestitute.zip`. This is a static archive inspection, **not** a test of the user's current working directory or a Django runtime test.

| Finding | Direct evidence in archived path | Interpretation |
|---|---|---|
| Django project scaffold exists | `django/manage.py`; `django/phoenixdestitute/{settings,urls,asgi,wsgi}.py` | Some reusable configuration, not a verified functional backend |
| SQLite configured | `django/phoenixdestitute/settings.py`: `DATABASES` uses `django.db.backends.sqlite3` | Starting database engine is defined |
| `game` app referenced | `settings.py`: `INSTALLED_APPS` includes `game` | Expects a separate Django application |
| Views imported and routes declared | `django/phoenixdestitute/urls.py`: `from game import views`; home, prototype, player detail and player create routes | HTTP route intentions exist; behavior not verified |
| No `django/game/` files included | Complete ZIP entry listing checked; 13 regular files under `django/`, none inside `django/game/` | The archived snapshot lacks the application required by its settings and routes |
| No game models, migrations, or SQLite DB included | Complete ZIP entry listing checked | Cannot infer a functioning current database or evaluate actual saved data from archive |
| README appears to describe files absent from archive | `django/README.md` mentions `game/models.py`, `game/views.py`, template and legacy static snapshot | Documentation and supplied snapshot do not match |
| Dependency declaration exists | `django/requirements.txt`: `Django>=5.2,<6.0` | Django was contemplated in this archive, not yet an approved stack decision |

**Result:** the Django snapshot is **incomplete as supplied**. It is **not established** that the user's live local project is incomplete. No runtime checks, migration checks, or app tests were run; do not mark them passed.

**Suggested next evidence:** current local `django/` folder snapshot (without `.venv/`, `__pycache__/`, or secrets) and, separately if appropriate, the current model/migration files. Do not delete or replace existing work in order to obtain this evidence.

## Phase 2C validation checklist — 2026-11-15

- Django model schema unchanged; `makemigrations --check --dry-run` should report no changes.
- New backend transition tests cover resurrection, regression, New Life with same character or new successor, predecessor chains, unprovisioned players, invalid outcomes, active-life constraints, and preservation of Player/GameSave.
- In the user's local Django environment run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py test game`.
- No death endpoint, game frontend transition, equipment transfer, character stat reset, or per-playthrough save migration is implemented.
- **Runtime verification is pending** until the local Django test output is received. The earlier baseline was 16 passing tests; this phase adds 11 tests (expect 27).


## Phase 2D validation — 2026-11-15

- Additive migration `0006_playthroughsave` creates life-scoped save rows and copies each existing `GameSave` JSON into the corresponding **initial** life, without deleting or modifying legacy rows. Back up `django/db.sqlite3` before applying.
- Service tests cover current-life saves, compatibility mirroring, repeated updates, empty new life, non-overwriting historical saves, resurrection continuity, cross-Legacy access denial, invalid payloads, and unprovisioned players.
- Source inspection found no deployed save/load API routes in `django/phoenixdestitute/urls.py`; no frontend or public save API is changed here.
- This packaged copy has syntax and ZIP checks only. **Django runtime check, migration, and tests must run on the user's installed environment**; expected test discovery 37 (27 previous + 10 new).
- Run from `PhoenixDestitute/django`: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate`, `python manage.py test game`, `python manage.py showmigrations game`.

## Phase 2E validation — 2026-11-15

- Add session-scoped active save/load routes and ten API tests covering CSRF, malformed JSON, no session, separate sessions, historical save preservation, and no predecessor fallback.
- Update only the Django-hosted legacy JavaScript and homepage CSRF-cookie provisioning; original `legacy_game/` remains read-only.
- No schema change/migration; `makemigrations --check --dry-run` must report none.
- Runtime tests **pending on user's Django environment**. Expected discovery: 47 tests (previous 37 + 10 new).
- API cannot restore ownership of anonymous saves after browser session loss; no account authorization is implemented.


## Phase 2F — backend-only inventory and death snapshots

- Add migration `0007_inventory_death_snapshots` (three models + inventory integrity constraints). Back up `django/db.sqlite3` before migration.
- Snapshot only carried inventory slots; equipped and world-stored possessions remain with the old life.
- Regression moves existing item instance IDs to the new life; original snapshot retains copied quantity/properties.
- Abort on stale snapshots, replayed snapshots and cross-Legacy access. No frontend/combat hooks.
- No conversion of saved JSON to relational inventory: live gameplay still uses its existing save format.
- Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate`, `python manage.py test game`, `python manage.py showmigrations game`. Previous baseline 47; 13 tests added (expect 60).
- Django runtime verification must be performed locally before treating Phase 2F as complete.

## Phase 2G — local validation — 2026-11-15

- User confirmed Phase 2F was pushed at `76d1123`, migration 0007 applied, and 60 tests passed. That 60-test baseline was also re-run successfully in this workspace before adding new tests.
- Final `python manage.py test game`: **76 passed, none skipped**. This includes the existing 60 tests, 15 new inventory service/API tests, and a headless Edge test executing 17 JavaScript checks against the production adapter/save/load functions.
- `python manage.py check`: passed with no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created `django/db.phase2g-backup.sqlite3`, then applied `0008_browser_inventory_identity` successfully. `showmigrations game` confirms 0001–0008 applied. Migration adds one nullable unique column; no browser inventory backfill or save conversion was run on the working database.
- Chromium subprocess launch initially failed inside the Windows sandbox. The same test passed after the user approved running outside that sandbox. The browser's own sandbox was not disabled.
- `legacy_game/` remains untouched. Existing untracked Phase 2C–2F README files were left alone. No commit or push performed.
- See [12-browser-inventory.md](12-browser-inventory.md) for the implemented contract and remaining gameplay limitations. Headless tests cover adapter and mocked HTTP calls; they are not a manual full-game playthrough or concurrent load test.

## Phase 2H first increment — local validation — 2026-11-15

- Full suite: **90 tests passed, none skipped** (76 previous + 14 inventory operation/API tests), including existing headless Chromium checks.
- `check`: no issues. `makemigrations --check --dry-run`: no changes detected. `git diff --check`: passed.
- No schema changes, data migration, frontend changes, or edits to `legacy_game/`. No commit or push.
- Equipment/stat rules remain pending user clarification; this increment implements reads and carried/stored movement only. See [13-inventory-operations.md](13-inventory-operations.md).

## Phase 2H durability increment — local validation — 2026-11-15

- Final full suite: **104 tests passed, none skipped** (90 previous + 14 durability/destruction tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- SQLite backup created at `django/db.phase2h-durability-backup.sqlite3`; migration `0009_equipment_destruction` applied successfully. `showmigrations game` confirms 0001–0009 applied. No existing items were destroyed or converted by the migration.
- Tests verify the agreed two-segment curve, unscaled enchantments, zero-durability destruction, retained death history, stale-snapshot rejection, save rollback, and blocked browser identity resurrection/durability overwrites.
- Wear remains an internal service; combat/environment triggers, repair outcomes, full equip/stat integration, and thermal formulas are not implemented. No frontend or `legacy_game/` changes; no commit or push.

## Phase 2H equipment setting — local validation — 2026-11-15

- Full suite: **113 tests passed, none skipped** (104 previous + 9 settings tests), including existing headless Chromium checks.
- `check`: no issues. `makemigrations --check --dry-run`: no changes detected.
- Created SQLite backup `django/db.phase2h-settings-backup.sqlite3`, then applied `0010_player_game_settings` successfully. `showmigrations game` confirms 0001–0010 applied. No settings backfill or save conversion.
- The API persists the opt-in preference only; no scoring engine, automatic swap execution, or frontend controls are implemented. No commit or push. Details: [15-game-settings.md](15-game-settings.md).

## Phase 2I — local validation — 2026-11-15

- Full suite: **136 tests passed, none skipped** (113 previous + 23 equipment definition/placement tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created SQLite backup `django/db.phase2i-backup.sqlite3` before successfully applying `0011_equipment_definitions_positions`. `showmigrations game` confirms 0001–0011 applied. No automatic catalog creation, legacy adoption, or inventory/save conversion.
- Tests cover all agreed garment layers, multi-position and two-handed equipment, atomic manual swaps/unequips, identity/properties, ownership/staleness, uniqueness, destruction cleanup, save rollback/protection, and Regression history.
- Placement services are backend-only and do not calculate stats or score upgrades. No new public equip endpoints, frontend changes, or edits to `legacy_game/`. No commit or push. Details: [16-equipment-placement.md](16-equipment-placement.md).

## Phase 2J — local validation — 2026-11-15

- Full suite: **152 tests passed, none skipped** (136 previous + 16 thermal definition/calculator tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created backup `django/db.phase2j-backup.sqlite3`, then applied `0012_equipment_thermal_coverage` successfully. `showmigrations game` confirms 0001–0012 applied. No automatic rating assignment, catalog seed, property conversion, or save mutation.
- Tests cover regional coverage independent of equipment positions, distinct and zero ratings, missing configuration, exact wear-scaled decimals, metadata/revision changes, constraints, invalid data, read isolation, and ownership/life/condition validation.
- No outfit totals, armor suppression coefficients, weather/scoring formulas, thermal enchantment interpretation, or frontend work. No `legacy_game/` edits, commit, or push. Details: [17-thermal-definitions.md](17-thermal-definitions.md).

## Phase 2K — local validation — 2026-11-15

- Full suite: **174 tests passed, none skipped** (152 previous + 22 outfit-layering tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created backup `django/db.phase2k-backup.sqlite3`, then successfully applied `0013_thermal_layering`. `showmigrations game` confirms 0001–0013 applied. Existing coverage fields remain unconfigured (NULL); no item/save conversion or parameter assignment.
- Hand-calculated tests verify additive warmth, multiplicative regional cooling, equal orders, wear-dependent breathability, destruction, and multi-position identity. Additional tests verify missing data, read-only behavior, validation, revisions, and ownership/life isolation.
- Existing Phase 2J calculations remain usable without the new optional layering fields. Its API serialization assertion now includes the two additive null metadata fields; no prior rating assertion was removed.
- No weather/enchantment totals, scoring, public thermal endpoint, frontend, or `legacy_game/` changes. No commit or push. Details: [18-outfit-thermal.md](18-outfit-thermal.md).

## Phase 2L — local validation — 2026-11-15

- Full suite: **199 tests passed, none skipped** (174 previous + 25 thermal-enchantment tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created backup `django/db.phase2l-backup.sqlite3`, then successfully applied `0014_thermal_enchantments`. `showmigrations game` confirms 0001–0014 applied. No opaque-property conversion or automatic bonus assignment.
- Tests verify unscaled magical contributions, armor bypass, additive/independent regional targets, exact totals, active source selection, incomplete diagnostics, model validation, and read-only behavior. Repeated saves preserve contribution IDs; browser tampering is rejected.
- Snapshot tests verify copied contribution data, rejection of additions/edits/deletions after death, preserved item/contribution IDs through Regression, and unchanged archived JSON. A cached-Playthrough validation failure found during development was fixed by querying current life status; the final full suite passed.
- No public enchantment mutation API, weather/scoring engine, frontend, or `legacy_game/` changes. No commit or push. Details: [19-thermal-enchantments.md](19-thermal-enchantments.md).

## Phase 2M — local validation — 2026-11-15

- Full suite: **214 tests passed, none skipped** (199 previous + 15 explicit-nonthermal tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created backup `django/db.phase2m-backup.sqlite3`, then successfully applied `0015_explicit_nonthermal_equipment`. `showmigrations game` confirms 0001–0015 applied. Existing definitions keep false; no item is automatically classified and no coverage/save/property data is removed.
- Tests distinguish unconfigured from explicitly nonthermal data; verify enchantment preservation, no ordinary blockage, stale revisions, invalid-condition handling, conflict rejection/current-database validation, read-only metadata, and unchanged legacy properties.
- No public catalog editor, weather/scoring engine, frontend, or `legacy_game/` changes. No commit or push. Details: [20-nonthermal-equipment.md](20-nonthermal-equipment.md).

## Phase 2N — local validation — 2026-11-15

- Full suite: **228 tests passed, none skipped** (214 previous + 14 thermal API tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected. No migration or database update required.
- Tests cover exact nested and very large fractions, response flags/IDs, incomplete diagnostics, nonthermal enchantments, session/account/method restrictions, ignored foreign-owner query parameters, service conflicts, unsaved new-life isolation, and no gameplay/save writes on repeated GETs.
- Existing APIs/calculators remain unchanged; the new endpoint is read-only. No weather/scoring, frontend, or `legacy_game/` changes. No commit or push. Details: [21-outfit-thermal-api.md](21-outfit-thermal-api.md).

## Phase 2O — local validation — 2026-11-15

- Full suite: **254 tests passed, none skipped** (228 previous + 26 birth-draft tests), including existing headless Chromium checks.
- `python manage.py check`: no issues. `python manage.py makemigrations --check --dry-run`: no changes detected.
- Created backup `django/db.phase2o-backup.sqlite3`, then successfully applied `0016_birth_stat_drafts`. `showmigrations game` confirms 0001–0016 applied. No existing character/save backfill or conversion.
- Tests cover server draw calls/bounds, derived previews, unlimited rerolls, up to three freely changeable locks, revision/retry protection, transaction rollback, session ownership/expiry/cleanup, constraints, CSRF/account/method/body validation, and unchanged existing actors/saves.
- The API handles unconfirmed stat drafts only. No final birth, name/gender/appearance, current-Condition/training mechanics, frontend, or `legacy_game/` changes. No commit or push. Details: [23-birth-stat-drafts.md](23-birth-stat-drafts.md).

## React prototype port — 2026-11-15

The authorized React port adds no Django/backend changes. All 254 existing Django tests pass, none skipped. The new app passes 6 settings tests, 7 Edge browser checks, and its Vite production build. A live Django integration check verifies CSRF and session persistence through the Vite proxy using a temporary database. Desktop/mobile layouts and keyboard dialogs are covered; desktop screenshot visually inspected. See [24-react-prototype-port.md](24-react-prototype-port.md) and [react/README.md](../../react/README.md). No commit, push, or deployment performed.

## Birth-first React UI — 2026-11-15

All 254 Django tests pass, none skipped. The updated UI passes 6 settings tests and 14 Edge browser tests, including real birth-draft/session/CSRF persistence, unchanged existing characters, locks/switching/rerolls, stale and lost-response recovery, and mobile layout at 200% text. Production build succeeds. Test integration uses only a temporary database; no Django code/migrations, working-database writes, or legacy edits. Details: [25-birth-first-react-ui.md](25-birth-first-react-ui.md). No commit or push performed.
