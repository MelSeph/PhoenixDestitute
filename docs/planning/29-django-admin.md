# Django administration screens — 2026-11-15

The user requested admin screens through `admin.py`. Added `django/game/admin.py` with registrations for every current game model. `/admin/` was already routed and Django admin/auth were already installed; no schema or framework changes were needed.

## Screens and intended use

- Players, Characters, Legacies, and Playthroughs: search/filter and inspect life relationships. Legacy detail includes its lives; life detail includes birth and inventory rows.
- Local characters and birth stat drafts: inspect ownership/drafts; full browser Session credentials are masked, exposing only an eight-character suffix for correlation.
- Birth records, compatibility/per-life saves, death snapshots and entries: inspect saved JSON/history with linked detail screens. Snapshot detail includes its entries.
- Inventory, equipped reservations, enchantments, equipment definitions, positions, and regional thermal coverage: searchable lists and relation links. Definition detail includes position/coverage inlines; inventory detail includes enchantments.
- Existing PlayerGameSettings: edit the auto-adapt-equipment preference only, with Player identity fixed. This does not implement the deferred automatic scoring engine.

Game state and catalogs are intentionally read-only in this initial administration milestone. Add/change/delete and bulk delete are disabled, including for superusers, so standard admin ModelForms cannot bypass revision checks, birth confirmation, equipment validation, lifecycle transitions, or the permanent whole-story deletion service. New catalogs/edit workflows can be scoped separately. No custom session impersonation, lifecycle, purge, or draft mutation admin actions are introduced.

## Access and Django explanation

Open **http://127.0.0.1:8000/admin/** directly (the React development proxy does not forward admin paths). Use an existing active staff login with appropriate model view permissions; a superuser can inspect all registered screens. Anonymous/nonstaff access redirects to login. This task does not create or modify accounts/passwords.

If no admin account exists, create one interactively from `django/`:

```powershell
python manage.py createsuperuser
```

`@admin.register` connects models to screen configurations. `list_display`, `search_fields`, and `list_filter` control the table/search/sidebar. Read-only inlines put related records on the parent screen. Permission methods enforce inspection at the HTTP level, rather than merely hiding Save buttons. Existing Django authentication, model permissions, and CSRF protection remain in force.

## Verification

Seven new admin tests exercise every model's list/detail rendering with populated related data, search/filter behavior, rejected add/change/delete requests, absence of bulk deletion, the editable preference, masked credentials, login restrictions, and limited staff view permissions. The full suite passes **305 Django tests, none skipped**. Django system checks report no issues; migration drift check reports no changes. Existing working database data/accounts and React/legacy frontends are unchanged. No migration, commit, or push.
