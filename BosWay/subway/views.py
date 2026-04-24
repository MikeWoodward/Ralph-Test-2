"""Page views for the BosWay subway app."""

from django.http import HttpRequest
from django.http import HttpResponse
from django.shortcuts import render


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
