"""Views for the BosWay subway app."""

from django.http import JsonResponse
from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render

from . import services


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
