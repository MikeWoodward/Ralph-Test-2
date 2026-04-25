"""Views for the BosWay subway app."""

import logging
import traceback

from django.http import JsonResponse
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render

from . import services

LOGGER = logging.getLogger(__name__)


def _build_page_context(
    *,
    page_title: str,
    active_page: str,
) -> dict[str, str]:
    """Build the shared template context for page views.

    Args:
        page_title: The page label to display in the document title.
        active_page: The navigation key for the active page.

    Returns:
        The shared template context for page rendering.
    """
    return {
        "page_title": page_title,
        "active_page": active_page,
    }


def _log_view_exception(
    *,
    exception: Exception,
) -> None:
    """Log the line number and source text for an unhandled view error.

    Args:
        exception: The exception raised while serving the request.
    """
    traceback_summary = traceback.extract_tb(exception.__traceback__)
    if not traceback_summary:
        LOGGER.exception("Unhandled subway view error.")
        return

    failing_frame = traceback_summary[-1]
    LOGGER.exception(
        "Unhandled subway view error at line %s: %s",
        failing_frame.lineno,
        failing_frame.line,
    )


def _validate_line_name_request(
    *,
    line_name: str,
) -> JsonResponse | None:
    """Validate a public subway line-name request parameter.

    Args:
        line_name: The subway line display name from the URL.

    Returns:
        A JSON error response for invalid input, or `None` when valid.
    """
    if not services.is_public_line_name_format_valid(line_name=line_name):
        return JsonResponse(
            {"error": "Invalid line name."},
            status=400,
        )

    if not services.line_exists(line_name=line_name):
        return JsonResponse(
            {"error": "Line not found."},
            status=404,
        )

    return None


def _validate_station_id_request(
    *,
    station_id: str,
) -> JsonResponse | None:
    """Validate a public station-id request parameter.

    Args:
        station_id: The MBTA station identifier from the URL.

    Returns:
        A JSON error response for invalid input, or `None` when valid.
    """
    if not services.is_public_station_id_format_valid(
        station_id=station_id,
    ):
        return JsonResponse(
            {"error": "Invalid station ID."},
            status=400,
        )

    if not services.station_exists(station_id=station_id):
        return JsonResponse(
            {"error": "Station not found."},
            status=404,
        )

    return None


def trains_alerts(
    request: HttpRequest,
) -> HttpResponse:
    """Render the Trains and Alerts page.

    Args:
        request: The incoming Django request.

    Returns:
        The rendered trains and alerts page response.
    """
    return render(
        request,
        "subway/trains_alerts.html",
        _build_page_context(
            page_title="trains & alerts",
            active_page="trains_alerts",
        ),
    )


def map_facilities(
    request: HttpRequest,
) -> HttpResponse:
    """Render the Map and Facilities page.

    Args:
        request: The incoming Django request.

    Returns:
        The rendered map and facilities page response.
    """
    return render(
        request,
        "subway/map_facilities.html",
        _build_page_context(
            page_title="map & facilities",
            active_page="map_facilities",
        ),
    )


def about(
    request: HttpRequest,
) -> HttpResponse:
    """Render the About page.

    Args:
        request: The incoming Django request.

    Returns:
        The rendered about page response.
    """
    return render(
        request,
        "subway/about.html",
        _build_page_context(
            page_title="about",
            active_page="about",
        ),
    )


def line_names(
    request: HttpRequest,
) -> JsonResponse:
    """Return the subway line names for frontend page-load requests.

    Args:
        request: The incoming Django request.

    Returns:
        A JSON array of subway line display names.
    """
    _ = request
    try:
        line_names_list = services.get_line_names()
    except Exception as error:  # pragma: no cover - exercised via tests
        _log_view_exception(exception=error)
        return JsonResponse(
            {"error": "Unable to load line names."},
            status=500,
        )

    return JsonResponse(
        line_names_list,
        safe=False,
    )


def line_detail(
    request: HttpRequest,
    line_name: str,
) -> JsonResponse:
    """Return geometry and station data for one subway line.

    Args:
        request: The incoming Django request.
        line_name: The subway line display name from the URL.

    Returns:
        A JSON response containing one validated line payload.
    """
    _ = request
    try:
        if (
            validation_response := _validate_line_name_request(
                line_name=line_name,
            )
        ) is not None:
            return validation_response

        line = services.get_line(line_name=line_name)
    except Exception as error:  # pragma: no cover - exercised via tests
        _log_view_exception(exception=error)
        return JsonResponse(
            {"error": "Unable to load line details."},
            status=500,
        )

    if line is None:
        return JsonResponse(
            {"error": "Line not found."},
            status=404,
        )

    return JsonResponse(
        line.model_dump(mode="json"),
    )


def line_alerts(
    request: HttpRequest,
    line_name: str,
) -> JsonResponse:
    """Return alert data for one subway line.

    Args:
        request: The incoming Django request.
        line_name: The subway line display name from the URL.

    Returns:
        A JSON array of validated alert payloads.
    """
    _ = request
    try:
        if (
            validation_response := _validate_line_name_request(
                line_name=line_name,
            )
        ) is not None:
            return validation_response

        alerts = services.get_line_alerts(line_name=line_name)
    except Exception as error:  # pragma: no cover - exercised via tests
        _log_view_exception(exception=error)
        return JsonResponse(
            {"error": "Unable to load line alerts."},
            status=500,
        )

    return JsonResponse(
        [
            alert.model_dump(mode="json")
            for alert in alerts
        ],
        safe=False,
    )


def station_detail(
    request: HttpRequest,
    station_id: str,
) -> JsonResponse:
    """Return facility-backed detail data for one subway station.

    Args:
        request: The incoming Django request.
        station_id: The MBTA station identifier from the URL.

    Returns:
        A JSON response containing one validated station payload.
    """
    _ = request
    try:
        if (
            validation_response := _validate_station_id_request(
                station_id=station_id,
            )
        ) is not None:
            return validation_response

        station = services.get_station(station_id=station_id)
    except Exception as error:  # pragma: no cover - exercised via tests
        _log_view_exception(exception=error)
        return JsonResponse(
            {"error": "Unable to load station details."},
            status=500,
        )

    if station is None:
        return JsonResponse(
            {"error": "Station not found."},
            status=404,
        )

    return JsonResponse(
        station.model_dump(mode="json"),
    )


def station_predictions(
    request: HttpRequest,
    station_id: str,
) -> JsonResponse:
    """Return prediction rows for one subway station.

    Args:
        request: The incoming Django request.
        station_id: The MBTA station identifier from the URL.

    Returns:
        A JSON array of validated prediction payloads.
    """
    _ = request
    try:
        if (
            validation_response := _validate_station_id_request(
                station_id=station_id,
            )
        ) is not None:
            return validation_response

        predictions = services.get_predictions(station_id=station_id)
    except Exception as error:  # pragma: no cover - exercised via tests
        _log_view_exception(exception=error)
        return JsonResponse(
            {"error": "Unable to load station predictions."},
            status=500,
        )

    return JsonResponse(
        [
            prediction.model_dump(mode="json")
            for prediction in predictions
        ],
        safe=False,
    )
