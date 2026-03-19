"""URL configuration for the subway app.

Page views:
    /                           → redirect to /trains-alerts/
    /trains-alerts/             → Trains & Alerts page
    /map-facilities/            → Map & Facilities page
    /about/                     → About page

API endpoints:
    /api/lines/                          → list of all line names
    /api/line/<line_name>/               → line data (color, shapes, stations)
    /api/line/<line_name>/alerts/        → alerts for a line
    /api/station/<station_id>/           → station details
    /api/station/<station_id>/predictions/ → predictions for a station
"""

from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "subway"

urlpatterns = [
    # Root redirect
    path(
        "",
        RedirectView.as_view(
            pattern_name="subway:trains-alerts",
            permanent=False,
        ),
        name="index",
    ),
    # Page views
    path(
        "trains-alerts/",
        views.trains_alerts_page,
        name="trains-alerts",
    ),
    path(
        "map-facilities/",
        views.map_facilities_page,
        name="map-facilities",
    ),
    path(
        "about/",
        views.about_page,
        name="about",
    ),
    # API endpoints
    path(
        "api/lines/",
        views.api_lines,
        name="api-lines",
    ),
    path(
        "api/line/<str:line_name>/",
        views.api_line_detail,
        name="api-line-detail",
    ),
    path(
        "api/line/<str:line_name>/alerts/",
        views.api_line_alerts,
        name="api-line-alerts",
    ),
    path(
        "api/station/<str:station_id>/",
        views.api_station_detail,
        name="api-station-detail",
    ),
    path(
        "api/station/<str:station_id>/predictions/",
        views.api_station_predictions,
        name="api-station-predictions",
    ),
]
