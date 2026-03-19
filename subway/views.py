"""Views for the MBTA subway app.

Page views return HTML responses (placeholder until templates are built).
API views return JSON responses (placeholder until the service layer exists).
"""

from django.http import HttpResponse, JsonResponse


# ---------------------------------------------------------------------------
# Page views — placeholders until templates exist (stories 4.x / 5.x)
# ---------------------------------------------------------------------------

def trains_alerts_page(
    request,
) -> HttpResponse:
    """Trains & Alerts page."""
    return HttpResponse(
        "<h1>Trains &amp; Alerts</h1><p>Coming soon.</p>",
        content_type="text/html",
    )


def map_facilities_page(
    request,
) -> HttpResponse:
    """Map & Facilities page."""
    return HttpResponse(
        "<h1>Map &amp; Facilities</h1><p>Coming soon.</p>",
        content_type="text/html",
    )


def about_page(
    request,
) -> HttpResponse:
    """About page."""
    return HttpResponse(
        "<h1>About</h1><p>Coming soon.</p>",
        content_type="text/html",
    )


# ---------------------------------------------------------------------------
# API views — stubs until the service layer is wired up (stories 3.x)
# ---------------------------------------------------------------------------

def api_lines(
    request,
) -> JsonResponse:
    """Return a list of all subway line names.

    GET /api/lines/
    """
    return JsonResponse(
        {"lines": []},
    )


def api_line_detail(
    request,
    line_name: str,
) -> JsonResponse:
    """Return line data (color, shapes, stations) for a given line.

    GET /api/line/<line_name>/
    """
    return JsonResponse(
        {"line_name": line_name, "line_color": "", "shapes": [], "stations": []},
    )


def api_line_alerts(
    request,
    line_name: str,
) -> JsonResponse:
    """Return alerts for a given line.

    GET /api/line/<line_name>/alerts/
    """
    return JsonResponse(
        {"line_name": line_name, "alerts": []},
    )


def api_station_detail(
    request,
    station_id: str,
) -> JsonResponse:
    """Return station details for a given station ID.

    GET /api/station/<station_id>/
    """
    return JsonResponse(
        {
            "id": station_id,
            "name": "",
            "latitude": 0.0,
            "longitude": 0.0,
            "address": None,
            "facilities": [],
            "lines_served": [],
        },
    )


def api_station_predictions(
    request,
    station_id: str,
) -> JsonResponse:
    """Return predictions for a given station ID.

    GET /api/station/<station_id>/predictions/
    """
    return JsonResponse(
        {"station_id": station_id, "predictions": []},
    )
