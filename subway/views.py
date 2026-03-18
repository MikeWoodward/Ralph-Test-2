from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

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
