# Game settings — equipment adaptation preference

## Agreed behavior

The user chose a game setting that offers automatic equipment adaptation or player-controlled timing, and approved **player-controlled timing as the default**. The subsequent “continue” authorizes implementing this settled preference independently of the still-undefined scoring formula. No frontend or automatic swapping engine is implemented here.

- `auto_adapt_equipment: false`: weather/build changes may update future equipment scores; auto-equip waits for a player request.
- `auto_adapt_equipment: true`: the future engine may reevaluate carried equipment on weather/build changes and perform qualifying automatic upgrades.
- Either mode permits manual equipment selection, including lower-scoring items. Automatic upgrades must use the complete-loadout, strictly-better, atomic-swap rules in `14-equipment-rules.md`.

## Step-by-step implementation

1. `PlayerGameSettings` has a one-to-one link to the existing Player and a boolean `auto_adapt_equipment` defaulting to false. This keeps the preference independent of an individual life, inventory item, or legacy JSON document. It survives the existing life-transition services because those retain the Player identity.
2. `GET /api/game/settings/` returns `{"success": true, "settings": {"auto_adapt_equipment": false}}` when no preference record exists. Reads create no records or saves. The endpoint uses only the session-selected local Player; a caller cannot select another owner with an ID.
3. `POST /api/game/settings/` accepts exactly `{"auto_adapt_equipment": true}` or the corresponding false value. Strings, numbers, null, missing fields, and extra fields are rejected with 400. CSRF remains enabled; account access is unsupported (403), missing local session returns 404, and unsupported HTTP methods return 405.
4. Updates lock the Player and update/create its single settings record in a transaction. Repeated updates do not duplicate rows. There is no preference revision: the last successful explicit update wins for this single setting.
5. Save/load JSON cannot overwrite the setting. Updating it does not alter inventory, trigger a swap, rotate inventory/save revisions, or touch `GameSave`/`PlaythroughSave`. It is a persisted input for the future adaptation engine, not a claim that that engine exists today.

Migration `0010_player_game_settings` creates one new table with no backfill and no changes to existing game data. There are no new dependencies, frontend changes, or edits to `legacy_game/`. Commit and push remain separately authorized.

## Verification

Nine new tests cover default reads without writes, toggling/repeated updates, session isolation, missing sessions, invalid payloads, CSRF, method restrictions, unsupported account access, persistence across Regression, and isolation from inventory/save data. Run `python manage.py test game`, `python manage.py check`, and `python manage.py makemigrations --check --dry-run` from `django/`.

Local results: **113 tests passed, none skipped**, including the existing headless Chromium checks. Django checks passed and no pending model changes were detected. Backup `django/db.phase2h-settings-backup.sqlite3` was created before applying migration 0010; `showmigrations game` confirms migrations 0001–0010 applied. No commit or push performed.
