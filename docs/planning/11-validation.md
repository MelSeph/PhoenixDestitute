# Planning validation — honest status

| Check | Status | Evidence or missing work |
|---|---|---|
| Approved handbook structure | **Passed** | 12 requested numbered `.md` documents created. |
| Original legacy-game file inventory | **First-pass complete** | 30 legacy source/assets/changelog files inventoried against ZIP entries; detailed per-variable reads/writes not yet exhaustive. |
| Script loading comparison | **Checked** | 22 `<script src>` references identified in `legacy_game/index.html`; `updatepotions.js` not directly referenced. |
| Every ZIP file accounted for | **Listed by category; partial review** | Legacy files plus existing Django project files and caches; empty React folder noted. Django code not line-by-line analyzed. |
| Every app/model has exactly one owner | **Not attempted** | No models or app boundaries approved. |
| No circular app dependencies | **Not attempted** | No dependency graph approved. |
| Every claim backed by source | **In progress** | Inventory names source files; detailed statement-by-statement provenance still needs work. |
| Full start-to-finish gameplay trace | **Not passed** | Partial flow documented only; branching remains. |
| Original game files left untouched | **Passed for produced artifact** | Files were read from ZIP; output contains only approved `CLAUDE.md` copy and planning Markdown documents. |

Do not convert a partial check into a passed check without doing the work.

## Django snapshot audit — 2026-11-15

**Scope:** examined Django entries from the user's `PhoenixDestitute.zip`. This is a static archive inspection, **not** a test of the user's current working directory or a Django runtime test.

| Finding | Direct evidence in archived path | Interpretation |
|---|---|---|
| Django project scaffold exists | `django/manage.py`; `django/phoenixdestitute/{settings,urls,asgi,wsgi}.py` | Some reusable configuration, not a verified functional backend |
| SQLite configured | `django/phoenixdestitute/settings.py`: `DATABASES` uses `django.db.backends.sqlite3` | Starting database engine is defined |
| `game` app referenced | `settings.py`: `INSTALLED_APPS` includes `game` | Expects a separate Django application |
| Views imported and routes declared | `django/phoenixdestitute/urls.py`: `from game import views`; home, prototype, player detail and player create routes | HTTP route intentions exist; behavior not verified |
| No `django/game/` files included | Complete ZIP entry listing checked; 13 regular files under `django/`, none inside `django/game/` | The archived snapshot lacks the application required by its settings and routes |
| No game models, migrations, or SQLite DB included | Complete ZIP entry listing checked | Cannot infer a functioning current database or evaluate actual saved data from archive |
| README appears to describe files absent from archive | `django/README.md` mentions `game/models.py`, `game/views.py`, template and legacy static snapshot | Documentation and supplied snapshot do not match |
| Dependency declaration exists | `django/requirements.txt`: `Django>=5.2,<6.0` | Django was contemplated in this archive, not yet an approved stack decision |

**Result:** the Django snapshot is **incomplete as supplied**. It is **not established** that the user's live local project is incomplete. No runtime checks, migration checks, or app tests were run; do not mark them passed.

**Suggested next evidence:** current local `django/` folder snapshot (without `.venv/`, `__pycache__/`, or secrets) and, separately if appropriate, the current model/migration files. Do not delete or replace existing work in order to obtain this evidence.

## Phase 2C validation checklist — 2026-11-15

- Django model schema unchanged; `makemigrations --check --dry-run` should report no changes.
- New backend transition tests cover resurrection, regression, New Life with same character or new successor, predecessor chains, unprovisioned players, invalid outcomes, active-life constraints, and preservation of Player/GameSave.
- In the user's local Django environment run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py test game`.
- No death endpoint, game frontend transition, equipment transfer, character stat reset, or per-playthrough save migration is implemented.
- **Runtime verification is pending** until the local Django test output is received. The earlier baseline was 16 passing tests; this phase adds 11 tests (expect 27).


## Phase 2D validation — 2026-11-15

- Additive migration `0006_playthroughsave` creates life-scoped save rows and copies each existing `GameSave` JSON into the corresponding **initial** life, without deleting or modifying legacy rows. Back up `django/db.sqlite3` before applying.
- Service tests cover current-life saves, compatibility mirroring, repeated updates, empty new life, non-overwriting historical saves, resurrection continuity, cross-Legacy access denial, invalid payloads, and unprovisioned players.
- Source inspection found no deployed save/load API routes in `django/phoenixdestitute/urls.py`; no frontend or public save API is changed here.
- This packaged copy has syntax and ZIP checks only. **Django runtime check, migration, and tests must run on the user's installed environment**; expected test discovery 37 (27 previous + 10 new).
- Run from `PhoenixDestitute/django`: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate`, `python manage.py test game`, `python manage.py showmigrations game`.
