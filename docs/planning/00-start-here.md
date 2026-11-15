# Start here — Phoenix Destitute backend planning

**Status (2026-11-15):** Phase 2F completed and pushed at `76d1123` (migration 0007 applied, 60 tests passed, confirmed by user). Phase 2G browser inventory bridge authorized with “make it so”; local implementation and validation are documented in [12-browser-inventory.md](12-browser-inventory.md). Commit/push approval remains separate. Earlier planning-only boundaries below are retained as historical context; later approved phase scopes supersede them.

**Current local work:** Phase 2P identity/visuals/birth confirmation was pushed at `18d6c7f`. The user requested character loading/deletion; Phase 2Q adds a session-owned roster with Load/New character/Delete and typed-name confirmation, retaining protected history internally. See [27-character-management.md](27-character-management.md). Migration 0018 is applied after backup and preservation checks. All 296 Django tests, 6 settings tests, and 29 browser tests pass; production build succeeds. No commit/push yet. Training, age progression, dynamic Condition, and later-life progression remain incomplete.

**Latest update:** Phase 2Q was pushed at `3e990e7`. The user subsequently requested a local database purge and then explicitly changed in-game Delete to permanent erasure of the selected story and history, superseding logical deletion. Implemented locally with ownership/name checks, ordered deletion, and atomic rollback; see [28-permanent-character-deletion.md](28-permanent-character-deletion.md). All 298 Django tests and 8 character-management browser tests pass; production build succeeds. No new migration, commit, or push for this update.

The equipment-adaptation preference is now persisted through a session-scoped API, defaulting to player-controlled timing: [15-game-settings.md](15-game-settings.md). Migration 0010 is applied locally and the full suite has 113 passing tests. Automatic adaptation/scoring remains unimplemented; the preference alone does not change gear.

## Read next

1. [01-game-overview.md](01-game-overview.md) for the observed original game.
2. [02-file-inventory.md](02-file-inventory.md) for source provenance and initial reads/writes/decides notes.
3. [03-data-rules-presentation.md](03-data-rules-presentation.md) to separate browser presentation from stored data and gameplay rules.
4. [10-open-questions.md](10-open-questions.md) for our next short interview round.

The remaining documents record decisions **only after discussion and user agreement**.

## Scope and project boundaries

- `PhoenixDestitute/` is the main project root.
- `legacy_game/` is the original game; **read-only**.
- `django/` is pre-existing work; **not an approved framework choice** and not modified in planning.
- `react/` is present as an empty folder in the supplied ZIP; frontend decisions are outside scope.
- Only `CLAUDE.md` and `docs/planning/*.md` may be written in the user's working project; this download is a separately prepared copy of those approved planning files.
- No code, models, migrations, dependencies, endpoints or frontend changes.
- `Phoenix_Destitute_Backend_Apps.xlsx` is a **proposal**, not an adopted design.

## Evidence status

- ZIP entry list inspected, along with loaded script references in `legacy_game/index.html` and source summaries for legacy JavaScript files.
- This is a **first-pass inventory**, not a verified complete behavioral trace. Individual read/write paths need further line-by-line verification before architecture conclusions.
- No app boundary, dependency graph, model ownership or analytics logging policy is final.

## Recording protocol

After each agreed design decision, update its topic document and `09-decisions-log.md` with date, rationale and rejected alternatives. Never silently fill uncertainties with assumptions.

## Planning Phase 2 — existing-backend audit (2026-11-15)

The user wants planning to continue **with verifiable progress**, and is open to retaining or restarting Django after assessment. This does **not** authorize modifying Django code. See `11-validation.md` for a source-grounded audit of the Django snapshot in the uploaded `PhoenixDestitute.zip`.

**Next practical checkpoint:** compare that archived snapshot with a current copy of the user's local `django/` working tree, since they may not represent the same version. Then agree on a minimal data-model demonstration, with a separate explicit approval before creating code or migrations.

## Phase 2A delivery (2026-11-15)

The user explicitly authorized implementing the three foundational models following design review. This is a narrow exception to the earlier planning-only code boundary: `django/game/models.py`, an additive `0004` migration, and a focused tests module are changed. Existing `Player`, `GameSave`, views, frontend, and `legacy_game/` are preserved. No inventory or death-transition logic is implemented. See `09-decisions-log.md` and `06-candidate-models.md`. Runtime Django tests remain to be executed on the user’s local environment.

## Phase 2B delivery (2026-11-15)

The user authorized integrating existing players with the life foundation. An additive nullable `Player.legacy` one-to-one relationship and migration `0005` backfill existing players into one Legacy, playable Character, and initial Playthrough. New anonymous player creation uses the same foundation. Existing Player/GameSave stats, APIs, and JSON remain authoritative. Transition operations and live save migration are not implemented. Django runtime verification must be performed locally before treating this milestone as complete.
