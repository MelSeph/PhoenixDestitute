# Phase 2I — Equipment definitions and placement foundation

## Approved scope

The user approved this implementation plan with “yes”: shared equipment definitions, relational position reservations, internal manual equip/unequip services, atomic movement of displaced instances into carried inventory, reservation release on destruction, compatibility-save protection, and automated tests. Commit/push remain separately authorized. No frontend or `legacy_game/` changes.

This is **placement only**. It does not expose public equip endpoints, calculate character stats, choose automatic upgrades, implement temperature effects, or roll repairs. The game setting from Phase 2H remains a stored preference rather than an active adaptation engine.

## Understanding the Django relationships

| Model | Responsibility | Example |
|---|---|---|
| `EquipmentDefinition` | Shared equipment key | One backend key for a kind of two-handed weapon |
| `EquipmentDefinitionPosition` | All positions that definition requires | Main hand and off hand, two rows |
| `InventoryItem` | One owned instance with identity, properties, durability, and placement | One particular upgraded weapon |
| `EquippedPosition` | A position actually reserved by that instance in one life | Two rows pointing to the same equipped weapon |

The optional `InventoryItem.equipment_definition` foreign key is the explicit adoption boundary. Its definition key must match the existing instance key. NULL preserves legacy/backend items without inventing a classification. Multiple instances can share one definition while keeping separate identities and properties.

The initial position vocabulary includes only the agreed layers and hands: upper/lower undergarment, upper/lower clothing, torso/leg armor, hosiery, footwear, main hand, and off hand. No left/right sock positions. Headwear, gloves, waist gear, accessories, and further layers still need their own decisions; they are not silently inferred from the old game.

## Placement flow

1. The trusted backend caller passes an authorized `player_id`, expected `playthrough_id`, current inventory `revision`, and `item_id` to `equip_item` or `unequip_item`. Future HTTP endpoints must obtain the Player from session ownership rather than browser-supplied owner IDs.
2. The transaction locks the Player and verifies the active life and revision. The inventory revision now includes definition metadata and actual reservations, so definition/reservation changes invalidate stale requests as well as item/save changes.
3. The target must be one equipment instance with an explicitly matching definition, a nonempty set of valid positions, and positive valid durability. Equipping requires it to be carried; abstract stored items must be moved into carried inventory first. No default durability, score, or slot capacity is invented.
4. Existing equipped items must have complete reservations matching their definitions. Missing definitions, partially reserved items, and other inconsistent existing placements cause the operation to fail unchanged. Even unrelated new placement is refused if current legacy equipment makes occupancy ambiguous.
5. A manual equip is the player's explicit choice and does **not** require a higher score or the automatic-adaptation preference. Every conflicting instance is moved exactly once into a distinct carried slot, releasing all of its positions. The incoming item's former carried slot is available for reuse. Allocation uses the lowest free nonnegative slot; this is an implementation choice, not an inventory-capacity rule.
6. All incoming positions are reserved together. The database enforces unique positions within a life, unique positions per item, and valid position codes. Model validation additionally checks ownership/life, equipped state, and declared requirements. Full relationship invariants are service-enforced; direct ORM `save()` does not automatically call `full_clean()`.
7. Unequipping releases the entire item's reservations and moves the same instance into one free carried slot. Re-equipping an already equipped, consistently reserved instance is a no-op. Invalid calls and write failures roll back the entire operation, including reservations, displaced items, and save writes.
8. Neither operation edits quantity, durability, upgrades, enchantments, or other instance properties. No character-stat field is recalculated or modified in this placement milestone.

Inventory reads now include each item's explicit `equipment_definition` metadata (or null) and a top-level `equipped_positions` list. The existing inventory read endpoint exposes these additively; no new public equip endpoint is registered.

## Compatibility, destruction, and life history

- Existing versioned saves and the `GameSave` mirror refresh atomically after placement; browser revision rotation rejects stale payloads. Legacy equipped-name and cached-stat fields are not rewritten to pretend they implement the new slot scheme. Unsaved lives remain unsaved.
- Once an instance is explicitly definition-linked, the browser save bridge cannot move, edit its instance properties, or omit it. New browser instances cannot claim a registered definition key. Lives with definition-linked equipment cannot introduce new unreserved legacy-equipped items through the browser bridge. Old, unadopted records otherwise retain their previous compatibility behavior.
- Destruction removes all reservations before marking the item destroyed. Failure to refresh saves rolls those removals back. The history-only identity and death snapshot copies remain intact.
- Regression transfers carried instances without cloning them; these have no equipped reservations. Equipped items and their reservations remain in the historical life. The new life can equip a transferred defined instance without modifying old reservations or archived JSON.
- Definition edits are not exposed here. Treat requirements of in-use definitions as stable: direct changes that disagree with existing equipped reservations cause later placement to fail instead of silently reinterpreting occupancy. No adoption/editing API or automatic legacy backfill is provided.
- SQLite does not provide PostgreSQL-style row locks. Transactions, database uniqueness, and revision checks are tested; concurrent multi-process load testing remains outside this phase.

## Migration and verification

Migration `0011_equipment_definitions_positions` adds three tables and the nullable definition link. It creates no gameplay catalog or reservations and converts/deletes no existing items or saves. Backup created before local migration: `django/db.phase2i-backup.sqlite3`.

Twenty-three new tests cover layers, multi-position garments, two-handed swaps, lower-score manual choices, no-op equip, whole-item unequip, stored/unknown/invalid equipment, ownership and stale lives, definition changes, database constraints, destruction, rollback of swaps/unequips/destruction, browser write protection, and historical reservations after Regression.

Final local checks: **136 Django tests passed, none skipped**, including existing headless browser checks; `check` reported no issues and `makemigrations --check --dry-run` reported no changes. Migration 0011 applied locally, and `showmigrations game` confirms 0001–0011 applied. No commit or push performed.
