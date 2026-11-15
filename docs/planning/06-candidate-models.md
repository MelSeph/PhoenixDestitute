# Candidate models — spreadsheet suggestions only

**Not approved.** These entries are copied as candidate topics from `Phoenix_Destitute_Backend_Apps.xlsx`; the spreadsheet’s MVP/Later labels are **its proposals**, not our decisions. Fields and relationships are suggestions from the workbook and require source-based review and user agreement.

Terms like `TextChoices`, `abstract`, and `non-model` describe **non-table concepts**; the actual implementation will depend on the backend stack, which is undecided.

## `core` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| TimeStampedModel (abstract) | created_at, updated_at | None (abstract - creates no table). | MVP |
| CharacterClass (TextChoices, not a table) | WARRIOR, ARCHER, MAGE | Used by players.Player and by items (class restrictions). | MVP |
| GameEvent | player_id (plain integer, not an FK), event_type, payload (JSON), created_at | None - deliberately no FK, because core cannot import players. | Later |
| (non-model) random helpers | - | - | MVP |
| (non-model) constants and validators | - | - | MVP |
| (non-model) dev cheat endpoint | - | - | Later |

## `items` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| Item | name, description, item_type (weapon/armor/potion/material/drop/misc), base_value, stackable, class_restriction (nullable, from core) | Parent of Weapon/Armor/Potion via one-to-one. | MVP |
| EquipmentSlotType | code, name | Referenced by Armor and by inventory.EquippedItem. | MVP |
| Weapon | item (1-1), damage_min, damage_max, damage_type, proc_effect (nullable), proc_chance | One-to-one Item; FK EquipmentSlotType (hand). | MVP |
| Armor | item (1-1), slot (FK), defense, stat bonuses | One-to-one Item; FK EquipmentSlotType. | MVP |
| Potion | item (1-1), restores (health/stamina/mana), amount | One-to-one Item. | MVP |
| Material | item (1-1), is_gatherable, tier | One-to-one Item. | Later |
| Recipe | output_item (FK Item), output_qty, station_type (forge/tannery/apothecary) | FK Item; has many RecipeIngredient. | Later |
| RecipeIngredient | recipe (FK), item (FK), quantity | FK Recipe, FK Item. Unique (recipe, item). | Later |

## `world` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| Location | name, description, location_type (town/road/wilds/dungeon), parent (self FK, nullable), is_starting_area | Self-referencing parent FK. Referenced by shops, npcs, combat, town. | MVP |
| LocationConnection | from_location (FK), to_location (FK), requirement (nullable), travel_cost | Two FKs to Location. | Later |
| LocationResource | location (FK), material (FK Item), min_yield, max_yield, weight | FK Location, FK Item. | Later |

## `npcs` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| NPC | name, description, level, base health/stamina/mana, strength, defense, endurance, intelligence, home_location (FK Location, nullable) | FK Location. Many roles via NPCRole. | MVP |
| Role | code, name | Referenced by NPCRole. | MVP |
| NPCRole | npc (FK), role (FK) | FK NPC, FK Role. Unique (npc, role). | MVP |
| EnemyProfile | npc (1-1), xp_reward, gold_min, gold_max, aggression | One-to-one NPC. | MVP |
| AllyProfile | npc (1-1), join_condition, help_style | One-to-one NPC. | Later |
| ShopkeeperProfile | npc (1-1), markup, buy_rate | One-to-one NPC. | Later |
| ResidentProfile | npc (1-1), unlock_requirement | One-to-one NPC. | Later |

## `shops` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| Shop | name, keeper (FK NPC), location (FK Location, nullable), is_open | FK NPC (shopkeeper role), FK Location (nullable). A town Building may point to a Shop. | MVP |
| ShopItem | shop (FK), item (FK), price, stock (null = unlimited), class_restriction (nullable) | FK Shop, FK Item. Unique (shop, item). | MVP |
| Transaction | player (FK), shop (FK), item (FK), quantity, unit_price, direction (buy/sell), total_gold, created_at | FK Player, Shop, Item. | MVP |
| ShopPriceRule | shop (FK), item (FK), multiplier, active_from/to | FK Shop, FK Item. | Later |

## `players` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| User (framework built-in) | username, password, email | Not designed by hand. | MVP |
| SaveGame | user (FK), slot_name, game_version, created_at, updated_at, is_active | FK User; one Player. | MVP |
| Player | save (1-1), name, gender, class (from core), level, experience, max/current health, stamina, mana, strength, defense, endurance, intelligence, current_location (FK) | One-to-one SaveGame; FK Location. | MVP |
| LevelUpEvent | player (FK), old_level, new_level, created_at | FK Player. | Later |
| StoryFlag | player (FK), key, value | FK Player. Unique (player, key). | Later |
| CharacterClass (table) | code, name, per-level stat growth | FK from Player. | Later |

## `inventory` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| InventoryItem | player (FK), item (FK), quantity | FK Player, FK Item. Unique (player, item). | MVP |
| EquippedItem | player (FK), slot (FK EquipmentSlotType), item (FK Item) | FK Player, EquipmentSlotType, Item. Unique (player, slot). | MVP |
| Wallet | player (1-1), gold | One-to-one Player. | MVP |
| GoldTransaction | player (FK), amount, reason, created_at | FK Player. | Later |

## `combat` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| AttackType | code, name, resource_used (stamina/mana/none), cost, power_formula_key | Referenced by BattleLog. | MVP |
| Battle | player (FK), enemy (FK NPC), location (FK, nullable), status (active/won/lost/fled), enemy_current_health, started_at, ended_at, xp_gained, gold_gained | FK Player, NPC, Location. | MVP |
| BattleLog | battle (FK), turn_number, actor (player/enemy), attack_type (FK), damage, resource_spent, note, created_at | FK Battle, AttackType. | MVP |
| EnemyDrop | enemy (FK NPC), item (FK Item), drop_chance, min_qty, max_qty | FK NPC, FK Item. | MVP |
| EnemySpawn | enemy (FK NPC), location (FK), weight, min_player_level | FK NPC, FK Location. | Later |
| BattleParticipant | battle (FK), npc (FK, nullable), player (FK, nullable), side, current_health/stamina/mana | FK Battle, NPC, Player. | Later |

## `town` — spreadsheet candidate

| Suggested entity or helper | Proposed key fields | Proposed relationships | Workbook phase |
|---|---|---|---|
| Building | name, building_type (residence/business), location (FK), shop (FK, nullable), resident (FK NPC, nullable) | FK Location, Shop, NPC. | MVP |
| BuildingRequirement | building (FK), item (FK), quantity | FK Building, FK Item. | MVP |
| PlayerBuilding | player (FK), building (FK), status (ruined/in_progress/built), progress, completed_at | FK Player, Building. Unique (player, building). | MVP |
| GatherLog | player (FK), material (FK Item), amount, location (FK, nullable), created_at | FK Player, Item, Location. | Later |
| CraftingLog | player (FK), recipe (FK), quantity, created_at | FK Player, items.Recipe. | Later |
| UnlockRule | key, required_building (FK), description | FK Building. | Later |

## Next actions

Before accepting any entity: establish what game state it represents, whether it is per-player or shared catalog data, exactly one owning app, required fields and relationships, and whether history is needed for analytics. Check redundant state (e.g. gold or won/lost counters), and do not add framework-specific constructs prematurely.

## Audit note (2026-11-15)

No models or migrations were included under `django/` in the uploaded project archive. Do **not** treat previously discussed `Player`, item, crafting, or inventory entities as already implemented in this snapshot. A current local copy may differ. No candidate model is approved for implementation merely because it was discussed.

## Phase 2A — additive foundation (2026-11-15)

Authorized as a small implementation milestone: `Legacy`, `Character`, `Playthrough` in the existing `django/game` app. See `09-decisions-log.md` for gameplay and migration decisions. `Legacy` holds the *identity* of one continuous story, not serialized memories. `Character` holds personal identity (`name`, `kind`). `Playthrough` references a Legacy and a playable Character, optionally a predecessor, with a transition type and active/historical status. New Life records whether the original person returns or a new successor person is created. Full world, memory and inventory behavior is deferred.

Validation: Initial playthrough has no predecessor; transitioned playthrough has a predecessor from the same Legacy. Regression and same-person New Life keep Character. Successor New Life changes Character. A conditional unique constraint permits at most one active Playthrough per Legacy. These transitions are *structural modeling*, not implemented death gameplay. Validation uses `full_clean()` and does not automatically run for bare ORM `save()`; constraints at database level are limited to the single-active rule.

**Existing Player / GameSave:** Unchanged, no data backfill. The model bridge from existing Player to Character, and any reassignment of saved state to Playthrough, need a later approved migration. Do not assume new data structures are populated by the existing APIs.
