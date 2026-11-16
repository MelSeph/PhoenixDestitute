# Player account recovery and retention — 2026-11-16

The user approved collecting an email address during signup without verification while the game is pre-live. Email verification is expected to become the primary recovery route later. Until then, a deleted account can be reclaimed by signing in with its original username and password during a two-year recovery period.

## Player deletion

1. The player confirms account deletion with their current password and exact username.
2. Django serializes the account's owned players, character roster, recovery codes, birth draft/records, saves, settings, lives, inventory, and item enchantments into a `DeletedAccountArchive`, alongside the password hash and an expiry date two years out.
3. The live user and game rows are removed in the same transaction. A de-identified `AccountDepartureMetric` keeps the deletion date, play time, latest progress summary, recovery attempts, and reclaim/purge outcome.
4. Signing in with the same username/password restores the archived graph, clears the archive, and marks the metric reclaimed. The username remains reserved while a recoverable archive exists.

## Administration and expiry

- Django admin exposes read-only deleted-account archive details and a superuser-only action to permanently purge selected archives. Active accounts are not in that model and cannot be selected.
- The built-in Django user screen cannot delete active users; permanent deletion is only available through the deleted archive action.
- A management command, `python manage.py purge_expired_account_archives`, purges archives after two years. Account state, signup, and sign-in requests also purge expired archives opportunistically.
- For daily automatic cleanup while the app is idle, schedule the management command with the host's task scheduler. The app's request hooks cover active use; they cannot run while the server is stopped.
- Admin departure metrics survive archive purge without storing username, email, password hash, or character snapshots. Recovery totals keep attempt counts without retaining the reclaimed player's username.
- Play time is counted in 60-second visible-game heartbeats, capped at 90 seconds per request. Progress currently records owned character count, highest level, life count, and birth count.

## Verification

Focused Django tests cover email persistence, signed deletion, live-row removal, password-based restore of characters and JSON saves, admin archive purge, recovery metrics, and expiry cleanup. `legacy_game/` is not changed.
