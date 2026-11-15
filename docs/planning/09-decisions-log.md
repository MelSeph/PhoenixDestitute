# Decisions log

| Date | Decision | Why | Alternatives rejected | Scope / approval |
|---|---|---|---|---|
| 2026-11-14 | Planning only; original `legacy_game/` is read-only | User's `message.txt` and project-folder clarification | Rebuilding or editing original game | Established requirement |
| 2026-11-14 | Framework remains undecided; plan must remain stack-agnostic | Explicit in `message.txt` | Choosing Django just because a directory exists | Established requirement |
| 2026-11-14 | `PhoenixDestitute/` is project root; `legacy_game/` and `django/` are subdirectories | User confirmed folder hierarchy | Treating `legacy_game/` as writable project root | User confirmed |
| 2026-11-14 | `CLAUDE.md` working principles approved | User reviewed and approved Step 1 | None proposed | User approved |
| 2026-11-14 | Twelve-file handbook structure approved | Separate gameplay research, app choices, models, analytics and validation | None formally evaluated | User approved |

**No candidate app boundary, model, dependency direction, or event-logging strategy is approved.** Add subsequent decisions only after an interview round, recording actual considered alternatives and reasoning.

## Planning-mode clarification — 2026-11-15

| Date | Decision | Why | Alternatives and status | Approval |
|---|---|---|---|---|
| 2026-11-15 | Keep the work labeled *planning*, but establish tangible checkpoints by inspecting and validating existing backend work | User explicitly requested practical progress without abandoning planning | Rebuilding Django is **not** approved; retaining Django is **not** mandated | User-stated preference |

**Still pending:** review of user's current local Django files; whether to continue this Django codebase, repair it, or deliberately restart; initial models and any implementation approval. The previous interview established gameplay requirements, but the handbook has not yet fully incorporated or validated every conversation decision.

## Phase 2A authorization and gameplay foundations — 2026-11-15

| Date | Decision | Rationale | Alternative / boundary | Approval |
|---|---|---|---|---|
| 2026-11-15 | Introduce an additive `Legacy`, `Character`, and `Playthrough` foundation in the existing Django `game` app | Distinguish continuous story/memories, individual person, and one life/world timeline | Do not rewrite the working Player API, `Player`, `GameSave`, or legacy game | User said “go ahead” after Phase 2A recommendation |
| 2026-11-15 | Retain `Player` and `GameSave` during gradual migration | Avoid risking existing saves and prototype behavior | Immediate replacement rejected for Phase 2A | Approved scope |
| 2026-11-15 | Regression carries only the items in carried inventory slots **at death**, not equipped or externally stored possessions | Rewards preparation, prevents after-death rearrangement | Actual transfer implementation deferred | User selected |
| 2026-11-15 | Old timelines remain available as memories, not physically revisit-able | Separate remembered history from active world state | Physical return to archived playthroughs rejected | User selected |
| 2026-11-15 | New Life can return as younger original person or create a new person, even without biological descendants; all New Life people retain past-life memories | Legacy continuity is not the same as biological ancestry | Genealogy and actual memory access mechanics deferred | User selected |
| 2026-11-15 | Previously attained mastery accelerates relearning but bonuses have natural diminishing returns, not an endlessly stacking regression-count multiplier | Earlier achievements make repetition easier; no endless power exploit | Exact formula deferred | User confirmed |
| 2026-11-15 | One active playthrough per Legacy in initial foundation | Single-player lifecycle consistency | More complex parallel branches deferred | Phase 2A working assumption, verify on review |

**Phase 2A implementation boundary:** Only additive models, migration, and tests plus planning text are changed. Existing data is not migrated or backfilled into the new models. `Player` and `GameSave` stay authoritative for the current API. Cross-life memory, crafting progression, inventory, resurrection/regression/new-life operations, and world evolution are NOT implemented by this milestone.

## Phase 2B implementation authorization — 2026-11-15

| Date | Decision | Rationale | Boundary | Approval |
|---|---|---|---|---|
| 2026-11-15 | Preserve `Player` and `GameSave`, link each Player to one Legacy, and backfill existing Player records to an initial Character/Playthrough | Existing saves must continue working while the new models become usable | Do not migrate GameSave, change player stats, implement transitions, or edit legacy_game | User: “make it so” after Phase 2B proposal |

**Phase 2B design detail:** `Player.legacy` is a nullable one-to-one compatibility relationship. The active Playthrough identifies the current Character, avoiding a second mutable current-character foreign key on Player. New local players are provisioned atomically; migration `0005` backfills existing rows. Existing direct calls to `Player.objects.create` outside the API are not automatically provisioned; integration of additional creation paths is deferred. `Character.name` is an initial identity snapshot; during compatibility the original Player fields remain authoritative for the old API. Existing GameSave is still one-to-one with Player and cannot independently save multiple lives.
