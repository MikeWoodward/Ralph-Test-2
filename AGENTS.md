# Project Root

## Architecture
- The active Django project now lives under `BosWay/`.
- The repo-level virtual environment remains at `.venv/`.
- Ralph bookkeeping for this feature lives under `ralph/projects/mbta-subway/`.

## Build & Run
```bash
source .venv/bin/activate
cd BosWay
python manage.py runserver
```

## Patterns
- Application code lives under `BosWay/`; run Django commands from that directory with `../.venv/bin/python manage.py ...`.
- Keep the root URL redirect in `BosWay/BosWay/urls.py` pointed at the named route `subway:trains_alerts` so page routing stays stable if the page path changes later.
- Use `BosWay/subway/templates/subway/` and `BosWay/subway/static/subway/` for app-owned templates and static assets.
- Keep project-level placeholders in `BosWay/templates/` and `BosWay/static/` when settings point to those directories.
- The repo root `.env` file remains the server-side location for configuration values.
- MBTA integration lives in `BosWay/subway/services.py`: load the repo-root `.env`, reference the sibling `MBTA-API/MBTA_class.py`, and reuse the module-level singleton instead of creating per-request clients.
- Startup MBTA initialization belongs in `BosWay/subway/apps.py` via `SubwayConfig.ready()` and must stay idempotent because Django can call `ready()` more than once in tests.

## Gotchas
- `STATICFILES_DIRS` points at `BosWay/static/`; keep that directory present or Django will raise `staticfiles.W004` during `manage.py check` and tests.
- The previous root-level Django files are no longer the active app location; new implementation work should happen inside `BosWay/`.
- `DATABASES = {}` is exposed by Django as the dummy backend during runtime/tests, so assertions should check for `django.db.backends.dummy` rather than expecting a literal empty dict.

## Dependencies
- The Django project depends on the repo-level virtual environment at `.venv/`.
- Ralph bookkeeping for this feature lives under `ralph/projects/mbta-subway/`.
