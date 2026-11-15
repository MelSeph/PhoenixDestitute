# Analytics questions — discussion starters, not requirements

The user explicitly wants database and analytics design practice. Potential questions to evaluate, subject to the actual game's mechanics and future approval:

- Which enemies are fought, and how often are those battles won or lost? (`js/battle.js`, `js/enemies.js`)
- How many turns or consumables does a battle use? (`js/battle.js`, `js/potions.js`)
- Which equipment is bought/sold or equipped most often? (`js/shop.js`, `js/equipment.js`)
- How do resource-gathering actions and rebuilding progress change over time? (`js/material.js`, `js/building.js`)
- How often do players level up, and after which events? (`js/levelup.js`, `js/player.js`)

**Open decision:** Persist every event, a few targeted ledgers (e.g. battles and purchases), or only current state? Event logging increases analytical power and also work/storage complexity. Avoid logging the same event twice unless there is a clear purpose. Nothing in this list authorizes creating tables yet.
