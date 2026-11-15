# Phase 2K — Ordinary outfit thermal calculation

## Approved scope

The user approved the reviewed Phase 2K plan with “yes”: optional regional breathability/layer-order data, internal read-only ordinary outfit calculations, incomplete-configuration diagnostics, inventory revision integration, and tests. This implements the agreed thermal layering formulas without adding weather effects, enchantment totals, automatic scoring, character-stat writes, or frontend controls. Commit/push remain separately authorized.

## Definition data

`EquipmentThermalCoverage` now has two optional fields:

- `breathability`: a decimal percentage from 0 through 100, stored with four fractional places. NULL means unconfigured, not airtight or fully breathable. A database constraint enforces the percentage range; model validation also rejects nonfinite values.
- `layer_order`: a nonnegative integer, with higher values farther outside for that region. Zero is valid; NULL means unconfigured. Equal orders are allowed and do not block one another. These values are explicit definition data rather than inferred from weight, item names, or equipment positions.

Each region on one garment may have its own order. A long coat can therefore be outside trousers over the legs even while occupying an upper-clothing equipment position. The existing position and reservation rules are unchanged.

Inventory metadata exposes both fields (`breathability` as a decimal string or null, `layer_order` as an integer or null). Both participate in revision hashes; changing either invalidates pending inventory moves and equipment requests. The Phase 2J API serialization test was extended to assert the two additive null fields alongside the existing unchanged ratings.

## Step-by-step calculation

1. The internal service `calculate_outfit_thermal(player_id=...)` locks the Player and reads the active life's equipped instances. Carried, stored, destroyed, other-player, and historical equipment are not included. Multi-position instances contribute once, not once per reservation.
2. The existing per-item calculator supplies each covered region's ordinary warmth/cooling after the agreed durability scaling. It now also returns `base_breathability`, `effective_breathability`, and `layer_order`. Its `configured` flag still describes ordinary thermal rating configuration: missing layering data does not break the Phase 2J item calculation.
3. For positive durability, with condition multiplier `f` and base breathability fraction `b`, effective breathability is `1 - (1 - b) * f`. Thus an airtight item at half durability passes 25%, and a base-80%-breathable item at half durability passes 85%. Destroyed items are removed as layers entirely.
4. For each region, ordinary warmth is the sum of each equipped item's condition-adjusted rating. Breathability does not further reduce this sum.
5. For each garment's regional ordinary cooling, multiply by the effective breathability of every overlapping garment whose regional order is strictly higher. Equal-order layers, inner layers, nonoverlapping regions, and the garment's own breathability do not suppress that contribution.
6. Sum the resulting cooling contributions within the region. All arithmetic uses exact fractions. No body-wide weighting, cap, environmental penalty, or rounding rule is introduced.
7. Fully configured calculations validate current relational equipment reservations using the same consistency checks as manual placement. Invalid reservations or invalid durability fail rather than produce plausible-looking totals.

Example at full durability in one region:

| Layer | Warmth | Cooling | Breathability | Order | Cooling after outer layers |
|---|---:|---:|---:|---:|---:|
| Undergarment | 2 | 10 | 0% | 0 | 10 × 80% × 50% = 4 |
| Clothing | 3 | 6 | 80% | 1 | 6 × 50% = 3 |
| Armor | 5 | 2 | 50% | 2 | 2 |

Regional totals: 10 ordinary warmth and 9 ordinary cooling. The undergarment's own 0% breathability does not suppress its own cooling.

## Results and missing configuration

The internal result contains the active `playthrough_id`, `configured`, `regions`, and `unconfigured`. Complete regional results contain `ordinary_warmth`, `ordinary_cooling`, and per-item contribution details, including the outer transmission multiplier. These exact-fraction values are an internal contract, not a new JSON endpoint.

If any equipped item lacks a definition/thermal coverage, or any coverage row lacks breathability/order, `configured` is false, `regions` is empty, and `unconfigured` identifies the item, region when known, and missing fields. No partial totals are returned. An item intended to be nonthermal is not silently exempted: explicit nonthermal applicability is a future catalog decision. A correctly empty outfit is a known empty result with no inferred eight-region rating list.

Ordinary zero ratings are still real configuration and do not exempt a layer from blocking. The calculator never interprets opaque enchantment properties. Enchantment strength remains governed by the existing full-strength-until-destruction rule, but enchantment thermal totals require a separately defined data contract.

Neither calculator writes item properties, coverage, reservations, Player stats, death snapshots, or save JSON. Repeated reads do not compound wear, mutate enchantments, or trigger automatic adaptation.

## Migration and verification

Migration `0013_thermal_layering` adds nullable fields and a percentage constraint. It sets no default breathability/order, assigns no material parameters, and converts no existing items or saves. Backup created before local migration: `django/db.phase2k-backup.sqlite3`. Migration 0013 applied locally; `showmigrations game` confirms 0001–0013 applied.

Twenty-two new tests cover hand-calculated three-layer totals, equal orders, fully/partially/impermeable layers, wear and destruction, independent regional ordering/overlap, excluded carried/stored gear, single contribution for multi-position instances, missing configuration, empty outfits, reservation/durability errors, metadata/revisions, model/database validation, read-only behavior, enchantment preservation, and player/life isolation.

Final validation: **174 tests passed, none skipped** (152 previous + 22 new), including existing headless Chromium checks. `check` reported no issues; `makemigrations --check --dry-run` reported no changes. No public thermal endpoint, frontend, or `legacy_game/` changes. No commit or push performed.
