# PhoenixDestitute — Django migration starter

This is a **separate project** based on the supplied PhoenixDestitute 0.0.20 ZIP. The existing browser interface and JavaScript are preserved. **Game rules have not yet been ported to Python**, and **progress is not yet saved by Django**. Account login is deferred for development but is the intended requirement for the completed game.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Visit http://127.0.0.1:8000/ . Stop the server with Ctrl+C.

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of `python` without activating.

## Structure

- `phoenixdestitute/` — Django project settings and URL configuration
- `game/templates/game/index.html` — original browser game page with updated static paths
- `game/static/game/legacy/` — untouched source snapshot, including original HTML, scripts, styles and version notes
- `game/views.py` — temporary game page endpoint
- `game/models.py` — reserved for future persistent game data

## Migration sequence

1. Capture baseline behaviors and formulas from the original JS.
2. Implement character, inventory, and game-state models with migration tests.
3. Port game actions into pure Python domain services and Django endpoints.
4. Change the browser UI to call endpoints instead of directly mutating authoritative state.
5. Add durable saves, then login/ownership and authorization for every save.

## Important

This scaffold is **development-only**. Before deploying publicly, configure a strong secret key, disable debug mode, set allowed hosts, enforce secure cookies/HTTPS, configure password validators, and review static file serving and authentication. The existing JavaScript cheat console remains present; it must not be trusted when server-authoritative state is introduced.
