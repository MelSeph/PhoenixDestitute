# Open questions and research uncertainties

## Interview round 1 — begin with evidence, not an architecture commitment

1. Which game-state values are shared definitions (e.g. equipment templates), and which are distinct values for each player (e.g. a player's equipped sword or materials)? How would two different players owning the same named item be represented?
2. Does a location represent a real game-world place, a story progression phase (`playerInfo.area`), a UI screen, or some combination? `main.js` uses values such as `Gender Assignment`, `Battle`, and `City Gates`; not all obviously describe geographical locations.
3. What are the minimum analytics questions worth making possible *first*, so that event logging is proportional to the hobby project?

We should debate options for each question, recommend one, ask the user to choose, and challenge the selected design with a concrete scenario before recording a conclusion.

## Research verification still needed

- Exhaustive reads/writes/decides for all game source files (02 is a first-pass inventory).
- Every game start-to-finish branch, menu unlock, quest/rebuilding condition, and state mutation.
- Whether any hidden state/save mechanism exists outside currently inspected scripts.
- Whether `updatepotions.js` is ever used indirectly; not directly referenced by HTML script loading.
- Alignment of the version label in `main.js` and the `v. 0.0.20.txt` changelog.
- Rebuilding behavior including the Raj House path, and whether the changelog documents intended vs implemented functionality.
- Consequences of treating existing `django/` as study material while intentionally leaving framework choice undecided.

## Immediate questions before a backend implementation checkpoint (2026-11-15)

1. Does the user's **current** local `django/` directory include the `game/` package, models, migrations and tests omitted from the uploaded ZIP? The archived snapshot alone cannot answer this.
2. Once the current code is available, which parts are reusable and which conflict with the approved gameplay requirements?
3. What is the smallest demonstrable model relationship for learning schema design (for example shared item definitions vs a uniquely owned equipment instance), and how should it be tested?
4. Before any implementation, which specific files and changes does the user approve? The existing planning-only code-write restriction remains in force until explicitly amended.
