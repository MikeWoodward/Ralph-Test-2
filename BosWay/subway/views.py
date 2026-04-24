"""Views for the BosWay subway app."""

import logging
import traceback

from django.http import JsonResponse
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render

from . import services

LOGGER = logging.getLogger(__name__)


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
        {
            "page_title": "trains & alerts",
        },
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
    return JsonResponse(
        services.get_line_names(),
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
