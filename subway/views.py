import sys
import traceback

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from subway.schemas import LineSchema
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
