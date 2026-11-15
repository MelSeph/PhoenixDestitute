# Phase 2J — Thermal definition foundation

## Approved scope

The user approved the reviewed Phase 2J implementation plan with “yes”: the eight agreed regions; per-definition, per-region nonnegative decimal warmth/cooling; inventory read/revision integration; an internal per-item ordinary thermal calculator using the agreed durability curve; and automated tests. Existing instance properties and saves are preserved. Commit/push remain separately authorized.

This phase does not calculate outfit totals, outer-armor suppression, environmental/temperature effects, thermal enchantment totals, carrying weight, physical combat stats, or automatic scores. Those need their remaining rules/data contracts. No frontend changes or new public calculator endpoint are included.

## Step-by-step Django explanation

1. **A shared definition owns regional data.** `EquipmentThermalCoverage.definition` is a foreign key to `EquipmentDefinition`. Each row describes one region: head, neck, upper torso, lower torso, arms, hands, legs, or feet. A unique constraint prevents duplicate rows for one definition/region. Region codes and nonnegative ratings also have database constraints.
2. **Coverage is independent of positions.** A garment may occupy only hosiery while having feet, legs, and lower-torso coverage rows. A footless variant simply has different explicitly declared coverage. Neither names nor occupied positions generate thermal regions. No left/right limb distinction is introduced.
3. **Both ratings must be supplied.** `warmth` and `cooling` are decimal fields, each storing up to 12 digits with four decimal places. This is storage precision, not a chosen gameplay scale or a temperature unit. The model validates finite, nonnegative values. No default ratings or sample catalog rows are created. A supplied zero is a valid configured rating; no coverage rows means unconfigured.
4. **Inventory reads expose the definition data.** `equipment_definition.thermal_coverage` is either null for unconfigured definitions or a region-ordered list such as `[{"region": "feet", "warmth": "4.0000", "cooling": "2.0000"}]`. Decimal strings preserve stored precision in JSON. No definition still has `equipment_definition: null`. The inventory revision includes these records, so changes invalidate pending moves/equips.
5. **Instances apply their own condition.** Internal `calculate_item_thermal(player_id=..., item_id=...)` authorizes the active-life scope using the existing Player-lock convention. It reads ordinary base ratings from the explicitly linked definition and current/max durability from the instance. Two instances sharing a definition can therefore have different effects.
6. **Calculation preserves originals.** Configured results include `base_warmth`, `base_cooling`, `ordinary_warmth`, and `ordinary_cooling` per region. Ordinary values use the exact agreed multiplier (full → 100%, half → 75%, approaching zero → 25%). Internally, base values are Decimal and effective values are Fraction, avoiding a new rounding rule. These internal results are not a JSON API contract.
7. **Unknown is not zero.** An unadopted item or definition without thermal coverage returns `configured: false` with an empty region list. Explicit zero rows return `configured: true`. Configured gear with missing/invalid durability fails instead of receiving invented defaults. Destroyed, foreign, historical, non-equipment, or mismatched-definition instances are rejected.
8. **Reads do not mutate gameplay.** Neither calculation nor metadata reads change instance properties, equipment reservations, stats, definitions, or save JSON. Opaque upgrades and enchantment properties are preserved and are not interpreted as thermal overrides. Enchantment bonuses remain full-strength under the agreed rule; this ordinary-only calculator does not combine them into a thermal total because that data contract is still undefined.

## Migration and compatibility

`0012_equipment_thermal_coverage` creates one table. It does not classify equipment, invent ratings, seed a catalog, convert instance properties, change existing saves, or alter placement rules. Backup created before local migration: `django/db.phase2j-backup.sqlite3`. Migration 0012 applied locally; `showmigrations game` confirms 0001–0012 applied.

The existing Phase 2I browser-write protections remain in force for explicitly adopted equipment. New read metadata is additive; no browser payload can edit the definition's thermal rows through the save API. Previous legacy property names are not automatically mapped into these ratings.

Layering's qualitative rules are recorded in `14-equipment-rules.md`: warmth increases with layering; heavy outer armor restricts ordinary cooling only in overlapping regions. This phase supplies data for that later calculation but chooses no layer ordering, numeric penalty, or weather threshold.

## Validation

Sixteen new tests cover all eight regions, position-independent coverage, distinct regional values, exact decimals/wear scaling, unconfigured versus zero, shared definitions with individual condition, read-only behavior, API serialization, stale requests after data edits, constraints, invalid input, ownership, destroyed/historical items, and definition mismatch.

Final full suite: **152 tests passed, none skipped**, including existing headless Chromium checks. `python manage.py check` reported no issues; `python manage.py makemigrations --check --dry-run` reported no changes. No frontend or `legacy_game/` edits. No commit or push performed.
