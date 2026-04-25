# BosWay

A real-time web application for the Massachusetts Bay Transportation Authority
(MBTA) subway system. BosWay shows train predictions, service alerts, station
facilities, and interactive subway maps through a Django backend and
page-specific JavaScript clients.

## Author

**Mike Woodward**  
Author and maintainer of BosWay.

## How BosWay Works

The application provides three pages accessible via tab navigation:

### Trains & Alerts

Select a subway line from the dropdown to see it drawn on an interactive map.
The map zooms to fit all stations on the selected line. Any active service
alerts for that line appear above the map. Click a station marker to see a
popup with the next four predicted train arrivals per route, formatted as
relative times (e.g. "3 min") or absolute times for trains further out.

### Map & Facilities

Displays all subway lines and stations on a single map with a color legend.
Hover over or click any station to see its name, the lines it serves, and its
facilities (elevators, escalators, etc.) in a popup.

### About

Lists the external services the application depends on, with links, and credits
the author.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser                          │
│  ┌────────────────┐  ┌───────────────────────────┐ │
│  │ HTML templates │  │ Page scripts + Leaflet    │ │
│  │ + shared CSS   │  │ trains_alerts.js          │ │
│  │                │  │ map_facilities.js         │ │
│  │                │  │ map_styles.js             │ │
│  └────────┬───────┘  └──────────────┬────────────┘ │
│           │ server-rendered pages   │ fetch JSON   │
│           └──────────────┬──────────┴──────────────┘ │
└────────────────────┼────────────────────────────────┘
                     │ HTTP
┌────────────────────┼────────────────────────────────┐
│               Django 6.0 / BosWay                  │
│  ┌──────────┐   ┌────────────┐   ┌──────────────┐  │
│  │ urls.py  │──▶│ views.py   │──▶│ services.py  │  │
│  │ routing  │   │ pages + API│   │ MBTA bridge  │  │
│  └──────────┘   └─────┬──────┘   └──────┬───────┘  │
│                        │                 │          │
│                  ┌─────▼──────┐   ┌──────▼───────┐  │
│                  │ schemas.py │   │ apps.py      │  │
│                  │ Pydantic   │   │ startup init │  │
│                  └────────────┘   └──────────────┘  │
└──────────────────────────────────┼──────────────────┘
                                   │ HTTPS
                          ┌────────┴────────┐
                          │  MBTA V3 API    │
                          └─────────────────┘
```

BosWay is organized into four main layers:

1. **Routing and views**: `BosWay/BosWay/urls.py` redirects `/` to the named
   `subway:trains_alerts` route and includes the app routes from
   `BosWay/subway/urls.py`. `BosWay/subway/views.py` serves both HTML pages and
   JSON endpoints.
2. **Service and schema layer**: `BosWay/subway/services.py` owns MBTA client
   startup, public input validation, raw payload normalization, and conversion
   into Pydantic models from `BosWay/subway/schemas.py`.
3. **Frontend layer**: shared layout lives in
   `BosWay/subway/templates/subway/base.html`, shared styling lives in
   `BosWay/subway/static/subway/css/style.css`, and each interactive page loads
   a dedicated script: `trains_alerts.js` or `map_facilities.js`. Both map
   pages share the MBTA-specific Leaflet styling helpers in `map_styles.js`.
4. **External MBTA integration**: `BosWay/subway/apps.py` triggers
   initialization through `SubwayConfig.ready()`, and
   `BosWay/subway/services.py` loads the repo-root `.env`, imports the sibling
   `MBTA-API/MBTA_class.py`, and reuses one module-level MBTA client for the
   lifetime of the process.

There is **no database** in the live app. Transit data comes from the MBTA V3
API, and Django is used as a thin application layer that renders pages,
validates requests, shapes responses, and serves the static assets that power
the maps.

## Request Flow

### Page Requests

1. A browser requests `/trains-alerts`, `/map-facilities`, or `/about`.
2. `BosWay/subway/views.py` renders the matching template with `page_title` and
   `active_page` so the shared header and navigation stay in sync.
3. The page template extends `BosWay/subway/templates/subway/base.html` and
   loads any page-specific assets through the template blocks.
4. The interactive pages then bootstrap client-side behavior:
   - `trains_alerts.js` initializes the Trains & Alerts map, fetches
     `/api/lines`, and later loads one selected line plus its alerts in
     parallel.
   - `map_facilities.js` initializes the Map & Facilities map, fetches
     `/api/lines`, loads every `/api/lines/<line_name>` response in parallel,
     renders the full network, builds the legend, and fetches station details
     on popup interaction.
   - `about.html` is fully server-rendered and does not need page-specific API
     calls.

### API Requests

1. Frontend JavaScript calls one of the JSON routes in
   `BosWay/subway/urls.py`.
2. `BosWay/subway/views.py` validates public `line_name` and `station_id`
   values before any detail lookup:
   - malformed values return JSON `400`
   - unknown-but-well-formed values return JSON `404`
3. The view delegates to `BosWay/subway/services.py`.
4. The service layer ensures the shared MBTA client has been initialized, calls
   the MBTA class, and normalizes the raw response into the app's schema shape.
5. `BosWay/subway/schemas.py` validates the final payload structure.
6. The Django view serializes the validated schema with
   `model_dump(mode="json")` or returns a JSON array for list endpoints.
7. On unexpected failures, the view logs the failing line information and
   returns a short JSON `500` response instead of an HTML error page.

### Page-Specific Software Flow

- **Trains & Alerts**: page render -> initialize Leaflet map -> fetch line
  names -> user selects a line -> fetch selected line detail and alerts in
  parallel -> draw one `L.featureGroup` for the active line -> fetch station
  predictions when a marker is clicked.
- **Map & Facilities**: page render -> initialize Leaflet map -> fetch line
  names -> fetch every line detail in parallel -> draw the full network in one
  `L.featureGroup` -> render a legend from the already-fetched line data ->
  fetch station details when a marker is hovered or clicked.
- **About**: page render -> shared navigation and static informational content.

## Project Structure

```
BosWay/
  manage.py                      Django management entry point
  BosWay/
    settings.py                  Project settings
    urls.py                      Root redirect and app include
  subway/
    apps.py                      Startup initialization hook
    schemas.py                   Pydantic response models
    services.py                  MBTA integration and normalization
    urls.py                      Page and JSON routes
    views.py                     HTML and JSON views
    tests.py                     Focused Django tests
    static/subway/
      css/style.css              Shared app styling
      js/trains_alerts.js        Trains & Alerts page behavior
      js/map_facilities.js       Map & Facilities page behavior
      js/map_styles.js           Shared Leaflet styling helpers
    templates/subway/
      base.html                  Shared page shell and navigation
      trains_alerts.html         Trains & Alerts page
      map_facilities.html        Map & Facilities page
      about.html                 About page
.env                             MBTA API key (not committed)
requirements.txt                 Python dependencies
```

## Libraries and Versions

### Python (3.12)

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| Django | 6.0.3 | Web framework — serves pages and JSON API endpoints | [BSD 3-Clause](https://github.com/django/django/blob/main/LICENSE) |
| Pydantic | 2.12.5 | Data validation — schemas for API responses | [MIT](https://github.com/pydantic/pydantic/blob/main/LICENSE) |
| requests | 2.32.5 | HTTP client — calls to the MBTA V3 API | [Apache 2.0](https://github.com/psf/requests/blob/main/LICENSE) |
| python-dotenv | 1.2.2 | Environment variables — loads `.env` for API key | [BSD 3-Clause](https://github.com/theskumar/python-dotenv/blob/main/LICENSE) |

Transitive dependencies (installed automatically):

| Library | Version |
|---------|---------|
| annotated-types | 0.7.0 |
| asgiref | 3.11.1 |
| certifi | 2026.2.25 |
| charset-normalizer | 3.4.6 |
| idna | 3.11 |
| pydantic_core | 2.41.5 |
| sqlparse | 0.5.5 |
| typing-inspection | 0.4.2 |
| typing_extensions | 4.15.0 |
| urllib3 | 2.6.3 |

### JavaScript (browser, via CDN)

| Library | Version | Purpose | License |
|---------|---------|---------|---------|
| Leaflet.js | 1.9.4 | Interactive map rendering and controls | [BSD 2-Clause](https://github.com/Leaflet/Leaflet/blob/main/LICENSE) |

### Source-integrated dependency

| Dependency | Version / Source | Purpose |
|------------|------------------|---------|
| `MBTA-API/MBTA_class.py` | Sibling checkout outside this repo; version not pinned here | The only backend bridge to MBTA subway lines, stations, alerts, predictions, and facilities |

## External Services

| Service | Purpose | Terms / Policy |
|---------|---------|----------------|
| **MBTA V3 API** | Supplies live subway line, station, alert, and prediction data to the server-side MBTA client | [MBTA developer portal](https://www.mbta.com/developers/v3-api) and the [MassDOT Developers License Agreement](https://www.mass.gov/doc/massdot-developers-license-agreement-0/download) |
| **OpenStreetMap** | Supplies the browser basemap tiles and attribution-backed map data references | [Copyright and attribution page](https://www.openstreetmap.org/copyright) and the [tile usage policy](https://operations.osmfoundation.org/policies/tiles/) |
| **UNPKG CDN** | Delivers the pinned Leaflet `1.9.4` CSS and JavaScript assets used by the two map pages | [Sideway Terms of Service](https://app.unpkg.com/policies@1.0.1/files/terms-of-service.md) and [Usage Rules](https://app.unpkg.com/policies@1.0.1/files/usage-rules.md) |

## Compliance Notes

- **Django 6.0.3**: Used under the
  [BSD 3-Clause License](https://github.com/django/django/blob/main/LICENSE).
  BosWay uses Django as an application framework only; no additional runtime
  attribution is required, but the license must remain intact if the project is
  redistributed with vendored framework code.
- **Pydantic 2.12.5**: Used under the
  [MIT License](https://github.com/pydantic/pydantic/blob/main/LICENSE).
  The app relies on Pydantic for response validation and should preserve the
  upstream license notice in any redistributed bundled copy.
- **requests 2.32.5**: Used under the
  [Apache License 2.0](https://github.com/psf/requests/blob/main/LICENSE).
  BosWay uses it server-side through the sibling MBTA client, and any
  redistribution of bundled source should keep the Apache license text and
  notices.
- **python-dotenv 1.2.2**: Used under the
  [BSD 3-Clause License](https://github.com/theskumar/python-dotenv/blob/main/LICENSE).
  It is used only to load the repo-root `.env` on the server, and any bundled
  redistribution should preserve the upstream license notice.
- **Leaflet.js 1.9.4**: Used under the
  [BSD 2-Clause License](https://github.com/Leaflet/Leaflet/blob/main/LICENSE).
  BosWay loads the exact `1.9.4` assets from UNPKG with subresource integrity
  hashes on the two map pages instead of vendoring local copies.
- **`MBTA-API/MBTA_class.py`**: BosWay imports this sibling source file as its
  only MBTA backend integration path. This repository does not pin or vendor a
  release of that project, so any packaged redistribution should review the
  sibling project's own licensing and usage terms before bundling it.
- **MBTA V3 API**: Data use is governed by the
  [MassDOT Developers License Agreement](https://www.mass.gov/doc/massdot-developers-license-agreement-0/download).
  The API key stays in the server-side `.env` file, never appears in templates,
  JavaScript, or JSON responses, and BosWay acknowledges MBTA usage in the
  About page and this README.
- **OpenStreetMap**: The map pages display the required
  [OpenStreetMap attribution](https://www.openstreetmap.org/copyright)
  in Leaflet's attribution control, and tile usage follows the
  [OSM Foundation tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
  OpenStreetMap data remains subject to the
  [ODbL](https://opendatacommons.org/licenses/odbl/).
- **UNPKG CDN**: BosWay uses pinned asset URLs plus SRI hashes for Leaflet's
  browser assets and depends on UNPKG only as a static delivery service. Use of
  that CDN remains subject to Sideway's published
  [Terms of Service](https://app.unpkg.com/policies@1.0.1/files/terms-of-service.md)
  and
  [Usage Rules](https://app.unpkg.com/policies@1.0.1/files/usage-rules.md).

## Setup and Running

### Prerequisites

- Python 3.12+
- An MBTA V3 API key ([register here](https://api-v3.mbta.com/register))

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Ralph-Test-2

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API key
echo "MBTA_V3_API_KEY=your_api_key_here" > .env
```

### Running the Development Server

```bash
source .venv/bin/activate
cd BosWay
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser. The root
URL redirects to the Trains & Alerts page.

> **Note**: The first page load takes ~3 seconds while the MBTA client
> initializes and caches line/station data. Subsequent requests are instant.

### Running Tests

```bash
source .venv/bin/activate
cd BosWay
python manage.py test subway
```

> **Note**: There is no database, so `migrate` is not needed and will fail.
> Tests use Django's `SimpleTestCase`.

## API Endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/lines` | List of subway line names |
| GET | `/api/lines/<name>` | Line data (color, shapes, stations) |
| GET | `/api/lines/<name>/alerts` | Alerts for a line |
| GET | `/api/stations/<id>` | Station details (name, facilities, lines served) |
| GET | `/api/stations/<id>/predictions` | Train predictions for a station |

Line names support spaces via URL encoding (for example,
`/api/lines/Red%20Line`).
Malformed line names or station IDs return `400`. Unknown-but-well-formed
resources return `404`. Server errors return `500`.
