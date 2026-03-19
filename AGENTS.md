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
- Pydantic schemas in `subway/schemas.py` — all API responses must be validated through these models
- `get_line_alerts()` returns raw MBTA API format; extract `attributes.header` → `headline`, `attributes.severity` → `severity` before validating with `AlertSchema`
- `get_predictions()` returns flat dicts that match `PredictionSchema` directly — no transformation needed
- `StationDetailSchema.lines_served` must be computed by the service layer (not returned by MBTA class)
- URL namespace is `subway:` — use `reverse("subway:trains-alerts")` etc.
- URL parameters: `<str:line_name>` (supports spaces via `%20`), `<str:station_id>` (e.g. `place-knncl`)
- Root `/` redirects to `/trains-alerts/` via `RedirectView`
- All API views are wired to the service layer with proper error handling (404 for unknown resources, 500 for unexpected errors)
- API views validate resource existence before fetching related data (e.g. check line/station exists before fetching alerts/predictions; return 404 for unknown resources)
- API views use `.model_dump()` on Pydantic models for JSON serialization
- Service layer: `subway/services.py` — singleton MBTA client with lazy initialization
- Import service functions with `from subway import services` then call e.g. `services.get_line_names()`
- Service functions validate return data through Pydantic schemas; views should use `.model_dump()` for JSON serialization
- `services.get_station()` computes `lines_served` by scanning cached `_mbta_client.lines`

## Template Patterns
- Base template: `subway/templates/subway/base.html` — all pages extend this
- Active nav highlighting: views pass `{"active_page": "trains-alerts"}` (or `map-facilities`, `about`) in context
- Base template uses `{% if active_page == 'X' %}nav-tab--active{% endif %}` for highlighting
- Leaflet 1.9.4 CDN: CSS in `<head>`, JS before `</body>` — child templates add page-specific JS in `{% block extra_scripts %}`
- Map container divs use `id="map"` and class `map-container`; Leaflet JS initializes against `#map`
- Shared Leaflet utilities: `subway/static/subway/js/map_utils.js` — drawing functions used by both pages; must load before page-specific scripts
- Page-specific JS: `subway/static/subway/js/app.js` (trains-alerts) and `map_facilities.js` (map-facilities)
- Drawing functions return `L.layerGroup` instances — call `.remove()` to clear layers from the map
- Station markers store `stationId` and `stationName` in Leaflet marker options for click handler access
- Prediction popups: `attachPredictionHandlers(stationsLayer)` wires click→fetch→popup on station markers; must be called after layers are drawn
- Popup mouseout close: shared `popupCloseTimeout` variable coordinates close delay between marker and popup DOM elements
- Popup Leaflet options: both pages set `maxHeight`, `autoPanPadding: [50, 50]`, and `keepInView: true` — Leaflet `maxHeight` must be set in JS (not just CSS) for autopan positioning to work correctly
- Route colors: `ROUTE_COLORS` constant in `app.js` maps MBTA route IDs to hex colors; Green-* variants all use `"00843D"`
- Always escape user-facing text in popups via `escapeHtml()` to prevent XSS
- Zoom-to-fit: both pages use `getStationBounds()` + `map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING })` — never use a hardcoded `setView` for all-lines view; always compute bounds from station coordinates
- `FIT_BOUNDS_PADDING = [30, 30]` is consistent across `app.js` and `map_facilities.js`

## CSS Design System
- Single stylesheet: `subway/static/subway/css/style.css` — uses CSS custom properties (`:root` variables)
- Design tokens: `--color-*` (palette), `--space-*` (spacing scale), `--font-size-*` (typography), `--shadow-*`, `--radius-*`, `--transition-*`
- MBTA line colors: `--mbta-red`, `--mbta-orange`, `--mbta-green`, `--mbta-blue`, `--mbta-mattapan`
- Alert severity classes: `.alert-severity--high`, `--medium`, `--low` — use in JS when rendering alerts
- Popup CSS classes: `.popup-title`, `.popup-section`, `.popup-line-badge`, `.popup-facilities`, `.popup-route-name`, `.prediction-item`, `.prediction-time` — use in JS when building popup HTML
- Map legend: `.map-legend`, `.legend-item`, `.legend-swatch`, `.legend-label` — use for color legend on Map & Facilities page
- Loading states: `.loading-spinner`, `.loading-text` — use for async data fetches
- Responsive breakpoints: 768px (tablet), 480px (mobile)
- Popup viewport constraints use CSS `min()` for responsive sizing: `min(280px, 50vh)` height, `min(320px, 80vw)` width
- When adding new CSS, use existing custom properties rather than hard-coding colors/spacing

## Gotchas
- `.env` file must be present in project root with `MBTA_V3_API_KEY`
- `.env` is in `.gitignore` — never commit it
- `DATABASES = {}` means `migrate` is not needed and will fail
- `DATABASES = {}` also means tests must use `SimpleTestCase`, not `TestCase` (TestCase tries to flush the DB)
- MBTA_class.py was copied from `../MBTA-API/` with two changes: `.env` path uses `parent.parent` instead of `parent`, and `get_line_alerts()` sort key navigates into `attributes.severity` with `None` fallback to 0
- First call to any service function triggers ~3s initialization; subsequent calls are instant
- Raw MBTA API alert data nests severity under `attributes.severity`, not top-level `severity`; severity can be `None` — always use a fallback when sorting

## Dependencies
- Python packages: Django, Pydantic, requests, python-dotenv
- External: MBTA V3 API, OpenStreetMap tiles, Leaflet.js
