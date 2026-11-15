# Game save access across browser restarts — 2026-11-15

The user reported saved characters disappearing after closing/reopening the same normal browser and address. Inspection found Django already issued persistent 14-day game cookies (`SESSION_EXPIRE_AT_BROWSER_CLOSE=False`), but admin and game shared the same session credential. Admin login rotates/deletes the old Session; logout flushes it. Because roster/draft ownership references Session with cascading deletion, this could orphan permanent characters. The working database had two Players and no LocalCharacter rows, with old authenticated sessions containing a game selection. No data or credentials were printed beyond aggregate diagnostics.

## Fix

`GameSessionMiddleware` extends Django's existing SessionMiddleware. Game requests retain the original persistent `sessionid` cookie; `/admin/` requests use the separate `phoenix_admin_session` cookie. Request handling and response cookie creation/deletion use the same scope, preserving Django expiry, HttpOnly, SameSite, authentication, and logout behavior. No global settings are changed per request. Browser-close expiration is explicitly disabled; the existing 14-day lifetime is retained.

For an old shared staff session, Django validates authentication first. A game request then copies non-auth session data into a separate anonymous game Session and transfers any surviving ownership/draft rows transactionally. Only the character selection already proven by that cookie can be adopted; unrelated orphaned characters are never listed or assigned. Normal nonstaff account API guards remain unchanged. Admin may require logging in again under its new cookie. No passwords or accounts are changed.

There is no broad database reclamation or save reset. A lost/cleared/expired cookie still cannot prove ownership; private windows and different hostnames remain separate profiles. This fixes ordinary restart persistence and admin session interference, not cross-device recovery. Existing permanent characters/history are retained.

## Verification

All **309 Django tests pass, none skipped**, including four new checks for a reopened client's persistent cookie, expiry/HttpOnly flags, actual admin login/logout without losing game ownership, and compatibility recovery from an old shared staff login. Existing admin tests now authenticate using the dedicated admin cookie.

Nine browser checks pass: all eight character-management cases plus a real Edge process-restart test. The restart case launches a temporary persistent browser profile, creates a saved character against a temporary database, closes the entire browser context/process, reopens that profile, and loads the exact same roster entry without recreating it. No live user characters were created/deleted for testing. No migration, commit, or push.
