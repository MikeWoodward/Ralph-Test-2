# MBTA Subway App

## Architecture
- Django 6.0 project (`mbta_project`) with a single app (`subway`)
- No database — all data from the MBTA V3 API via the `MBTA` class
- Vanilla JavaScript frontend with Leaflet.js for maps
- Virtual environment at `.venv` with Python 3.12

## Build & Run
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server
python manage.py runserver
```

## Patterns
- Database-dependent Django apps (admin, auth, sessions) are removed since there's no DB
- Middleware is minimal: security, common, clickjacking only
- Static files: `subway/static/subway/{css,js}/`
- Templates: `subway/templates/subway/`
- MBTA API client: `subway/MBTA_class.py` — import with `from subway.MBTA_class import MBTA`
- MBTA class loads `.env` from project root (parent.parent of `__file__`); do not move `.env` into `subway/`
- `MBTA.initialize()` is expensive (~3s, many API calls); call once at startup, cache the instance

## Gotchas
- `.env` file must be present in project root with `MBTA_V3_API_KEY`
- `.env` is in `.gitignore` — never commit it
- `DATABASES = {}` means `migrate` is not needed and will fail
- MBTA_class.py was copied from `../MBTA-API/` with one change: `.env` path uses `parent.parent` instead of `parent`

## Dependencies
- Python packages: Django, Pydantic, requests, python-dotenv
- External: MBTA V3 API, OpenStreetMap tiles, Leaflet.js
