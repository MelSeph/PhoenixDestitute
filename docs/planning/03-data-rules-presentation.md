# Data, rules and presentation — provisional classification

**Data** means values/definitions that might be looked up or persisted; **rules** calculate outcomes or change state; **presentation** shows values and receives input. A single existing file may contain more than one category.

| Observed example | Category | Source | Notes |
|---|---|---|---|
| Player identity/stats and class/gender bonus values | Data + rules | `js/player.js` | Definitions and direct stat mutations are mixed. |
| Enemy stats and drop quantities | Data | `js/enemies.js` | Enemy selection also involves rules. |
| Equipment and potion attributes | Data | `js/equipment.js`, `js/potions.js` | Catalog candidates, not yet database models. |
| Turn order, attacks, damage, potion effects, battle outcomes | Rules | `js/battle.js` | Reads and mutates player/enemy state. |
| Shop catalog, purchases/sales and costs | Data + rules | `js/shop.js` | Numbered purchasing functions suggest repeated logic, not automatically separate tables. |
| Rebuilding requirements/progress/rewards | Data + rules | `js/building.js` | Building state and gameplay checks share a file. |
| Gathering resources and counters | Data + rules | `js/material.js` | Distinguish resource definitions from player-owned quantities later. |
| Title case and number abbreviations | Presentation/formatting | `js/textconversion.js`, `js/numberconversion.js` | Not good reasons for backend tables. |
| Display updates | Presentation | `js/updateplayer.js`, `js/updateenemy.js`, `js/updateshop.js`, `js/updatebuildings.js`, `js/updatepotions.js` | Mostly DOM population. |
| Menus, unlock flags and visibility | Presentation + possible rules | `js/open_and_close.js` | **Open question:** which flags are gameplay progression and which are UI state only? |

These categories guide **discussion**, not an automatic translation from each JavaScript file into one backend app. Do not assume file names determine module boundaries.
