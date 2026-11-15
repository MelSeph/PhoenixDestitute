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

## Phase 2H direction and initial backend increment — 2026-11-15

The user clarified that the new backend takes precedence over legacy frontend data. The legacy repair proposal was withdrawn. The frontend prototype and React preference are context only; the user explicitly declined changing scope to a React foundation, then instructed “proceed” with backend inventory operations.

Implement session-scoped relational inventory reads and narrow whole-item carried/stored placement commands. Preserve identities/properties, validate slots and expected state, and refresh existing versioned compatibility saves atomically so stale browser writes fail. Do not add a frontend, import legacy rules, invent capacity limits, or perform equipment/stat changes without defined rules. Equip/unequip scope remains pending a specific question to the user. Details and limits: [13-inventory-operations.md](13-inventory-operations.md).

## Equipment rule discussion — 2026-11-15

The user selected defining equipment rules first. Agreed additions: upper/lower undergarments, one paired hosiery position for socks/stockings/pantyhose independent of footwear, and environment-dependent warmth/cooling plus durability for clothing. The user explicitly chose destruction at zero durability, with restoration possible at any positive durability. Retaining zero-durability items as repairable broken equipment was rejected. Exact calculations, repair costs, and history-safe destruction persistence remain undecided. See [14-equipment-rules.md](14-equipment-rules.md); these decisions do not authorize inventing the remaining gameplay rules.

The user subsequently confirmed that destruction at zero and repairability above zero apply to **all equipment**, not only clothing.

The user chose **gradual effectiveness degradation** as durability falls, until repair or destruction. Full effectiveness until zero was rejected; the exact curve and attribute-specific effects remain to be defined.

The user selected **gentler scaling**, illustrated as 75% effectiveness at 50% durability, instead of direct scaling (50% effectiveness at 50% durability). The full curve and near-zero behavior remain undecided.

The user then specified **about 25% effectiveness immediately before zero durability**, with destruction still occurring at zero. This supersedes the proposed near-zero floor of roughly 50%. Interpolation and rounding remain undecided.

The user approved **straight-line interpolation within each half of durability**: full durability → 100% effectiveness, half → 75%, approaching zero from above → 25%, zero → destroyed. With positive durability fraction `r`, use `0.5 + 0.5*r` for `r >= 0.5`, otherwise `0.25 + r`. Rounding and which attributes scale remain open.

The user specified that **enchantments retain full strength until equipment breaks**. Under the agreed destruction-at-zero rule, enchantment bonuses are unscaled for positive durability and cease contributing when the item is destroyed. No repairable zero-durability state is introduced.

The user specified **mastery/stat-dependent repair quality**: low repair mastery plus stats insufficient for repairing the item degrades its maximum durability; high repair mastery plus high stats relevant to crafting that equipment can increase its maximum durability. Always preserving or always reducing maximum durability was not selected. Mixed mastery/stat cases, exact requirements/formulas, repair amounts/costs, and improvement limits remain undecided.

The user resolved mixed repair qualifications: **high mastery / low stats preserves the current maximum**; **low mastery / high stats can reduce the maximum**, depending on mastery shortfall and gear level. The crafting recipe identifies the applicable mastery, and the mastery required to create the equipment is the baseline for repairing it to its current maximum. This resolves the previously open mixed-case decision; numerical formulas and improvement limits remain open.

The user approved a **repair quality ceiling based on mastery, relevant stats, and the item**. Repeated repairs must not increase maximum durability indefinitely. The ceiling formula and item-specific limits remain open; this agreement does not select numerical caps or growth rates.

The user specified **guaranteed results to a floor, with chance of success/failure above it**, and referred to exceeding the floor or ceiling. The guaranteed-floor principle is recorded; numerical floors and whether exceptional outcomes can exceed the earlier ceiling remain unresolved. Clarification is required before treating the ceiling as a soft limit.

The user explicitly clarified **soft ceiling**: exceptional success may exceed the expected upper range. This resolves the prior hard-versus-soft ambiguity. The floor remains guaranteed; results above it are chance-based. Numerical outcomes and how repeated exceptional repairs interact with the earlier goal of avoiding indefinite growth remain undecided; do not silently impose a hard cap.

The user then instructed “proceed”. Implement the settled deterministic durability curve, unscaled enchantment calculation, and internal wear/destruction service while leaving undefined repair rolls and thermal/stat mappings unwired. Destroyed equipment retains a history-only relational identity using a destroyed location, is omitted from usable inventory, and cannot be replayed through its old browser token. This preserves Phase 2F history without creating a repairable broken-item state. Migration 0009 adds that location choice without backfilling gear or deleting saves. See `14-equipment-rules.md` for technical limits and pending rules. Commit/push remain separately authorized.

The user approved **separate ordinary clothing and armor layers**: upper undergarment → shirt/upper clothing → torso armor; lower undergarment → trousers/lower clothing → leg armor; hosiery beneath footwear. Ordinary clothing and armor do not compete for one torso/leg position. Additional footwear armor layers and multiple garments per layer remain undefined.

The user approved **definition-declared multi-position equipment**: a single instance may occupy multiple positions with one identity/durability value, and all required positions must be available together. Examples include jumpsuits spanning upper/lower clothing, one-piece undergarments spanning both undergarment positions, and two-handed weapons occupying both hands. Pantyhose remains hosiery-only. No partial equipping or name-based position inference. Automatic replacement versus explicit unequipping remains undecided.

The user selected **automatic equipment swaps**: conflicting equipped instances move to carried inventory, then the new item takes its required positions. Multi-position conflicts are handled once per identity and release the whole old item's occupied positions. Failure to complete any move rolls back the entire swap. Explicit manual unequipping is not required; no capacity limit or item-property changes are implied.

The user revised automatic replacement: it occurs **only if the new item is better than the current equipment**. Unconditional swapping is superseded. The superiority criterion, ties/tradeoffs, comparison against multiple displaced items, and manual overrides remain unresolved. Atomicity and preservation rules still apply to qualifying swaps.

The user specified that superiority considers **weather, build, player priorities, and overall score** together. No fixed weighting, ordering, or numerical scoring formula has been selected. Tie behavior, multi-item comparisons, and manual overrides remain open.

The user explicitly approved **manual selection of lower-scoring equipment** as a player choice. Only automatic replacement is gated on superiority; manual choice does not imply bypassing ownership, condition, or position/eligibility validation.

The user approved **complete-loadout comparison** for automatic replacements: compare all resulting equipment benefits against the current set, including every displaced instance for multi-position gear. Automatic replacement requires a strictly higher score; equal scores retain current gear. This resolves tie and multi-item comparison behavior. Manual selection remains available. Numerical score weights/formulas remain open.

The user selected **player-configurable equipment adaptation timing in game settings**: automatic reevaluation/swaps on weather or build changes, or score updates only until the player requests auto-equip. Neither behavior is imposed universally. The default setting and persistence schema remain undecided; existing superiority and atomicity rules apply to automatic swaps.

The user approved **player-controlled timing as the default**, with automatic adaptation available as an opt-in setting. This resolves the default-mode decision; preference persistence and reevaluation implementation remain open.

The subsequent “continue” advances the settled preference into a backend-only increment: one `PlayerGameSettings` record per existing Player, default false, and session-scoped GET/POST `/api/game/settings/`. Reads do not create rows; updates accept a boolean with CSRF/ownership checks. Player-level persistence survives life transitions and is independent of save JSON. Migration 0010 creates the table without backfill. The setting does not trigger equipment changes until a scoring/adaptation engine is defined and implemented. See [15-game-settings.md](15-game-settings.md). No frontend, commit, or push is included.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the accumulated Phase 2H inventory commands, durability/destruction foundation, equipment-setting persistence, tests, migrations 0009–0010, and planning decisions. The full suite passed 113 tests before publication; scoring, repair rolls, equipment positions, and frontend integration remain deferred as documented.

## Phase 2I — definitions and placement authorization — 2026-11-15

Phase 2H was pushed at `d24049a`. The user approved the reviewed Phase 2I plan with “yes”: additive equipment definitions/reservations, internal manual equip/unequip services with atomic displacement, destruction cleanup, legacy-save protection, and tests. No public equip endpoint, character-stat integration, automatic scoring, thermal formulas, repair rolls, or frontend work is authorized by this phase.

Definitions declare the agreed garment/hand positions through relational requirement rows; instances opt in through an explicit nullable definition foreign key. Existing gear is not classified or adopted automatically. Manual choice bypasses scoring but requires valid condition/ownership and complete known occupancy. Unidentified/inconsistent equipped gear blocks ambiguous placement. Displaced instances retain properties and use distinct lowest-free carried slots; no capacity rule is introduced. Explicitly adopted instance data/placement is protected from full-payload browser edits. Details, scope limits, and validation: [16-equipment-placement.md](16-equipment-placement.md). Commit/push require separate approval.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the Phase 2I implementation, migration 0011, tests, and documentation. The full suite passed 136 tests before publication. Deferred public equip/stat/scoring/frontend work remains outside this commit's scope.

## Equipment effects discussion after Phase 2I — 2026-11-15

Phase 2I was pushed at `251108a`. For the proposed Phase 2J equipment-effects foundation, the user approved using the agreed wear curve for physical damage, armor protection, warmth, and cooling, and explicitly added **weight** to the wear-scaled values. Keeping weight constant was rejected because degrading equipment loses material. Original values remain preserved and condition determines effective values. Enchantments stay unscaled until destruction; occupied positions remain unchanged. Weight units/load rules, thermal aggregation, numerical environmental/scoring formulas, and the concrete Phase 2J implementation scope remain open.

The user selected **different warmth and cooling layering rules**: layering increases warmth, while heavy outer armor limits the cooling benefit of breathable underclothing. One common additive/diminishing aggregation rule for both was not selected. Exact formulas, regional versus global application, and environmental effects remain undecided.

The user approved **regional cooling suppression**: torso armor limits the upper layers beneath it, and leg armor limits the lower layers beneath it. This is not a global reduction across the whole outfit. Exact garment coverage and numerical suppression remain open.

The user approved **definition-declared thermal coverage separate from equipment positions**. Socks may cover feet, stockings feet/legs, and pantyhose feet/legs/lower torso while all occupy hosiery. Explicit definitions support variants such as footless stockings; names do not determine coverage. Cooling suppression requires regional overlap with an outer layer. Region vocabulary, rating distribution, and numerical overlap/suppression rules remain undecided.

The user approved **per-region warmth and cooling ratings** on equipment definitions. Multi-region garments may have different values for each covered region; no item-wide rating is duplicated or automatically split. Durability scales the ordinary regional ratings and cooling restrictions remain local to overlap. This resolves rating distribution; numeric scales and aggregation/suppression formulas remain open.

The user confirmed that eight **thermal regions** are sufficient: head, neck, upper torso, lower torso, arms, hands, legs, and feet. Paired limbs are grouped. Thermal coverage remains independent of occupied equipment positions; covering arms does not require a separate arm equipment position. Finer body-region divisions are not part of the initial design.

## Phase 2J — thermal definition authorization — 2026-11-15

The user approved the reviewed Phase 2J plan with “yes”: additive explicit regional warmth/cooling definition records, inventory metadata/revision integration, ordinary per-item wear-scaled calculations, and tests. Missing data remains unconfigured rather than inferred as zero. Decimal storage uses four fractional places; this does not choose rating units or balance values. Calculations preserve exact fractions internally, with no new rounding rule. No outfit aggregation, numeric cooling suppression, weather/scoring engine, thermal enchantment schema, or frontend work is implemented. Details: [17-thermal-definitions.md](17-thermal-definitions.md). Migration 0012 creates only the new table, with no seed data or conversion. Commit/push require separate approval.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the Phase 2J thermal definition/calculator implementation, migration 0012, tests, and planning decisions. The full suite passed 152 tests before publication. Deferred outfit, weather, scoring, and frontend work remains outside this commit's scope.
