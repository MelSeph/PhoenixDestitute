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

## Phase 2C — Backend-only playthrough lifecycle — 2026-11-15

| Decision | Rationale and limits |
|---|---|
| Add an atomic `apply_life_outcome` service for simulated playthrough changes | Exercises the already-approved Lifecycle relationships without exposing gameplay actions |
| Resurrection retains the current active Playthrough | No new character or archived life is created; game state is not modified |
| Regression archives the current Playthrough and creates a new active one with the same Character and Legacy | No inventory movement, knowledge grants, stat resets, or world reset yet |
| New Life (same) reuses Character; New Life (successor) creates a distinct playable Character | Successor creation is only a backend placeholder for a future character-creation panel; any successor may be unrelated |
| Historical playthroughs remain queryable as memories only | No API or UI for returning to historical worlds is added |
| Existing `Player` and `GameSave` remain the gameplay/save authority | Transitions are **not wired to death gameplay**. Per-playthrough saves are a prerequisite before activating transitions in the game |
| No schema changes in Phase 2C | The Phase 2A/2B models already represent the required relationships; no migration 0006 is needed |

Regression inventory-at-death and mastery diminishing returns remain approved *future* rules, not Phase 2C behavior. This change does not implement death snapshots, NPC generations, era changes, character creation UI, nor lasting memory mechanics. Playthrough transitions are only safely callable in isolated backend scenarios at this stage.


## Phase 2D — Playthrough-aware backend saves — 2026-11-15

| Decision | Reason and boundary |
|---|---|
| Add a one-to-one `PlaythroughSave` record containing JSON and updated timestamp for each life | Current `GameSave` permits only one row per Player; distinct lives need distinct snapshots |
| Preserve existing `GameSave` and populate initial-life saves by migration `0006` | Existing player saves must not be deleted or overwritten; historical records kept |
| Copy legacy save to the **initial** playthrough, not arbitrarily to a later active life | Legacy GameSave has no reliable life identifier; prevent silently attributing old data to a new era |
| Add a backend-only active-life save/load service and historical read service | Scoped writes cannot overwrite archived saves; a newly transitioned life starts without a save |
| Mirror new active save writes to `GameSave` transactionally for backward compatibility | Old callers can continue reading the latest saved JSON after an explicit service save; mirror is not a substitute for life-aware reads |
| Do not connect existing frontend/API or lifecycle transition code | Legacy JS references older `/api/players/<id>/save/` and `/load/` endpoints that are **not** present in current Django URL routes. Phase 2D is a storage foundation, not a production-ready death/save UI |

**Known limitation:** Existing code that reads `GameSave` directly can still see a predecessor's data immediately after a backend-only simulated life transition and before the new life is saved. New code must use `load_active_playthrough` (which returns `None` for an unsaved life); UI/API cutover and stat/inventory reset are future milestones. The new schema enforces one save per playthrough; read-only historical policy is enforced by the service, not by database-level prohibitions on direct model writes. No account authorization or save/load endpoints are introduced.

## Phase 2E — Session-scoped active-life save/load API — 2026-11-15

| Decision | Rationale and limitation |
|---|---|
| Add `GET /api/game/load/` and `POST /api/game/save/` using only session-selected local Player | Avoid ID-based reads/writes to other characters; account saves still unsupported |
| Return an explicit 404 for an unsaved active life | Never silently load predecessor data from the compatibility `GameSave` |
| Continue using Phase 2D `PlaythroughSave` service, retaining atomic `GameSave` mirror | Historical saves remain immutable through the API; preserve previous integrations |
| Update only Django-hosted legacy JS copy, not `legacy_game/` | Replace hard-coded Player 2 with session-bound active saves; auto-create local Player on first save |
| Keep CSRF checks and provide homepage CSRF cookie | Prevent forged write requests; no CSRF exemption |
| Do not expose life-transition APIs yet | Death snapshots, attribute resets, and inventory transfers not implemented |

**Boundary:** Any old browser session cookie is needed to access its saved Player. Current implementation does not offer an account-recovery route or assign another player's save from a supplied ID.


## Phase 2F — Inventory identity and death snapshot foundation — 2026-11-15

| Decision | Rationale / limitation |
|---|---|
| Create a minimal relational InventoryItem holding item/batch identity, properties, quantity and carried/equipped/stored placement | Ensure a persistent item identity survives Regression; ordinary stored/equipped items are excluded. This is a new backend foundation, **not** a conversion of the existing GameSave JSON. |
| Capture a per-death immutable-by-service list of carried inventory slots as DeathSnapshot and DeathSnapshotEntry | Death-time eligibility must not be determined by changes made after death; multiple deaths per playthrough are possible after Resurrection. |
| Provide a backend-only atomic `regress_from_death_snapshot` helper | Uses existing Phase 2C lifecycle transition and moves existing item rows without cloning them; refuses stale or already-used snapshots. |
| Do not expose a death endpoint or wire to actual combat | The live JS inventory is not yet mapped to relational inventory. Caller must freeze inventory at death; unrelated model writes are not globally prevented. |
| No hardcoded slot capacity | Inventory size and stack limits have not been finalized; the slot represents placement, not an approved capacity rule. |

**Implementation boundary:** no changes to the legacy original, browser save/load API, Player or GameSave. No automatic material conversion, stat resets, world timeline simulation, or player death hook. Snapshot rows should only be created via the dedicated backend service. Item `properties` currently represents instance-specific attributes and is not a substitute for a future ItemDefinition / MaterialBatch schema.

## Phase 2G — Browser inventory integration — 2026-11-15

User approved the reviewed proposal with “make it so”. Commit and push still require separate approval. Detailed evidence, teaching notes, and limitations are in [12-browser-inventory.md](12-browser-inventory.md).

Publication approval: user subsequently instructed “push to github”, authorizing committing the Phase 2G changes and pushing them to the existing GitHub remote. Unrelated untracked Phase 2C–2F README files remain excluded.

| Decision | Reason / alternative rejected |
|---|---|
| Add a nullable unique client UUID alongside the existing item primary key | Preserve backend identities and avoid duplicate creations after lost responses; rebuilding all rows on every save rejected |
| Synchronize a versioned inventory envelope inside the active-save transaction | Keep item rows, life-scoped JSON, and compatibility JSON consistent; independent item/save writes rejected |
| Convert old saves only after a successful load and explicit save | Preserve old JSON and reject ambiguous conversion; bulk migration and name-based merging rejected |
| Use body-position fields for worn gear and counters for potion quantities | The legacy array mixes gear and stale potion references; treating every entry as equipped or carried rejected |
| Keep full item properties and explicit carried/stored entries | Preserve upgrades, durability, and distinct instances sharing a definition; automatic material conversion deferred |
| Use original catalog defaults when converting name-only equipment, retaining legacy object references during restoration | Old saves lack instance properties; guessing missing upgrades or breaking reference-based gameplay comparisons rejected |
| Require current playthrough and revision; require saved timestamp for first conversion | Reject stale tabs and old-client overwrites after conversion; blind overwrite rejected |
| Leave NULL-token backend records unmanaged and block deletion of snapshot-linked rows | Preserve Phase 2F data/history; automatic adoption, deletion of history, and invented disposal rules rejected |
| Keep transition UI and full new-life restoration deferred | Inventory synchronization alone cannot safely reset the rest of the game; stale-life writes and empty saves that would erase transferred items are rejected |
