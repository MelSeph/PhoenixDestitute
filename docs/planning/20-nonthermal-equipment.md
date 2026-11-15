# Phase 2M — Explicitly nonthermal equipment

## Authorization and behavior

After Phase 2L, the user approved the proposed explicit “no ordinary thermal effects” declaration with “Yes”. The approved behavior distinguishes intentionally nonthermal equipment from missing configuration and permits its thermal enchantments to contribute normally. This increment implements that declaration, calculator behavior, revision metadata, and tests. No automatic classification, frontend changes, or commit/push is included.

## Step-by-step Django explanation

1. `EquipmentDefinition.no_ordinary_thermal_effects` is a boolean defaulting to false. It belongs to the shared backend definition; a weapon/item name or missing coverage rows never sets it automatically. Existing instance identities/properties are untouched.
2. An explicitly nonthermal definition has **no ordinary thermal coverage rows**. It provides no ordinary warmth, cooling, or cooling blockage, regardless of occupied equipment positions. It may still have other, nonthermal equipment properties.
3. `calculate_item_thermal` returns `configured: true` with an empty regional contribution list for this explicit declaration. The item still needs valid positive durability and a matching equipment definition. The flag cannot make destroyed, unidentified, or invalid equipment usable.
4. Outfit calculation can therefore finish when a fully configured garment is worn alongside explicitly nonthermal equipment. Nonthermal equipment creates no inferred thermal regions and does not form an ordinary blocking layer. Definitions without either regional data or the declaration remain unconfigured, preserving previous diagnostics.
5. Instance-owned thermal enchantments remain separate. An explicitly nonthermal item can provide full-strength magical warmth/cooling to its declared target regions, including regions outside any physical coverage. Source wear/destruction, ownership, and equipped-state rules remain unchanged.

| Declaration | Ordinary coverage | Interpretation |
|---|---|---|
| False | Missing | Unconfigured, as before |
| False | Present | Use explicit regional data; layering completeness rules still apply |
| True | Missing | Known to have no ordinary thermal effects |
| True | Present | Contradictory configuration; reject rather than discard data |

## Safety and compatibility

- Model validation rejects declaring a definition nonthermal while it has coverage and rejects coverage rows referencing a declared nonthermal definition. Validation queries current database data so cached related objects do not hide conflicts.
- Cross-row consistency is not a database check: bare ORM writes can bypass `full_clean()`. The calculator also detects contradictions and fails without deleting or ignoring coverage. Even zero-rating coverage is not silently discarded, because its breathability/order could still affect other items.
- Inventory reads expose `no_ordinary_thermal_effects` in definition metadata. The field participates in inventory revision hashes, so declaration changes invalidate pending moves/equips.
- Definition metadata in full-payload browser saves is read-only; it cannot toggle this backend field. No new public catalog editing endpoint is introduced.
- Raw legacy warmth/enchantment properties are neither parsed nor modified. No thermal/enchantment records are synthesized by a read or by the declaration.

## Migration and verification

Migration `0015_explicit_nonthermal_equipment` adds the boolean with false for existing definitions. It does not classify anything as nonthermal, delete coverage, alter item properties, or convert saves. Backup before local migration: `django/db.phase2m-backup.sqlite3`. Migration 0015 applied locally; `showmigrations game` confirms 0001–0015 applied.

Fifteen new tests cover known-empty versus unknown configuration, no automatic adoption/classification, enchantment effects and destruction, lack of ordinary blockage, conflict rejection including zero-rating coverage, cached validation, condition validation, read metadata/staleness, browser metadata isolation, and preservation of properties/data.

Final validation: **214 tests passed, none skipped** (199 previous + 15 new), including existing headless Chromium checks. `check` reported no issues and `makemigrations --check --dry-run` reported no changes. No weather/scoring, frontend, or `legacy_game/` changes. No commit or push performed.
