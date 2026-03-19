"""Views for the MBTA subway app.

Page views return HTML responses (placeholder until templates are built).
API views return JSON responses backed by the service layer.
"""

from __future__ import annotations

import logging
import sys
import traceback

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from subway import services

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Page views
# ---------------------------------------------------------------------------

def trains_alerts_page(
    request: HttpRequest,
) -> HttpResponse:
    """Trains & Alerts page."""
    return render(
        request,
        "subway/trains_alerts.html",
        {"active_page": "trains-alerts"},
    )


def map_facilities_page(
    request: HttpRequest,
) -> HttpResponse:
    """Map & Facilities page."""
    return render(
        request,
        "subway/map_facilities.html",
        {"active_page": "map-facilities"},
    )


def about_page(
    request: HttpRequest,
) -> HttpResponse:
    """About page."""
    return render(
        request,
        "subway/about.html",
        {"active_page": "about"},
    )


# ---------------------------------------------------------------------------
# API views — line endpoints (story 3.2)
# ---------------------------------------------------------------------------

def api_lines(
    request: HttpRequest,
) -> JsonResponse:
    """Return a list of all subway line names.

    GET /api/lines/
    """
    try:
        line_names = services.get_line_names()
        return JsonResponse({"lines": line_names})
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        lineno = tb[-1].lineno if tb else "?"
        logger.exception(
            "Error fetching line names (line %s): %s",
            lineno,
            exc,
        )
        return JsonResponse(
            {"error": "Failed to fetch line names"},
            status=500,
        )


def api_line_detail(
    request: HttpRequest,
    line_name: str,
) -> JsonResponse:
    """Return line data (color, shapes, stations) for a given line.

    GET /api/line/<line_name>/

    Returns 404 if the line name is not found.
    """
    try:
        line = services.get_line(line_name=line_name)
        if line is None:
            return JsonResponse(
                {"error": f"Line '{line_name}' not found"},
                status=404,
            )
        return JsonResponse({
            "line_name": line_name,
            **line.model_dump(),
        })
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        lineno = tb[-1].lineno if tb else "?"
        logger.exception(
            "Error fetching line '%s' (line %s): %s",
            line_name,
            lineno,
            exc,
        )
        return JsonResponse(
            {"error": f"Failed to fetch line '{line_name}'"},
            status=500,
        )


def api_line_alerts(
    request: HttpRequest,
    line_name: str,
) -> JsonResponse:
    """Return alerts for a given line.

    GET /api/line/<line_name>/alerts/

    Returns the alerts array even if empty (not a 404).
    Returns 404 only if the line name itself is invalid.
    """
    try:
        if services.get_line(line_name=line_name) is None:
            return JsonResponse(
                {"error": f"Line '{line_name}' not found"},
                status=404,
            )
        alerts = services.get_line_alerts(line_name=line_name)
        return JsonResponse({
            "line_name": line_name,
            "alerts": [alert.model_dump() for alert in alerts],
        })
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        lineno = tb[-1].lineno if tb else "?"
        logger.exception(
            "Error fetching alerts for '%s' (line %s): %s",
            line_name,
            lineno,
            exc,
        )
        return JsonResponse(
            {"error": f"Failed to fetch alerts for '{line_name}'"},
            status=500,
        )


# ---------------------------------------------------------------------------
# API views — station endpoints (story 3.3)
# ---------------------------------------------------------------------------

def api_station_detail(
    request: HttpRequest,
    station_id: str,
) -> JsonResponse:
    """Return station details for a given station ID.

    GET /api/station/<station_id>/

    Returns 404 if the station ID is not found.
    """
    try:
        station = services.get_station(station_id=station_id)
        if station is None:
            return JsonResponse(
                {"error": f"Station '{station_id}' not found"},
                status=404,
            )
        return JsonResponse(station.model_dump())
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        lineno = tb[-1].lineno if tb else "?"
        logger.exception(
            "Error fetching station '%s' (line %s): %s",
            station_id,
            lineno,
            exc,
        )
        return JsonResponse(
            {"error": f"Failed to fetch station '{station_id}'"},
            status=500,
        )


def api_station_predictions(
    request: HttpRequest,
    station_id: str,
) -> JsonResponse:
    """Return predictions for a given station ID.

    GET /api/station/<station_id>/predictions/

    Validates the station exists first (404 if not), then returns
    the predictions array (which may be empty).
    """
    try:
        if services.get_station(station_id=station_id) is None:
            return JsonResponse(
                {"error": f"Station '{station_id}' not found"},
                status=404,
            )
        predictions = services.get_predictions(
            station_id=station_id,
        )
        return JsonResponse({
            "station_id": station_id,
            "predictions": [
                pred.model_dump() for pred in predictions
            ],
        })
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        lineno = tb[-1].lineno if tb else "?"
        logger.exception(
            "Error fetching predictions for '%s' (line %s): %s",
            station_id,
            lineno,
            exc,
        )
        return JsonResponse(
            {
                "error": (
                    f"Failed to fetch predictions for"
                    f" '{station_id}'"
                ),
            },
            status=500,
        )
