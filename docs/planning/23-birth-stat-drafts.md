# Phase 2O — Birth stat drafts

## Approved scope

The user approved the reviewed Phase 2O plan with “yes”: persistent session-owned stat drafts, independent equal-chance server rolls from 1–5, unlimited explicit rerolls, freely switchable locks with at most three active, ×10 resource previews, refresh/retry/stale-request protection, and tests. Existing characters/saves stay unchanged. Name, gender, looks, final birth confirmation, training, and current-Condition formulas are later steps. Commit/push remain separately authorized.

## Step-by-step Django explanation

1. **Store a draft, not a born character.** `BirthStatDraft` has a UUID identifier, an opaque UUID revision, and a one-to-one foreign key to Django's database Session. One live browser session owns one draft. The draft UUID is not a Character ID, and no Player/Legacy/Character/Playthrough/save is created by this flow.
2. **Use explicit base fields.** The eight integer fields are `luck`, `strength`, `defense`, `agility`, `likeability`, `intelligence`, `endurance`, and `baseline_condition`. Model validators and a database check enforce 1–5. These constraints apply only to creation drafts, not lifetime character growth. No sexual-attraction field is rolled for a newborn. Dynamic current Condition and its underlying statuses are not fabricated.
3. **Roll on the server.** Creation uses a separate `secrets.randbelow(5) + 1` draw for each field. Each outcome 1–5 is equally likely; no point budget, weighted distribution, or Luck modifier is introduced. Repeating creation for an existing draft resumes it without calling the generator again. GET never generates or creates a draft.
4. **Keep locks explicit.** `locked_stats` is a JSON list containing at most three distinct names from those eight fields. Locks may be freely switched or cleared, and changing locks does not roll values. Invalid lists, duplicate names, and derived resource names are rejected without changing the draft. The service canonicalizes lock ordering; resubmitting the same selection is a no-op.
5. **Reroll only unlocked values.** Each explicit reroll draws once for every unlocked attribute and preserves locked values. There is no attempt limit, currency cost, or Stamina cost during draft selection. Chance may produce the same value again; a reroll is not guaranteed to differ.
6. **Derive resource previews.** The response computes Health = Strength ×10, Mana = Intelligence ×10, and Stamina = Endurance ×10. Each preview has `current` equal to `maximum`, as agreed for birth. These values are not independently rolled, locked, or stored. A locked parent consequently preserves its resource preview across rerolls. There are no live gameplay resource pools in this draft model.
7. **Coordinate writes.** Services use transactions and lock the owning live Session before the draft. Mutation requests require the current revision. A changed lock selection or an explicit reroll generates a fresh revision. Rerolls advance the revision even if chance repeats every value, so retries using the old revision fail before generating more random values. Write failures roll back stat/lock/revision changes.

## API contract

| Endpoint | Request | Behavior |
|---|---|---|
| `GET /api/creation/stats/` | No body | Read the current session's draft; 404 if absent |
| `POST /api/creation/stats/` | `{}` | Create (201), or resume existing draft unchanged (200) |
| `POST /api/creation/stats/locks/` | `revision`, `locked_stats` | Replace the entire active lock selection |
| `POST /api/creation/stats/reroll/` | `revision` | Reroll unlocked base attributes |

Success responses contain `success: true` and a `draft` object with `draft_id`, `revision`, `stats`, `locked_stats`, and `resources`. Each resource preview uses integer `current` and `maximum` fields. Baseline Condition's machine name is `baseline_condition`; there is no independently rolled current Condition. No session key is exposed.

All POST bodies must be JSON objects containing exactly the action's fields. Client-supplied roll values, resources, owner/session IDs, or draft IDs are rejected. Query parameters do not select a foreign draft. Malformed/unexpected fields return 400; invalid locks or stale revisions return 409; missing/expired ownership returns 404. Unsupported methods return 405, subject to normal CSRF middleware for unsafe requests. Authenticated account draft access remains unsupported (403).

All writes retain CSRF protection. A valid anonymous session is explicitly initialized only on creation POST, allowing stat selection before a Player exists. GET, lock, and reroll never create a missing draft. The existing homepage/prototype supplies the CSRF cookie; no frontend is added or rewritten in this phase.

On a 409, a future client should reload the current draft. It must not silently resubmit an old reroll intention with the new revision, which would be another explicit roll. No client retry automation is implemented here.

## Ownership, lifetime, and compatibility

- A valid existing session cookie resumes the same stored draft across page reloads. A public draft UUID alone is not an ownership credential. Expired session keys cannot read or mutate drafts; explicit creation after expiration starts a new anonymous session/draft.
- Drafts are unconfirmed temporary selection data. Deleting/cleaning up their Session cascades to the draft; no recovery/account migration mechanism is introduced. Existing Player/life/save data has no draft foreign key and is not deleted or rewritten by draft actions.
- Final birth confirmation does **not** exist yet. A future approved step must transfer/freeze the selected values into permanent character/life state before session cleanup can remove a draft. Identity, gender, appearance, age progression, and confirmation locking are not pretended to be complete here.
- An existing legacy Player may coexist in the session while a draft is prepared; this does not rename, reset, adopt, or reroll that Player/Character or any old save. The old local-player creation API remains a compatibility route until the new birth flow is explicitly integrated.
- Direct ORM writes bypass service/model validation. Services validate stored drafts rather than silently repair corrupt locks. SQLite lacks PostgreSQL-style row locking; database uniqueness/range checks and transaction rollback are tested, but concurrent multi-process contention is not load-tested.

## Migration and verification

Migration `0016_birth_stat_drafts` creates one new table with a dependency on Django's existing Session table. It backfills no characters, changes no saves, and adds no birth attributes to existing actors. Backup before local migration: `django/db.phase2o-backup.sqlite3`. Migration 0016 applied locally; `showmigrations game` confirms 0001–0016 applied.

Twenty-six new service/API tests cover deterministic independent draw calls and bounds, derived full resource previews, create/read retries, lock persistence/switching/validation, unlimited rerolls, stale revisions before RNG, equal-value rolls, atomic failure, Session ownership/expiry/cleanup, database constraints, malformed/forged inputs, CSRF/method/account restrictions, and preservation of existing Player/life/save data.

Final full suite: **254 tests passed, none skipped** (228 previous + 26 new), including existing headless Chromium checks. `check` reported no issues and `makemigrations --check --dry-run` reported no changes. No frontend or `legacy_game/` edits. No commit or push performed.
