# Game overview — observations, not backend design

## Source and experience

`legacy_game/index.html` names the game Phoenix Destitute and supplies a command-driven journey panel plus menus for Stats, Inventory, Shop, Battle, Gathering, Rebuilding, and Production. The actual state/rules are distributed across `legacy_game/js/*.js`.

## Observed player journey (partial trace)

1. `main.js` begins with a `playerInfo.area` state such as `Pre-Start`, then progresses through `Gender Assignment`, `Set Name`, `Set Class`, and `Start`; `player.js` applies gender/class stat adjustments.
2. `main.js` routes to `Battle`; `enemies.js` defines enemy information and the available Endora enemy selection, while `battle.js` resolves attacks, turn-taking, potions and consequences.
3. A subsequent `Post-Battle-Reprieve` branch can reach `City Gates` (`main.js`). This is **not** a claim that every branch or ending has been fully traced.
4. Shop, gathering, rebuilding and production systems appear in the page and their corresponding scripts (`shop.js`, `material.js`, `building.js`, `endorahiddenmenu.js`). Visibility and unlock controls are managed partly by `open_and_close.js`.

## Existing state/data examples

- **Player:** `playerInfo`, `playerStats`, class/gender values (`player.js`).
- **Enemies/combat:** enemy templates and `enemyInfo`/`enemyStats`; battle state, HP/stamina/mana and outcomes (`enemies.js`, `battle.js`).
- **Items:** equipment definitions (`equipment.js`), potions (`potions.js`), shop item/price/quantity definitions (`shop.js`).
- **Town/resources:** material counters and raw materials (`material.js`); building owners, requirements, progress and rewards (`building.js`); production actions (`endorahiddenmenu.js`).

## Important limitations

This file describes identifiable flows from the source; it is not a full playthrough or validated state-transition diagram. Actual save/persistence behavior, every possible progression branch, gating, reward, and interaction still require a careful trace. Changelog statements may describe intent or history rather than guaranteed present behavior.
