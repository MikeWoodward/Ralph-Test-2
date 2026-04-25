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
- Shared page navigation lives in `BosWay/subway/templates/subway/base.html`; page views should pass both `page_title` and `active_page` so the title stays `BosWay - <page>` and the correct nav tab is highlighted.
- Page-specific frontend behavior should be loaded from each template's `page_scripts` block with a dedicated asset under `BosWay/subway/static/subway/js/` instead of inlining scripts into `base.html`.
- For browser-verification artifacts, run `../.venv/bin/python run_chrome_tests.py` from `BosWay/`; the runner reuses an already-running local server at `127.0.0.1:8000` when available, otherwise starts its own `manage.py runserver`, then writes per-case JSON and Markdown results to the repo-root `test-results/` directory.
- When a page needs third-party frontend assets, add them with a page-specific `extra_head` block and/or that page's `page_scripts` block instead of loading them globally for the whole site.
- When a page needs a full-width map layout, add a page-specific wrapper class in the template and keep the shared `page-content` shell generic instead of changing the centered card styles used by other pages.
- For Leaflet views that redraw one selected route, keep the rendered polylines and station markers inside one `L.featureGroup`, remove that group before drawing the next selection, and call `fitBounds()` on the replacement group so the viewport follows the active route.
- For Leaflet views that must show the full subway network on load, fetch `/api/lines` once, load each `/api/lines/<line_name>` response in parallel, render all line shapes plus one deduplicated station marker per station inside one `L.featureGroup`, and call `fitBounds()` on that aggregate group so the full network stays in view.
- For Leaflet page overlays such as map legends, keep the overlay container in the page template, anchor it with `position: relative` on the page-specific map shell, and populate it from data the page already fetched instead of adding extra API calls.
- For Map & Facilities station detail popups, store `stationId` and `stationName` on each deduplicated station marker, fetch `/api/stations/<id>` on hover or click, and render served-line badges from the already-fetched line color map instead of hardcoding route colors.
- On the Trains & Alerts page, fetch line detail and line alerts in parallel after a non-default selection, keep the alerts panel hidden until a line is selected, and make `#alerts-content` the scrollable container so long alert lists do not grow the whole page.
- When the Trains & Alerts dropdown returns to its default option, invalidate the active request token, remove the selected `L.featureGroup`, clear alert DOM content, hide the alerts panel, and refit the map to the full-system bounds so stale responses cannot restore an old selection.
- For Trains & Alerts station prediction popups, store `stationId` and `stationName` on each Leaflet station marker, fetch `/api/stations/<id>/predictions` on marker click, and group the client-side results by line while capping each group at four rows.
- For Trains & Alerts station prediction popups, bind the Leaflet popup with explicit `keepInView`, `closeOnEscapeKey`, `closeOnClick`, `maxHeight`, and popup `className` options, then coordinate marker/popup mouseleave handling with a short close timer so the popup stays usable while the pointer moves from the marker into the popup.
- For Leaflet pages that should share MBTA route/station visuals, keep the common stroke and station-ring options in one shared asset such as `subway/static/subway/js/map_styles.js`, and load it before each page-specific map script so both pages stay visually in sync.
- When MBTA line colors flow from backend JSON into shared Leaflet styling helpers, normalize optional leading `#` characters before building CSS color strings so routes and station rings do not render with invalid `##RRGGBB` values.
- For Leaflet pages that should share the same map-shell or popup boundary styling, define the shared selectors once in `subway/static/subway/css/style.css` and keep the page-specific classes only for content unique to one page.
- Keep the shared fallback full-system bounds in `subway/static/subway/js/trains_alerts.js` and `subway/static/subway/js/map_facilities.js` aligned with the outermost live subway stations so default/reset map states do not clip edge stations.
- Keep project-level placeholders in `BosWay/templates/` and `BosWay/static/` when settings point to those directories.
- The repo root `.env` file remains the server-side location for configuration values.
- MBTA integration lives in `BosWay/subway/services.py`: load the repo-root `.env`, reference the sibling `MBTA-API/MBTA_class.py`, and reuse the module-level singleton instead of creating per-request clients.
- Keep Pydantic response models in `BosWay/subway/schemas.py`, and normalize raw `MBTA_class.py` payloads inside `BosWay/subway/services.py` before views consume them.
- In `BosWay/subway/services.py`, guard raw MBTA payload boundaries with small mapping/list validators before normalizing into schemas so malformed upstream data fails clearly instead of triggering attribute errors mid-transform.
- Keep `PredictionSchema` time fields as validated datetimes and serialize API responses with `model_dump(mode="json")` so frontend code receives normalized timestamp strings.
- Startup MBTA initialization belongs in `BosWay/subway/apps.py` via `SubwayConfig.ready()` and must stay idempotent because Django can call `ready()` more than once in tests.
- When a JSON endpoint returns a top-level list for frontend code, use `JsonResponse(..., safe=False)` and keep the view response shape identical to the service output.
- For schema-backed detail endpoints such as `api/lines/<str:line_name>`, return `JsonResponse(schema.model_dump(mode="json"))` so nested tuples serialize cleanly to JSON arrays.
- For list endpoints that can legitimately return an empty list, validate the parent resource first (`get_line()` or `get_station()`) so the view can still return JSON `404` for unknown IDs instead of treating missing resources as empty data.
- Validate public `line_name` and `station_id` path inputs in `BosWay/subway/views.py` before detail lookups: reject malformed values with JSON `400`, reject unknown-but-well-formed values with JSON `404`, and use the cached allowlists in `BosWay/subway/services.py` to avoid unnecessary MBTA detail calls.
- For frontend consumers of `/api/lines/<line_name>`, validate the parsed JSON object, shapes array, and station coordinates before passing data into Leaflet, and clear any active route layer before showing a line-load error so stale geometry does not linger on the map.
- When `README.md` documents browser dependencies loaded from third-party CDNs, document the library license/version and the delivery service terms separately; a CDN such as `unpkg` is a distinct external service from the hosted library itself.

## Gotchas
- `STATICFILES_DIRS` points at `BosWay/static/`; keep that directory present or Django will raise `staticfiles.W004` during `manage.py check` and tests.
- The previous root-level Django files are no longer the active app location; new implementation work should happen inside `BosWay/`.
- `DATABASES = {}` is exposed by Django as the dummy backend during runtime/tests, so assertions should check for `django.db.backends.dummy` rather than expecting a literal empty dict.
- For JSON API views, return short JSON `404`/`500` responses instead of falling back to Django's default HTML error pages, and log the failing line number when catching unexpected exceptions.
- The sibling `MBTA-API/MBTA_class.py` alert sorter can raise `TypeError` when upstream severities are `None`; keep the fallback in `BosWay/subway/services.py` that rebuilds line alerts from cached route IDs so line selection stays usable even when the upstream helper crashes.
- If Ralph tracking files disagree with the `BosWay/` implementation state, verify the live code and tests first, then sync `ralph/projects/mbta-subway/prd.json` instead of re-implementing an already-finished story.
- Keep `README.md` aligned with the live `BosWay/` layout, page script names, and `/api/lines` / `/api/stations` routes; older root-level paths and endpoint shapes are legacy documentation only.
- Keep a favicon linked from `BosWay/subway/templates/subway/base.html`; missing it creates browser-console `404` noise that can fail manual verification or browser automation runs even when the feature logic works.
- The shared full-system bounds can drift as MBTA station data changes; when updating them, verify both scripts still cover edge stations such as the Green Line D branch western stops and Red Line Braintree.

## Dependencies
- The Django project depends on the repo-level virtual environment at `.venv/`.
- Ralph bookkeeping for this feature lives under `ralph/projects/mbta-subway/`.
