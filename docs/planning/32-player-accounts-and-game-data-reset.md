# Player accounts and game-data reset — 2026-11-15

The user requested player registration/sign-in to make saved characters available across browser sessions, and selected deletion of current game data while preserving the Django admin account and shared catalogs. Account recovery is username/password with transfer of the current browser's characters and support for admin-code claims. Numeric game IDs restart at 1; UUID identities remain random and cannot be reset to zero.

## Account ownership

1. Django's built-in `User` stores usernames and password hashes. Registration uses `UserCreationForm`; configured Django password validators enforce a ten-character minimum, common-password checks, numeric-only rejection, and username similarity. Login errors do not distinguish unknown users from wrong passwords. Registration/login/logout are same-origin CSRF-protected JSON actions. Signup is not staff, admin, or superuser creation.
2. Migration 0020 allows a `LocalCharacter` and an unfinished `BirthStatDraft` to have either browser-session ownership or account ownership. Migration 0021 adds database checks requiring exactly one owner. `Player.account` remains the relational link from each continuing story to its account.
3. Signup/sign-in moves only rows already owned by that browser session to the authenticated account **before** Django rotates the session key. The player and roster ownership move together; an unfinished draft moves too. If the account and browser both have unfinished drafts, sign-in stops with a conflict rather than discarding either draft. Logout removes authentication/session data but does not delete account-owned characters or drafts.
4. Each authenticated browser has its own active-character selection in its Django session. Character lists and load/delete operations query the account-owned roster; save, inventory, settings, thermal, and birth endpoints resolve the active Player and verify account ownership on the server. Client-supplied IDs cannot select another user's data.
5. Admin recovery-code redemption while signed in attaches the selected orphan directly to that account. Anonymous redemption remains browser-owned. Neither path duplicates the Player, life, birth, or save.

## Endpoints and UI

- `/api/account/` reports login state; `/register/`, `/login/`, and `/logout/` perform account actions.
- The React **Player account** panel handles registration/sign-in/sign-out. It refreshes the character roster after authentication changes and explains account syncing.
- Account usernames are unique. Email verification, email delivery, and forgotten-password reset are not configured; password recovery remains an open follow-up before public deployment.

## Local data reset

After tests and schema migrations, the local SQLite database's game/story state is cleared: Players, playable/NPC Characters, Legacies, Playthroughs, births, drafts, rosters, recovery codes, JSON saves, player settings, inventory/enchantments/equipment reservations, and death history. Active game selections are removed from Django sessions while Django login/session records are retained. Django users (including the existing superuser) and shared equipment definitions/position/coverage catalogs are preserved. Numeric SQLite sequences for the emptied game tables are reset so the next numeric IDs are 1; UUID-based IDs are not sequences. The recent snapshot containing the cleared current saves was removed; older historical development backups were left untouched. No reset is embedded in a migration or command that would affect another database.

## Verification

Automated tests cover password validation, CSRF, browser-to-account transfer with session-key rotation, draft preservation, recovery-code account claims, two-browser character/save/inventory/settings/thermal access, logout retention, ownership isolation, and birth creation under an account. React browser tests cover UI signup, current-character transfer, and sign-in/loading from a second browser. The working database reset is verified by table counts, foreign-key checks, sequence rows, and preservation of the Django superuser/catalog tables.

Staff accounts may also own player characters. Intentional player sign-in is marked in the Django session so admin/game session-isolation middleware does not mistake a game login for an old shared admin session. A regression test reloads the account state and roster twice for a staff player account.
