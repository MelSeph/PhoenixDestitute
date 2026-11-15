# Phase 2N — Read-only outfit thermal API

## Approved scope

The user approved the reviewed Phase 2N plan with “yes”: one session-scoped GET endpoint exposing the established ordinary/magical/combined calculator, exact fraction transport, incomplete-configuration diagnostics, ownership/read-isolation tests, and no model/save/frontend changes. Commit/push remain separately authorized.

## Step-by-step request flow

1. `GET /api/equipment/thermal/` is routed to `thermal_api.outfit_thermal` (URL name `api-equipment-thermal`). Django's GET-only decorator rejects unsupported methods.
2. The existing `_local_player` helper selects only the local Player from the browser session. Query parameters do not choose an owner or life. No session-selected Player means 404; account access remains unsupported with 403, consistent with the other local-game endpoints.
3. `calculate_outfit_thermal_effects` reads the current active life and applies the existing equipment, condition, ordinary layering, nonthermal-declaration, and enchantment rules. No rules or balances are added by the HTTP view.
4. A successful response is `{"success": true, "thermal": ...}`. The `thermal` object preserves `playthrough_id`, `configured`, the `ordinary` result/diagnostics, explicit `enchantment_regions`, and combined `regions` when complete.
5. `ThermalJSONEncoder` converts every nested Fraction into a numerator/denominator object using strings. This preserves exact values even when the fraction is nonterminating in decimal or its components exceed JavaScript's safe-integer range. Other values retain normal Django JSON behavior; flags stay booleans and identifiers keep their existing integer format.

For example, an arithmetic field is represented as:

```json
{"total_cooling": {"numerator": "3", "denominator": "2"}}
```

Whole-valued fractions still use the same shape (`"2"` / `"1"`), and zero is `"0"` / `"1"`. The endpoint introduces no rounding/display rule. Future presentation can format a value for display while backend calculations remain authoritative and exact.

## Response states

| State | HTTP behavior |
|---|---|
| Complete outfit | 200; configured true and exact component/combined results |
| Incomplete thermal data | 200; configured false, existing ordinary diagnostics, known explicit magical subtotals, no combined totals |
| Correctly empty, possibly unsaved active life | 200; known-empty results, no save creation |
| No local Player in session | 404 |
| Authenticated account access | 403; not implemented |
| No active life or invalid equipment/configuration | 409 with the service validation message |
| Unsupported HTTP method | 405 (subject to the existing CSRF middleware for unsafe requests) |

New unsaved lives do not fall back to predecessor equipment or compatibility JSON. The endpoint reads relational active-life equipment, not browser-supplied state or legacy cached stats. It does not create a Player, settings, save, definition, inventory item, enchantment, or snapshot.

The view exposes no equipment mutations, enchantment application, weather interpretation, scoring, or automatic adaptation. Existing write endpoints retain CSRF protection; this endpoint adds no write route and no exemption. No frontend/React integration is included.

## Validation

Fourteen new API tests cover exact ordinary/magical/nested/whole/nonterminating fractions, very large denominators, incomplete diagnostics, explicitly nonthermal gear, missing and isolated sessions, forged owner/life query parameters, unsupported accounts/methods, invalid-state conflicts, unsaved new-life behavior, and repeated GETs preserving gameplay and save tables.

Final full suite: **228 tests passed, none skipped** (214 previous + 14 new), including existing headless Chromium checks. `check` reported no issues and `makemigrations --check --dry-run` reported no changes. No migration or database update was required; migration 0015 remains the latest existing schema. No frontend or `legacy_game/` edits. No commit or push performed.
