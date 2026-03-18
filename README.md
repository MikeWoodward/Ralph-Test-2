# MBTA Subway Explorer

A web application for viewing real-time train predictions, service alerts,
station facilities, and interactive subway maps for the Massachusetts Bay
Transportation Authority (MBTA) rapid transit system.

**Author:** Mike Woodward

## Architecture

The app is built with a **Django** backend serving a **vanilla JavaScript**
frontend. There are no JavaScript build tools or frontend frameworks — the
browser loads a single `app.js` file and interacts with Django API endpoints
via `fetch()`.

```
┌────────────────────────────────────────────────────────┐
│  Browser (vanilla JS + Leaflet.js)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Trains &     │  │ Map &        │  │ About        │ │
│  │ Alerts       │  │ Facilities   │  │              │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘ │
│         │ fetch()         │ fetch()                    │
└─────────┼─────────────────┼────────────────────────────┘
          ▼                 ▼
┌────────────────────────────────────────────────────────┐
│  Django REST API                                       │
│  GET /api/lines          — all subway line names       │
│  GET /api/line/<name>    — line color, shapes, stations│
│  GET /api/alerts/<name>  — current alerts for a line   │
│  GET /api/predictions/<id> — arrival predictions       │
│  GET /api/station/<id>   — station details & facilities│
└──────────────────────┬─────────────────────────────────┘
                       │ requests
                       ▼
              ┌─────────────────┐
              │  MBTA V3 API    │
              │  (mbta.com)     │
              └─────────────────┘
```

### Project Structure

```
Ralph-Test-2/
├── mbta_project/           # Django project settings, root URL conf, WSGI/ASGI
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── subway/                 # Main Django app
│   ├── MBTA_class.py       # MBTA API client wrapper
│   ├── services.py         # Thread-safe MBTA singleton (get_mbta())
│   ├── schemas.py          # Pydantic validation models
│   ├── views.py            # Page views + API endpoints
│   ├── urls.py             # App URL routing
│   ├── templates/subway/   # Django HTML templates
│   │   ├── base.html       # Shared layout with tab navigation + Leaflet CDN
│   │   ├── trains_alerts.html
│   │   ├── map_facilities.html
│   │   └── about.html
│   └── static/subway/
│       ├── css/style.css   # App-wide stylesheet
│       └── js/app.js       # All client-side interactivity
├── manage.py
├── requirements.txt
└── .env                    # MBTA API key (not committed)
```

## Setup

### Prerequisites

- Python 3.12+
- An MBTA V3 API key ([request one here](https://api-v3.mbta.com/register))

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd Ralph-Test-2

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root with your MBTA API key:

```
MBTA_API_KEY=your_api_key_here
```

### Running the Dev Server

```bash
source .venv/bin/activate
python manage.py runserver
```

The app will be available at [http://localhost:8000](http://localhost:8000).

> **Note:** The first request takes ~4–5 seconds while the MBTA API client
> initializes and caches subway line data. Subsequent requests are instant.

## Libraries

### Python

| Library | Version | Purpose |
|---------|---------|---------|
| [Django](https://www.djangoproject.com/) | 6.0.3 | Web framework — routing, templates, static files |
| [Pydantic](https://docs.pydantic.dev/) | 2.12.5 | Data validation for API request/response schemas |
| [Requests](https://docs.python-requests.org/) | 2.32.5 | HTTP client for MBTA V3 API calls |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.2 | Load `.env` file for API key configuration |

### JavaScript (CDN)

| Library | Version | Purpose |
|---------|---------|---------|
| [Leaflet.js](https://leafletjs.com/) | 1.9.4 | Interactive map rendering, markers, popups, controls |

### Runtime

| Dependency | Version |
|------------|---------|
| Python | 3.12+ |

## External Services

| Service | Usage | Links |
|---------|-------|-------|
| **MBTA V3 API** | Real-time subway data: train predictions, service alerts, station info, route geometry | [Developer Portal](https://www.mbta.com/developers/v3-api) · [Terms of Use](https://www.mbta.com/policies/terms-use) |
| **OpenStreetMap** | Map tile layer for all interactive maps | [openstreetmap.org](https://www.openstreetmap.org/) · [Terms of Use](https://wiki.osmfoundation.org/wiki/Terms_of_Use) |
| **Leaflet.js** | Open-source JS library for mobile-friendly interactive maps | [leafletjs.com](https://leafletjs.com/) · [BSD 2-Clause License](https://github.com/Leaflet/Leaflet/blob/main/LICENSE) |

## License

See [LICENSE](LICENSE) for details.
