# App (module) dependencies — not yet decided

The spreadsheet proposes a one-directional dependency sequence from `core` through `items`, `world`, `npcs`, `players`, `inventory`, and finally `shops`/`combat`/`town`. This is a **hypothesis to test**, not a verified dependency graph.

Questions for interview: Could a catalog remain independent of its buyers? Should a shop depend on inventory or coordinate through a higher-level operation? Where could circular imports appear between player, combat, world, and building progress? Keep dependency arrows distinct from database foreign-key relationships.

**Validation status:** No cyclic-dependency check can be claimed until app ownership and edges are approved.
