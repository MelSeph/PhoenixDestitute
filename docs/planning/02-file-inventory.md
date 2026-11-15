# Existing source file inventory

Source: supplied `PhoenixDestitute.zip`. `Reads / writes / decides` is a **first-pass responsibility summary**, not a statement that every variable dependency was exhaustively traced. P = presentation, R = rule, D = reference/mutable data; labels can overlap.

## Original legacy game

| File | Reads / references | Writes / changes | Decides or provides | Class |
|---|---|---|---|---|
| `legacy_game/index.html` | Player command/input, JavaScript-updated state and DOM bindings. | Defines screens, input controls, stats, equipment, shop, resource gathering, rebuilding, production and combat text areas. | Page markup and handlers; some inline event calls. | P |
| `legacy_game/css/reset.css` | Browser element styling. | Resets browser default styles. | Page style reset only. | P |
| `legacy_game/css/main.css` | HTML class/id selectors. | Sets shared layout and component styles. | Presentation only. | P |
| `legacy_game/css/index.css` | HTML class/id selectors. | Styles the game page, menus and panels. | Presentation only. | P |
| `legacy_game/flow/JQuery.js` | Library APIs. | Bundled jQuery library copy in flow/. | Generic library behavior, not game rules. | P |
| `legacy_game/flow/normalize.css` | Browser element styles. | Bundled normalization stylesheet. | Cross-browser presentation. | P |
| `legacy_game/js/jquery.js` | DOM and library APIs. | Bundled jQuery library referenced by index.html. | Generic library behavior, not game rules. | P |
| `legacy_game/js/main.js` | playerInfo.area, user input, class/name selection, battle and city entry. | Main command/state-driven progression loop; sets a displayed version. | Area transitions and main narrative branch choices. | R/P |
| `legacy_game/js/player.js` | playerInfo/playerStats, gender and class definitions. | Player information/stats, gender and class bonuses, identity setup. | Creation choices and stat changes. | D/R |
| `legacy_game/js/updateplayer.js` | playerStats, playerInfo and other state objects. | Synchronizes player, class, materials, crafting and cheat values to HTML. | DOM text updates, not authoritative game rules. | P |
| `legacy_game/js/enemies.js` | Enemy stats, enemy selection array. | Defines enemy templates and selects an Endora-area enemy. | Enemy selection and base drop/XP-related attributes. | D/R |
| `legacy_game/js/updateenemy.js` | enemyInfo, enemyStats. | Displays current enemy information/stats. | DOM text updates. | P |
| `legacy_game/js/potions.js` | Potion names/effects/prices/quantities. | Defines health/stamina/mana potion data. | Reference data initialization. | D |
| `legacy_game/js/battle.js` | playerStats, enemy stats, battle flags and combat inputs. | Battle state, turn actions, attack outcomes, potion use and post-battle outcomes. | Turn order, damage/resources, win/loss and state changes. | R/D |
| `legacy_game/js/material.js` | Material values, gather counters, stone/wood/sand state. | Defines and updates resources gathered by the player. | Resource collection and gathered totals. | D/R |
| `legacy_game/js/building.js` | Building owners, costs, required resources and player resources. | Defines buildings and progress toward their rebuilding. | Contribution/rebuilding progress and rewards. | D/R |
| `legacy_game/js/levelup.js` | playerStats.experience and level. | Experience threshold and level-up calculation. | When the player levels and what changes. | R |
| `legacy_game/js/shop.js` | shop data, item catalog globals, equipment and player gold/stats. | Defines shop data plus item-purchase and sale actions. | Purchasing/selling, price and quantity changes. | D/R |
| `legacy_game/js/creation.js` | itemCreated, equippedItems. | Tracks/inspects crafted equipment. | Crafted/equipped item detection. | D/R |
| `legacy_game/js/cheats.js` | Player, material, potion and building state. | Defines development cheats for gold, resources, stats, potions, drops and rebuilding. | Direct cheat-triggered mutations. | R |
| `legacy_game/js/endorahiddenmenu.js` | Production materials and recipe-style requirements. | Crafting/production operations unlocked in Endora rebuilding context. | Smelting, condensing, tanning, spinning and item creation. | D/R |
| `legacy_game/js/updateshop.js` | shopKeeper, shopInfo, shopStats. | Synchronizes shopkeeper/shop data to HTML. | DOM updates. | P |
| `legacy_game/js/updatebuildings.js` | Various buildingInfo/buildingStats objects. | Synchronizes rebuilding data to HTML. | DOM updates. | P |
| `legacy_game/js/open_and_close.js` | Menu state and isShop/Gather/Rebuild/ProductionUnlocked booleans. | Menu visibility, interactions, unlock flags and enabling/disabling controls. | Display toggles and some gatekeeping logic requiring classification. | P/R |
| `legacy_game/js/equipment.js` | Equipment definitions, slots and stat effects. | Defines equipment prototypes/catalog values and equipped-item handling. | Item/equipment stats and availability, possibly equip behavior. | D/R |
| `legacy_game/js/randomnumber.js` | start/range values supplied by caller. | Random number helper for game calculations. | Random integer generation. | R |
| `legacy_game/js/numberconversion.js` | Numeric input. | Number abbreviations and display formatting. | Text representation, no game-state mutation. | P |
| `legacy_game/js/textconversion.js` | Text input. | Title case conversion for displayed or entered text. | String normalization for display; context of use still matters. | P |
| `legacy_game/js/updatepotions.js` | potionStats. | Synchronizes potion statistics to HTML. | DOM updates; not loaded directly in index.html. | P |
| `legacy_game/v. 0.0.20.txt` | Developer notes. | Historical change notes and open TODOs. | Documents intended and changed behavior; not executable. | Docs |

## Script loading verification

`index.html` loads the following JavaScript files in this order: `js/jquery.js`, `js/numberconversion.js`, `js/textconversion.js`, `js/main.js`, `js/player.js`, `js/updateplayer.js`, `js/enemies.js`, `js/updateenemy.js`, `js/potions.js`, `js/battle.js`, `js/material.js`, `js/building.js`, `js/levelup.js`, `js/shop.js`, `js/creation.js`, `js/cheats.js`, `js/endorahiddenmenu.js`, `js/updateshop.js`, `js/updatebuildings.js`, `js/open_and_close.js`, `js/equipment.js`, `js/randomnumber.js`.

`js/updatepotions.js` exists but is **not** present among these `<script src>` tags. `flow/JQuery.js` is likewise not loaded here; `js/jquery.js` is.

## Other repository entries in the ZIP

The following Django files are **existing work, not legacy-game source**. They are inventoried for completeness but are not evidence that the proposed backend must use Django.

- `django/.gitignore` — Version-control exclusions.
- `django/manage.py` — Django command-line entry.
- `django/phoenixdestitute/asgi.py` — ASGI bootstrap.
- `django/phoenixdestitute/settings.py` — Existing Django configuration.
- `django/phoenixdestitute/urls.py` — Existing routing configuration.
- `django/phoenixdestitute/wsgi.py` — WSGI bootstrap.
- `django/phoenixdestitute/__init__.py` — Python package marker.
- `django/phoenixdestitute/__pycache__/settings.cpython-313.pyc` — Generated Python bytecode cache (not source).
- `django/phoenixdestitute/__pycache__/urls.cpython-313.pyc` — Generated Python bytecode cache (not source).
- `django/phoenixdestitute/__pycache__/wsgi.cpython-313.pyc` — Generated Python bytecode cache (not source).
- `django/phoenixdestitute/__pycache__/__init__.cpython-313.pyc` — Generated Python bytecode cache (not source).
- `django/README.md` — Existing Django project notes.
- `django/requirements.txt` — Existing dependencies.
- `react/` — empty directory in the uploaded ZIP.

## Not yet validated

- Exhaustive per-symbol reads and writes for every game file.
- Runtime order/flow for every command and every menu button.
- Full correspondence between changelog entries and live game logic.
- All data values and who changes them (requires a source-level cross-reference).
