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

## Gotchas

- The MBTA class loads `.env` relative to its own file location — if copying the class, ensure `.env` is in the same directory or adjust the dotenv path
- Django settings reference `BASE_DIR / 'subway' / 'templates'` for template discovery
