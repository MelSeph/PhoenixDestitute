# Phase 2L — Thermal enchantment contributions

## Approved scope

The user approved the reviewed Phase 2L plan with “yes”: instance-owned regional enchantment contributions, full-strength magical subtotals, combined ordinary/magical results with incomplete-data diagnostics, inventory revision/save protection, death-time copies and Regression validation, and tests. Commit/push remain separately authorized. No frontend, weather, scoring, application/repair rolls, or public enchantment mutation endpoint is included.

The agreed gameplay rules remain: positive-durability enchantments retain full strength; magical cooling bypasses ordinary breathability restrictions; magical target regions are explicit and independent of physical coverage; contributions affecting the same region add; destruction ends the effects.

## Step-by-step Django explanation

1. **Contributions belong to an instance.** `ItemThermalEnchantment.item` points to an existing `InventoryItem` with `PROTECT`. Each row has one explicit target region and nonnegative decimal warmth/cooling, using the existing eight-region vocabulary and four-decimal storage precision. Multiple rows may target the same item and region: each is an additive contribution, with its own primary key. This is a contribution foundation, not a full named-enchantment/recipe system.
2. **Regions do not depend on fabric.** A garment whose ordinary coverage is upper torso may have magical contributions to feet, or explicit rows for all eight regions. Nothing infers targets or divides one bonus among them.
3. **Validate sources and values.** Database checks enforce region codes/nonnegative values. Model validation checks equipment kind/quantity and, for new rows, an active usable source with valid positive durability. Active-life validation queries the current database state rather than trusting a cached Playthrough object. As with existing models, bare ORM `save()`/`create()` does not automatically call `full_clean()`; no public creation endpoint bypasses a service here.
4. **Retain the ordinary contract.** Phase 2K `calculate_outfit_thermal` remains ordinary-only. New internal `calculate_outfit_thermal_effects(player_id=...)` calls it and returns the original result under `ordinary`, separate `enchantment_regions`, and combined regional `regions` when ordinary configuration is complete. All calculations use exact fractions.
5. **Magical effects are added after ventilation.** Only contribution rows whose source item is equipped in the active life are counted. Source durability must be valid and positive, but it does not multiply magical strength. Outer-layer breathability never reduces magical cooling. Multi-position sources count each contribution once, not once per position reservation. Carried, stored, displaced, destroyed, foreign-life, and historical sources do not contribute.
6. **Keep missing data visible.** If ordinary configuration is incomplete, the combined result remains `configured: false`, keeps its ordinary diagnostics, and returns no combined regional totals. Explicit magical subtotals remain available separately. When ordinary data is complete, a magical-only target region has no ordinary contribution, and the combined total includes the explicit magical values there. No unknown ordinary rating is silently replaced with zero.
7. **Use only structured data.** Existing opaque `properties.enchantment` and other instance properties remain unchanged and are not parsed, converted, or used to guess thermal bonuses. Zero explicit rows means no structured thermal contributions. The combined calculator reports only the structured system's effects; it does not claim to interpret legacy enchantment formats.

For example, ordinary cooling of 10 blocked by airtight armor contributes zero ordinary cooling. An equipped enchantment providing 5 cooling to that region still contributes the full 5, even at low positive durability. Other enchantments add to that subtotal. At source destruction the contribution stops, although its row is retained for history.

## Inventory, save, and identity protection

`InventoryItem.thermal_enchantment_data()` provides one canonical representation: an ordered list of contribution IDs, regions, and decimal-string ratings. Inventory reads and the compatibility save serializer include it as `thermal_enchantments`. IDs/values participate in inventory revision hashes, so adding, editing, replacing, or deleting contributions invalidates pending inventory commands.

The browser save API does not create/update contribution rows. If a payload supplies contribution metadata, it must match the backend records; forged or changed values are rejected. Legacy clients may omit this read-only metadata, in which case canonical serialization restores it without creating duplicates. An instance with explicit contributions is protected from browser placement/property edits and removal even if it has not been linked to an equipment definition. Existing Phase 2I protection still applies to all explicitly definition-linked gear.

Repeated saves/reads reuse contribution identities. Destroyed items retain their rows solely for history; they are absent from usable inventory and the magical calculation.

## Death snapshots and Regression

`DeathSnapshotEntry.thermal_enchantments` stores a copied canonical list at death, alongside the existing copied quantity/properties. Regression requires the current carried contribution IDs/regions/values to match that frozen list. Changes, additions, and deletions after capture make the snapshot stale and abort the transition unchanged.

Successful Regression moves the original carried InventoryItem. Its child contributions keep their IDs and item foreign key, so they follow that same instance into the new life without cloning. Equipped/stored possessions remain in the old life. Snapshot copies and archived save JSON are not rewritten by transfer or future contribution edits.

This remains a backend-only lifecycle contract. Future enchantment-writing services must coordinate through the same Player lock and death-freeze policy; direct concurrent ORM writes are not globally prevented by these models. No new death/combat UI is introduced.

## Migration and verification

`0014_thermal_enchantments` creates the contribution table and adds the snapshot-copy JSON field. Existing snapshot entries get an empty list, representing no structured contribution records before this new table existed. There is no conversion of opaque enchantment properties or automatic creation of bonuses. Backup created before local migration: `django/db.phase2l-backup.sqlite3`. Migration 0014 applied locally; `showmigrations game` confirms 0001–0014 applied.

Twenty-five new tests cover full-strength/bypass/additive rules, independent/all-eight targeting, exact decimals, multi-position sources, wear/destruction, carried/stored/displaced/history exclusions, incomplete ordinary configuration, read-only behavior, metadata/revisions, repeated-save identity, browser protection, immutable death copies, stale additions/edits/deletions, Regression IDs, model/database validation, and cached-life validation.

Final validation: **199 tests passed, none skipped** (174 previous + 25 new), including existing headless Chromium checks. `check` reported no issues; `makemigrations --check --dry-run` reported no changes. No frontend or `legacy_game/` changes. No commit or push performed.
