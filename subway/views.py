import sys
import traceback

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from subway.schemas import (
    AlertSchema,
    LineSchema,
    PredictionSchema,
    StationSchema,
)
from subway.services import get_mbta


def trains_alerts(
    request: HttpRequest,
) -> HttpResponse:
    """Render the Trains & Alerts page."""
    return render(
        request=request,
        template_name="subway/trains_alerts.html",
        context={"active_tab": "trains"},
    )


def map_facilities(
    request: HttpRequest,
) -> HttpResponse:
    """Render the Map & Facilities page."""
    return render(
        request=request,
        template_name="subway/map_facilities.html",
        context={"active_tab": "map"},
    )


def about(
    request: HttpRequest,
) -> HttpResponse:
    """Render the About page."""
    return render(
        request=request,
        template_name="subway/about.html",
        context={"active_tab": "about"},
    )


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


def api_lines(
    request: HttpRequest,
) -> JsonResponse:
    """Return all subway line names as a JSON array.

    Returns:
        JsonResponse with a list of line name strings,
        or an error object on failure.
    """
    try:
        mbta = get_mbta()
        line_names: list[str] = mbta.get_line_names()
        return JsonResponse(
            data=line_names,
            safe=False,
        )
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line_no = tb[-1].lineno if tb else "unknown"
        return JsonResponse(
            data={
                "error": str(exc),
                "line": line_no,
            },
            status=500,
        )


def api_line(
    request: HttpRequest,
    line_name: str,
) -> JsonResponse:
    """Return line color, shapes, and stations for a given subway line.

    Args:
        request: The HTTP request object.
        line_name: Display name of the line (e.g. "Red Line").

    Returns:
        JsonResponse with line_color, shapes, and stations,
        or a 404/500 error object on failure.
    """
    try:
        mbta = get_mbta()
        line_data = mbta.get_line(line_name=line_name)

        if line_data is None:
            return JsonResponse(
                data={"error": f"Line '{line_name}' not found"},
                status=404,
            )

        validated = LineSchema(**line_data)
        return JsonResponse(
            data=validated.model_dump(),
        )
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line_no = tb[-1].lineno if tb else "unknown"
        return JsonResponse(
            data={
                "error": str(exc),
                "line": line_no,
            },
            status=500,
        )


def api_alerts(
    request: HttpRequest,
    line_name: str,
) -> JsonResponse:
    """Return current alerts for a given subway line as a JSON array.

    Args:
        request: The HTTP request object.
        line_name: Display name of the line (e.g. "Red Line").

    Returns:
        JsonResponse with a list of alert objects (headline, severity),
        or an error object on failure.
    """
    try:
        mbta = get_mbta()
        raw_alerts = mbta.get_line_alerts(line_name=line_name)

        alerts = [
            AlertSchema(
                headline=alert["attributes"]["header"],
                severity=alert["attributes"]["severity"],
            ).model_dump()
            for alert in raw_alerts
        ]

        return JsonResponse(
            data=alerts,
            safe=False,
        )
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line_no = tb[-1].lineno if tb else "unknown"
        return JsonResponse(
            data={
                "error": str(exc),
                "line": line_no,
            },
            status=500,
        )


def api_predictions(
    request: HttpRequest,
    station_id: str,
) -> JsonResponse:
    """Return arrival predictions for a given station as a JSON array.

    Args:
        request: The HTTP request object.
        station_id: MBTA stop ID (e.g. "place-knncl").

    Returns:
        JsonResponse with a list of prediction objects
        (route, destination, arrival_time, departure_time, comments),
        or an error object on failure.
    """
    try:
        mbta = get_mbta()
        raw_predictions = mbta.get_predictions(station_id=station_id)

        predictions = [
            PredictionSchema(**prediction).model_dump()
            for prediction in raw_predictions
        ]

        return JsonResponse(
            data=predictions,
            safe=False,
        )
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line_no = tb[-1].lineno if tb else "unknown"
        return JsonResponse(
            data={
                "error": str(exc),
                "line": line_no,
            },
            status=500,
        )


def api_station(
    request: HttpRequest,
    station_id: str,
) -> JsonResponse:
    """Return station details including facilities for a given station.

    Args:
        request: The HTTP request object.
        station_id: MBTA stop ID (e.g. "place-knncl").

    Returns:
        JsonResponse with station name, coordinates, and facilities,
        or a 404/500 error object on failure.
    """
    try:
        mbta = get_mbta()
        station_data = mbta.get_station(station_id=station_id)

        if station_data is None:
            return JsonResponse(
                data={"error": f"Station '{station_id}' not found"},
                status=404,
            )

        station_data["station_id"] = station_data.pop("id")
        validated = StationSchema(**station_data)
        return JsonResponse(
            data=validated.model_dump(),
        )
    except Exception as exc:
        tb = traceback.extract_tb(sys.exc_info()[2])
        line_no = tb[-1].lineno if tb else "unknown"
        return JsonResponse(
            data={
                "error": str(exc),
                "line": line_no,
            },
            status=500,
        )
