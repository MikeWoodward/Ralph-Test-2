# MBTA Subway App

## Build & Run

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Django dev server
python manage.py runserver
```

## Project Structure

- `mbta_project/` — Django project settings, root URL conf, WSGI/ASGI
- `subway/` — Main Django app (views, urls, templates, static assets)
- `subway/templates/subway/` — Django templates (base.html + page templates)
- `subway/static/subway/css/` — CSS stylesheets
- `subway/static/subway/js/` — JavaScript files

## Patterns

- Templates use Django's `{% extends %}` / `{% block %}` inheritance from `base.html`
- Active tab is controlled via `active_tab` context variable passed from views
- Static files follow Django's `app/static/app/` namespace convention
- Leaflet.js and OpenStreetMap tiles loaded from CDN in base template

## Services

- `subway/services.py` provides a thread-safe MBTA singleton via `get_mbta()`
- Uses double-checked locking (`threading.Lock`) — safe for Django's multi-threaded request handling
- Import pattern: `from subway.services import get_mbta` then `mbta = get_mbta()`
- First call takes ~4-5 seconds (API initialization); subsequent calls return instantly

## Gotchas

- The MBTA class in `subway/MBTA_class.py` loads `.env` from one directory up (`Path(__file__).resolve().parent.parent`), which resolves to the Django project root. The `.env` file must be at the project root.
- Django settings reference `BASE_DIR / 'subway' / 'templates'` for template discovery
- Import the MBTA class as: `from subway.MBTA_class import MBTA`
- MBTA().initialize() makes multiple API calls and takes ~4-5 seconds — use a singleton pattern to avoid repeated initialization
- `get_station()` returns `id` as the key but `StationSchema` expects `station_id` — views must remap: `data['station_id'] = data.pop('id')`
- `get_line_alerts()` returns raw MBTA API alert dicts; extract `attributes.header` → `headline` and `attributes.severity` → `severity` for `AlertSchema`
- Pydantic schemas live in `subway/schemas.py` — import as: `from subway.schemas import LineSchema, StationSchema, AlertSchema, PredictionSchema`
