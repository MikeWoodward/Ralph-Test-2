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

## API Endpoints

- API views live in `subway/views.py` alongside page views, separated by a comment header
- API URLs are registered in `subway/urls.py` under the `api/` prefix (e.g. `api/lines`)
- Use `JsonResponse(data=..., safe=False)` when returning a list (non-dict) as JSON
- API error handling pattern: wrap in try/except, use `traceback.extract_tb(sys.exc_info()[2])` to get line number, return `JsonResponse(data={"error": ..., "line": ...}, status=500)`

## Frontend (JavaScript)

- `app.js` initialises Leaflet maps conditionally based on which page is loaded (checks for element ID)
- Global state namespace: `MBTA_APP` object holds shared references (e.g. `trainsMap`, future layer groups)
- Map initialisation: Leaflet requires a container element with an explicit height set via CSS before `L.map()` is called
- Auto-zoom pattern: fetch all lines → collect station coords → `map.fitBounds(L.latLngBounds(coords), { padding: [20, 20] })`
- Always use `encodeURIComponent()` when interpolating line names into API URLs (they contain spaces)
- Leaflet CDN (v1.9.4) CSS and JS are loaded in `base.html` — available on every page
- Inter-component communication: dropdown fires `document.dispatchEvent(new CustomEvent("lineSelected", { detail: { lineName } }))` — listen with `document.addEventListener("lineSelected", (e) => { ... e.detail.lineName ... })`
- `MBTA_APP.lineLayerGroup` holds the current line's Leaflet layers for clearing on re-selection
- `renderLineOnMap(lineName)` draws polylines + station markers for a single line; clears previous layers first
- `line_color` from API is hex without `#` — always prepend `#` before passing to Leaflet/CSS
- Draw polylines before circle markers so stations render on top of lines
- Station circle markers use `bindTooltip()` for hover labels (direction "top", offset [0, -8])
- Station click popups: use `marker.unbindPopup()` + `marker.bindPopup(html, { autoPan: true })` + `marker.openPopup()` for dynamic async content; update with `marker.setPopupContent()` after fetch completes
- Popup close-on-mouseout pattern: `schedulePopupClose(map, delay)` on marker mouseout, `clearPopupCloseTimer()` on marker/popup mouseover, popup mouseleave triggers close — use `map.on("popupopen")` to attach DOM-level events to popup element
- `MBTA_APP.popupCloseTimer` holds the shared timeout ID for popup auto-close
- Predictions are grouped by `route` key (e.g. "Red", "Green-B") with max 4 per route

## Gotchas

- The MBTA class in `subway/MBTA_class.py` loads `.env` from one directory up (`Path(__file__).resolve().parent.parent`), which resolves to the Django project root. The `.env` file must be at the project root.
- Django settings reference `BASE_DIR / 'subway' / 'templates'` for template discovery
- Import the MBTA class as: `from subway.MBTA_class import MBTA`
- MBTA().initialize() makes multiple API calls and takes ~4-5 seconds — use a singleton pattern to avoid repeated initialization
- `get_station()` returns `id` as the key but `StationSchema` expects `station_id` — views must remap: `data['station_id'] = data.pop('id')`
- `get_line_alerts()` returns raw MBTA API alert dicts; extract `attributes.header` → `headline` and `attributes.severity` → `severity` for `AlertSchema`
- Pydantic schemas live in `subway/schemas.py` — import as: `from subway.schemas import LineSchema, StationSchema, AlertSchema, PredictionSchema`
