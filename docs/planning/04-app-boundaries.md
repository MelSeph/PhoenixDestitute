# App (module) boundaries — awaiting interview

**No boundaries approved.** The supplied spreadsheet suggests `core`, `items`, `world`, `npcs`, `shops`, `players`, `inventory`, `combat`, and `town`. These are **candidate names only**, not nine adopted apps.

Questions to decide with the user: What is the smallest useful starting split? Which app owns each catalog versus player state? Which divisions separate independently meaningful concerns rather than just mirroring JavaScript files? Can `town` and `world`, or `shops` and `inventory`, be combined at first? Would `core` be a plain helper package rather than a database-bearing app?

We will document each decision's scope, evidence, alternatives, reasoning, date, and explicit user approval here **after** the appropriate interview round.

## Audit note (2026-11-15)

The archived Django scaffold references a monolithic `game` application that is **absent from the ZIP**. This does **not** establish a final app/module boundary and does not imply we should recreate `game` as-is. Reconcile the current working tree and approved gameplay concepts before deciding any split.
