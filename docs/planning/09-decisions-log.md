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

## Outfit thermal calculation discussion — 2026-11-15

Phase 2J was pushed at `8f049c3`. The user approved **explicit per-region breathability percentages** for outer layers: 100% allows all ordinary underlying cooling, 50% allows half, and 0% blocks it. Do not infer breathability from item weight. Multiple-layer composition, effects of durability on breathability, and the concrete next implementation scope remain open.

The user approved **multiplicative regional breathability stacking**: 80% × 50% outer layers pass 40% of an inner garment's ordinary cooling. A garment's own cooling is restricted only by overlapping layers outside it. This resolves multiple-layer composition; durability interaction and explicit regional layer ordering remain open.

The user specified that **holes make worn garments more breathable**. Cooling blockage must decrease with wear; simply scaling breathability downward is rejected. The numerical durability-to-blockage curve remains to be chosen. Destroyed items no longer contribute a layer.

The user approved applying the agreed wear curve to **cooling blockage**: `effective_breathability = 1 - (1 - base_breathability) * durability_multiplier` for positive durability, using fractions in [0, 1]. Initially airtight gear passes 0% at full durability, 25% at half, and approximately 75% immediately before destruction. Destruction removes the blocking layer entirely. This resolves the durability/breathability formula; regional layer ordering and next implementation scope remain open.

The user approved **explicit per-region layer order in equipment definitions**, separate from occupied equipment positions. This represents undergarment → clothing → armor and cases such as a long coat covering legs outside trousers while occupying upper clothing. Equal-order behavior and the numeric representation remain open.

The user approved **equal-order layers do not block one another**: cooling suppression uses only overlapping garments with a strictly higher regional layer order. This resolves equal-order behavior without imposing a uniqueness constraint on regional thermal depth.

The user approved **additive ordinary warmth within each region**: sum the individual condition-adjusted ratings. Breathability does not separately reduce warmth. This resolves the ordinary warmth aggregation rule; temperature interpretation and enchantment totals remain outside this calculation.

## Phase 2K — outfit thermal authorization — 2026-11-15

The user approved the reviewed Phase 2K scope with “yes”: nullable per-region breathability percentages and layer-order fields, exact internal ordinary outfit calculations from equipped instances, incomplete-data diagnostics without partial totals, inventory revision integration, and tests. Higher nonnegative integer order is outer; equal order never blocks. Regional cooling sums each condition-adjusted contribution after the product of overlapping outer effective breathabilities. Migration 0013 preserves existing coverage as unconfigured by adding nullable fields without backfill. No weather/enchantment totals, scoring engine, Player stat writes, public calculator endpoint, or frontend work. Details: [18-outfit-thermal.md](18-outfit-thermal.md). Commit/push require separate approval.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the Phase 2K layering model/calculator, migration 0013, tests, and planning decisions. The full suite passed 174 tests before publication. Weather/enchantment totals, scoring, and frontend work remain deferred.

## Thermal enchantment discussion after Phase 2K — 2026-11-15

Phase 2K was pushed at `303d17a`. For the proposed next thermal-enchantment milestone, the user confirmed **magical cooling bypasses outer clothing/armor breathability restrictions** and remains full strength until destruction, consistent with the earlier no-wear-scaling enchantment rule. Regional targeting, the explicit data contract, and aggregation remain open; no thermal enchantment implementation scope has yet been approved.

The user approved **independent regional targeting for thermal enchantments**: explicit targets may be one or more of the eight thermal regions, including all eight, regardless of the source garment's physical coverage. Do not infer magical targets from ordinary coverage. The data contract and stacking rule remain open.

The user approved **additive thermal enchantment stacking within each region**, rather than strongest-only selection: bonuses of 3 and 5 provide 8. Full strength at positive durability and bypass of ordinary cooling blockage still apply. Concrete contribution storage/calculation scope remains to be approved.

## Phase 2L — thermal enchantment authorization — 2026-11-15

The user approved the reviewed Phase 2L implementation plan with “yes”: explicit instance-owned regional contributions, full-strength magical subtotals and combined results, revision/save protection, copied death-state validation, and tests. Each contribution row has its own identity; multiple rows per item/region add, and target regions need not match physical coverage. The existing ordinary calculator stays unchanged in purpose. Combined totals are withheld when ordinary data is incomplete, while known explicit magical subtotals remain separate. No opaque legacy enchantment conversion, application/repair rolls, weather/scoring engine, frontend work, or public mutation API is included.

Migration 0014 creates the contribution table and snapshot-copy field; existing snapshots receive empty structured lists. Destruction retains contribution rows as history but ends their effects. Regression transfers the original item/contribution IDs and rejects post-death contribution changes. The browser cannot edit those rows or remove/rearrange their protected source through full-payload saves. Details: [19-thermal-enchantments.md](19-thermal-enchantments.md). Commit/push require separate approval.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the Phase 2L thermal contribution model/calculator, inventory/save protections, death-snapshot integration, migration 0014, tests, and planning decisions. The full suite passed 199 tests before publication. Weather/scoring, application/repair rolls, and frontend work remain deferred.

## Phase 2M — explicitly nonthermal equipment — 2026-11-15

Phase 2L was pushed at `ebc1cbb`. The user approved an explicit backend definition declaration of **no ordinary thermal effects**, distinct from unconfigured data, while preserving thermal enchantments. Implemented as `EquipmentDefinition.no_ordinary_thermal_effects`, default false; no automatic classification by name, item kind, or missing records. Explicitly nonthermal items add no ordinary warmth/cooling/blockage, but still obey condition/ownership/position rules and retain magical effects.

Conflicting ordinary coverage is rejected rather than discarded, through model validation and calculator checks; validation uses current database state rather than stale caches. The declaration is read-only inventory metadata included in revision hashes. Migration 0015 adds the false default without deleting/converting existing data. Tests and teaching notes: [20-nonthermal-equipment.md](20-nonthermal-equipment.md). Commit/push remain separately authorized.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the Phase 2M explicit nonthermal declaration, calculator/revision integration, migration 0015, tests, and planning decisions. The full suite passed 214 tests before publication. Weather/scoring and frontend work remain deferred.

## Phase 2N — thermal read API authorization — 2026-11-15

Phase 2M was pushed at `e44ddf8`. The user approved the reviewed Phase 2N plan with “yes”: GET `/api/equipment/thermal/`, scoped solely through the local-player session to the active life; ordinary/magical/combined results and existing incomplete diagnostics; exact nested Fraction values encoded as string numerator/denominator pairs; and ownership, precision, and read-only tests. This preserves exact transport beyond JavaScript's safe integer range without choosing a rounding rule. Valid incomplete/empty results use 200; service validation conflicts use 409; existing session/account/method restrictions remain in force.

No existing API behavior, models, saves, frontend, weather, or scoring rules are changed. No new migration or database update is required. Details: [21-outfit-thermal-api.md](21-outfit-thermal-api.md). Commit/push require separate approval.

Publication authorization: the user subsequently instructed “commit and push to github”, approving publication of the Phase 2N read-only thermal endpoint, exact JSON serialization, tests, and documentation. The full suite passed 228 tests before publication. No migration, frontend, or new gameplay rules are included.

## Birth-first character creation direction — 2026-11-15

Phase 2N was pushed at `fa00f13`. The user wants to shift focus from equipment to a completely new opening: first birth, chosen looks, and random starting stats between 1 and 5, with ID/Name on the character sheet and the listed physical, social, luck, and resource fields. Endurance/Stamina were found in earlier material; their inclusion/formula is not automatically adopted. Condition and resource semantics require clarification before schema design. Identity generation, roll mechanics, appearance details, and growth/lifecycle behavior remain proposals. Sexual attraction is an adult-only design boundary and will not be scored for newborn/child characters. No code or data reset is approved by this discussion. See [22-birth-first-character-creation.md](22-birth-first-character-creation.md).

The user added **player-chosen gender** and clarified that life experiences should shape appearance from birth, with attraction relevant later. Gender options/pronouns/mechanical effects and appearance formulas remain undecided. Early-life tracking will be nonsexual appearance/history and social impressions; sexual attraction remains an adult-only (18+) boundary. Younger-teen activation is not adopted. No model/API/frontend changes are authorized by this clarification.

The user defined **Condition as all of constitution/fitness and current wellbeing**, including hunger, fatigue, illness, and injuries. The original random 1–5 birth value still needs reconciliation with these changing factors: a baseline/current split and any combining formula remain proposals. No independent extra stat or status scale has been silently adopted.

The user approved **baseline and current Condition**: initially roll baseline Condition from 1–5, derive current Condition from that baseline and present wellbeing, and track underlying states separately so changes are explainable. Current Condition is not independently rerolled. The status scales/formula, current range, and long-term baseline growth remain open.

The user corrected **Health and Mana birth values to random 10–35**, replacing the earlier 1–5 direction for those resources. This does not settle maximum-versus-current representation or starting-full behavior. Other agreed rolled attributes retain the 1–5 direction; no Stamina rule is implied.

The user then approved **separate current and maximum Health/Mana pools**: each 10–35 birth roll sets that resource's starting maximum and current amount begins equal to it. For example, Health 27 starts at 27/27. Later growth/regeneration formulas and Stamina remain undecided.

The user approved **Endurance (1–5 starting sustained-exertion attribute)** and **Stamina (distinct current/maximum energy pool)** alongside Condition's wellbeing/performance role. Stamina is crucial to the part immediately after character creation. Its range, starting fullness, Endurance relationship, consumption/recovery, and the post-birth gameplay sequence remain unspecified; do not invent them or adopt legacy formulas implicitly.

The user defined Stamina as a **shared budget for physical, mental, and other training from newborn through adulthood**. Training leads to exhaustion, which requires rest before further activity. This is not limited to combat/physical actions. Session costs, exact exhaustion threshold/gating, rest/recovery timing, initial capacity, and the training/age progression details remain open.

The user selected **variable training costs depending on activity, intensity, and the associated stat**, and replaced independent resource birth rolls with **Health = Strength × multiplier; Mana = Intelligence × multiplier; Stamina = Endurance × multiplier**. Multipliers remain open. This supersedes independent 10–35 Health/Mana rolls; the earlier full starting Health/Mana pools remain agreed. Stamina fullness, cost/stat dependency direction, formulas, recovery, and stat-growth refill behavior are not decided. ×10 each (10–50 with 1–5 base stats) is an assistant recommendation awaiting approval, not an adopted constant.

The user approved **×10 as the initial multiplier for all three resource maximums**: Health = Strength × 10, Mana = Intelligence × 10, Stamina = Endurance × 10. With 1–5 parent birth attributes this gives 10–50 starting maxima and supersedes the earlier 10–35 independent-roll range. Health/Mana still begin full; Stamina fullness and later refill/recovery behavior remain open. No lifelong stat/resource cap is implied.

The user confirmed **Stamina also starts full at birth**. Initial current Health, Mana, and Stamina each equal their respective derived maximums. No training, recovery, or stat-growth refill formula is implied.

The user requested **unlimited creation rerolls with up to three locked base stats**, replacing the assistant's single-pre-confirmation-roll proposal. Locked values persist and unlocked base attributes reroll within 1–5. Resource maxima remain derived ×10 from their parents rather than separately rerolled/locked. Explicit draft rerolls are distinct from refreshing/loading or retrying a confirmed birth. Lock switching, exact sampling/API/retry behavior, and implementation scope remain open; no reroll currency/limit or permanent-lock rule is implied.

The user confirmed **locks can be freely removed or switched before birth confirmation**, with at most three active at once. This resolves lock-switching behavior; sampling and the concrete creation-draft implementation plan remain to be approved.

## Phase 2O — birth stat draft authorization — 2026-11-15

The user approved the reviewed Phase 2O scope with “yes”: session-owned persistent drafts for the eight base birth attributes, independent uniform integer 1–5 server rolls, unlimited explicit rerolls, up to three freely changeable locks, derived full ×10 resource previews, revision-based retry protection, and tests. This settles the sampling rule. One draft belongs to one live Django database Session; the session key is not exposed, and public IDs do not choose ownership. Draft reads/create retries do not reroll; changed locks and explicit rerolls use fresh revisions, including when chance repeats values.

Migration 0016 creates only the draft table, with no existing-actor/save conversion. Drafts are not permanent Characters and no birth-confirmation endpoint exists yet; final identity/gender/appearance and copying/freeze of selected stats remain future work. Existing sessions with legacy Players are preserved unchanged. Details: [23-birth-stat-drafts.md](23-birth-stat-drafts.md). Commit/push require separate approval.

The user authorized publication of the completed Phase 2O changes with “commit and push to github”. Validation before publication: all 254 tests passed; Django checks and migration drift checks passed.

## React prototype port authorization — 2026-11-15

The user explicitly requested recreating the Django prototype UI in React under `react/`. This supersedes the earlier frontend deferral for this scoped port. Preserve the existing design and appearance behavior, leave the Django prototype/backend and `legacy_game/` intact, and use the existing Character API. Use the active JavaScript palette where the prototype stylesheet's initial tokens differ. Preserve appearance backup version 1 and storage keys; transfer across origins by backup rather than implying shared localStorage. Newborn confirmation/stat-draft UI and other gameplay screens are separate integrations. Implementation and verification: [24-react-prototype-port.md](24-react-prototype-port.md). No commit/push or deployment authorization is inferred.

The user subsequently authorized committing and pushing the completed React port with “commit and push to github”. Pre-publication verification: 6 settings tests, 7 browser tests, the production build, and all 254 Django tests passed. Hosting deployment remains outside scope.

## Birth-first React opening — 2026-11-15

The user requested “Have new UI use birth-first creation”. Replace the React local-character opening with the existing server-owned birth stat draft flow: explicit creation, eight attributes, unlimited rerolls, up to three freely switchable locks, server resource previews, and refresh/revision-safe behavior. Do not use the old Player creation action, invent identity/appearance choices or final confirmation, or alter existing characters/saves. The UI clearly states the remaining creation steps are unavailable. A rejected stale write reloads without replay; uncertain writes require a manual read before further mutation. Details and validation: [25-birth-first-react-ui.md](25-birth-first-react-ui.md). No commit/push or deployment performed.

The user subsequently authorized committing and pushing the birth-first React UI with “commit and push to github”. Pre-publication validation: 14 browser tests, 6 settings tests, all 254 Django tests, and the production build passed. Deployment remains outside scope.

## Birth identity and confirmation — preset design first

The user requested name, gender, looks, and final birth confirmation. In response to the choice between simple free-text cosmetics and preset design, the user selected **“Define preset choices first”**. This supersedes the assistant's free-text fallback. No dependent identity/confirmation code has been changed. Proposed catalogs and confirmation direction are recorded as **awaiting agreement**, not adopted rules, in [26-birth-identity-confirmation.md](26-birth-identity-confirmation.md).

## Phase 2P — preset approval, visuals, and final birth — 2026-11-15

The user approved the reviewed presets with **“Yes. make sure every color option has an appropriate color visual and hair length has a hair length visual on the choice.”** Name/gender/looks saving, review, and final confirmation are authorized. Each color receives a matching labeled swatch/iris, and hair lengths receive SVG illustrations. The assistant stated before coding that length would be separated into Bald/Short/Medium/Long, with Straight/Wavy/Curly/Coily texture chosen separately. Gender/looks are cosmetic; bald clears unused hair fields, and Custom gender has a user-entered label. No attraction or stat bonuses are added.

Confirmation atomically creates the initial life and its permanent immutable-by-service BirthRecord and activates the existing session. Reviewed revision protection, unique source identity, idempotent retries, and frozen post-confirmation choices prevent duplicate births/rerolls. Existing local characters/saves are preserved; confirmation is refused rather than replacing them. Migration 0017 applied after a verified backup and before/after comparison of all existing game-table values. Full validation: 275 Django tests, 21 browser tests, 6 settings tests, and production build pass. Details: [26-birth-identity-confirmation.md](26-birth-identity-confirmation.md). No commit/push or deployment performed.

The user subsequently authorized committing and pushing Phase 2P with “commit and push to github”. Pre-publication validation remains 275 Django tests, 21 browser tests, 6 settings tests, and the production build passing. Hosting deployment remains outside scope.

## Phase 2Q — character loading and deletion — 2026-11-15

The user requested **“Add a way to load and delete characters.”** Implement a server-owned browser-session roster, with Load/New character/Delete and exact-name deletion confirmation. New character retains saved stories and resumes any unfinished draft; loading selects existing life/save state instead of creating or rerolling. Logical deletion removes playable access while retaining protected historical records, which the UI explains; no purge/restore system is introduced. Only owned nondeleted entries are loadable; legacy APIs also reject deleted/foreign ownership. Existing anonymous sessions are adopted from their trusted active ID, not by scanning unrelated characters. Details: [27-character-management.md](27-character-management.md). Migration 0018 applied after verified backup; existing rows preserved. No commit/push or deployment authorized.

The user subsequently authorized publication with “commit and push”. Pre-publication validation: 296 Django tests, 29 browser cases, 6 settings tests, and the production build passed. Hosting deployment remains outside scope.

## Local character-data purge — 2026-11-15

The user explicitly requested deleting any saved character records from the database. Permanently removed all six playable characters and associated Players, Legacies, lives, birth records/drafts, roster entries, saves, and character-owned records from the local database in one transaction. Cleared session character selections; shared equipment definitions and accounts were preserved. All targeted tables were verified empty and SQLite foreign_key_check passed. Recovery backup: `django/db.before-character-purge-20261115-204924.sqlite3` (ignored by Git). Django preview restored; character-list endpoint confirmed empty. No application-code changes or commit/push performed for this maintenance action.

The user then required in-game deletion to completely destroy the selected character. This supersedes the soft-delete decision: the service now permanently erases the entire owned story and its history after typed-name confirmation, without making a recovery copy. Other stories/shared definitions remain intact, and external protected references trigger atomic rollback. Existing external backups are not altered. See [28-permanent-character-deletion.md](28-permanent-character-deletion.md). Validation: 298 Django tests, 8 character-management browser tests, and production build pass. No commit/push.

The user subsequently authorized committing and pushing the permanent-deletion changes with “commit and push”. Validation remains 298 Django tests, 8 character-management browser tests, and production build passing. No hosting deployment is included.

## Django admin screens — 2026-11-15

The user requested admin screens via `admin.py`. Added searchable/filterable inspection screens for all game models and related inlines. Initial game state/catalog screens are read-only, with add/edit/delete and bulk deletion blocked so admin cannot bypass game services. Existing equipment-adaptation preferences are editable with fixed ownership. Session credentials are masked. No accounts or passwords are created/changed. See [29-django-admin.md](29-django-admin.md); seven new tests and all 305 Django tests pass. No schema change, commit, or push.

The user subsequently authorized committing and pushing the admin screens with “commit and push”. Validation: all 305 Django tests pass, system checks pass, and no migration drift is detected. No deployment or account changes are included.

## Save access after browser restart — 2026-11-15

The user reported save loading failing after closing/reopening the same normal browser/address. Confirmed a shared admin/game session lifecycle bug, rather than a browser-close cookie-expiry default. Isolated admin into its own cookie, retained persistent game cookies, and added validated compatibility handling for old shared staff sessions without claiming unrelated orphaned characters. See [30-session-persistence.md](30-session-persistence.md). All 309 Django tests and 9 relevant browser cases pass, including an actual persistent-profile browser process restart. No migration, account/password changes, live-data reset, commit, or push.

## Orphaned character recovery — 2026-11-15

The user clarified that recovery is an admin-level function and the goal is to make existing characters available in a new browser session. The local database contains two unrostered Players with permanent BirthRecords. Since those records alone cannot authenticate which browser should claim them, recovery uses an admin-issued, short-lived, one-use bearer code for one deliberately selected orphan, redeemed in the new browser's character screen. No anonymous orphan listing or automatic mass assignment. Codes expire after 24 hours, previous unredeemed codes for the same Player are invalidated on reissue, and only a digest is stored. Anyone who obtains the code can claim that selected save. Implementation/validation: [31-orphaned-character-recovery.md](31-orphaned-character-recovery.md).
