# MBTA Subway

A real-time web application for the Massachusetts Bay Transportation Authority
(MBTA) subway system. View train predictions, service alerts, station
facilities, and an interactive map of the entire subway network.

## Author

**Mike Woodward**

## How It Works

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
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  app.js       │  │ map_fac.js   │  │ map_utils │ │
│  │ (Trains page) │  │ (Map page)   │  │ (shared)  │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │     fetch() JSON API      Leaflet │       │
│         └──────────┬───────┘────────────────┘       │
└────────────────────┼────────────────────────────────┘
                     │ HTTP
┌────────────────────┼────────────────────────────────┐
│               Django 6.0                            │
│  ┌─────────┐  ┌────┴─────┐  ┌──────────┐           │
│  │ views.py│──│services.py│──│MBTA_class│           │
│  │ (pages +│  │(singleton │  │ (API     │           │
│  │  JSON)  │  │  + cache) │  │  client) │           │
│  └─────────┘  └──────────┘  └────┬─────┘           │
│  ┌──────────┐                    │                  │
│  │schemas.py│  Pydantic          │                  │
│  │(validate)│  validation        │                  │
│  └──────────┘                    │                  │
└──────────────────────────────────┼──────────────────┘
                                   │ HTTPS
                          ┌────────┴────────┐
                          │  MBTA V3 API    │
                          └─────────────────┘
```

**Backend** — Django 6.0 project (`mbta_project`) with a single app (`subway`).
There is no database; all transit data comes from the MBTA V3 API via the
`MBTA` class. A service layer (`services.py`) initializes the MBTA client once
at startup (~3 seconds), caches the result, and exposes wrapper functions.
Django views serve HTML pages and JSON API endpoints. All API responses are
validated through Pydantic schemas before serialization.

**Frontend** — Vanilla JavaScript (ES2022+) with Leaflet.js for interactive
maps. Two page-specific scripts (`app.js`, `map_facilities.js`) and a shared
utility module (`map_utils.js`) handle map rendering, API fetching, and popup
interactions. A single CSS stylesheet uses custom properties for theming and
responsive breakpoints.

**Project structure:**

```
mbta_project/              Django project settings, root URL config
subway/                    Django app
  MBTA_class.py            MBTA V3 API client (singleton)
  services.py              Service layer wrapping MBTA client
  schemas.py               Pydantic validation models
  views.py                 Page views and JSON API views
  urls.py                  URL routing
  tests.py                 Unit and integration tests
  static/subway/
    css/style.css           Stylesheet with CSS custom properties
    js/app.js               Trains & Alerts page logic
    js/map_facilities.js    Map & Facilities page logic
    js/map_utils.js         Shared Leaflet drawing utilities
  templates/subway/
    base.html               Base template with navigation
    trains_alerts.html      Trains & Alerts page
    map_facilities.html     Map & Facilities page
    about.html              About page
.env                       MBTA API key (not committed)
requirements.txt           Python dependencies
```

## Libraries and Versions

### Python (3.12)

| Library | Version | Purpose |
|---------|---------|---------|
| Django | 6.0.3 | Web framework — serves pages and JSON API endpoints |
| Pydantic | 2.12.5 | Data validation — schemas for API responses |
| requests | 2.32.5 | HTTP client — calls to the MBTA V3 API |
| python-dotenv | 1.2.2 | Environment variables — loads `.env` for API key |

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

| Library | Version | Purpose |
|---------|---------|---------|
| Leaflet.js | 1.9.4 | Interactive map rendering and controls |

## External Services

| Service | Purpose | Terms of Service |
|---------|---------|------------------|
| **MBTA V3 API** | Real-time subway data: lines, stations, alerts, predictions | [MBTA Developers License Agreement](https://www.mbta.com/developers/v3-api) |
| **OpenStreetMap** | Base map tile imagery | [ODbL License & Tile Usage Policy](https://www.openstreetmap.org/copyright) |
| **Leaflet.js** | Client-side map rendering library | [BSD 2-Clause License](https://github.com/Leaflet/Leaflet/blob/main/LICENSE) |

### Compliance Notes

- **MBTA V3 API**: Data is used in accordance with the
  [MassDOT Developers License Agreement](https://www.mass.gov/doc/massdot-developers-license-agreement-0/download).
  The API key is stored in a `.env` file and never exposed to end users or
  committed to version control. MBTA data attribution (linking to the API page)
  is displayed in the Leaflet attribution control on every map view.
- **OpenStreetMap**: "© OpenStreetMap contributors" attribution with a link to
  the [copyright page](https://www.openstreetmap.org/copyright) is displayed
  on every map view via Leaflet's built-in attribution control. Tile usage
  follows the OSM Foundation
  [tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
  Data is licensed under the
  [Open Data Commons Open Database License](https://opendatacommons.org/licenses/odbl/) (ODbL).
- **Leaflet.js**: Used under the
  [BSD 2-Clause License](https://github.com/Leaflet/Leaflet/blob/main/LICENSE).
  Loaded from the unpkg CDN with subresource integrity (SRI) hashes. Leaflet
  attribution is automatically shown in the map control.

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
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser. The root
URL redirects to the Trains & Alerts page.

> **Note**: The first page load takes ~3 seconds while the MBTA client
> initializes and caches line/station data. Subsequent requests are instant.

### Running Tests

```bash
source .venv/bin/activate
python manage.py test subway
```

> **Note**: There is no database, so `migrate` is not needed and will fail.
> Tests use Django's `SimpleTestCase`.

## API Endpoints

| Method | Path | Response |
|--------|------|----------|
| GET | `/api/lines/` | List of subway line names |
| GET | `/api/line/<name>/` | Line data (color, shapes, stations) |
| GET | `/api/line/<name>/alerts/` | Alerts for a line |
| GET | `/api/station/<id>/` | Station details (name, facilities, lines served) |
| GET | `/api/station/<id>/predictions/` | Train predictions for a station |

Line names support spaces via URL encoding (e.g. `/api/line/Red%20Line/`).
Invalid line names or station IDs return `404`. Server errors return `500`.
