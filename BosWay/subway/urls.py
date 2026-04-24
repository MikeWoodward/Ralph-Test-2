"""URL patterns for the BosWay subway app."""

from django.urls import path

from . import views

app_name = "subway"

urlpatterns = [
    path(
        "api/lines",
        views.line_names,
        name="line_names",
    ),
    path(
        "api/lines/<str:line_name>",
        views.line_detail,
        name="line_detail",
    ),
    path(
        "api/lines/<str:line_name>/alerts",
        views.line_alerts,
        name="line_alerts",
    ),
    path(
        "api/stations/<str:station_id>",
        views.station_detail,
        name="station_detail",
    ),
    path(
        "api/stations/<str:station_id>/predictions",
        views.station_predictions,
        name="station_predictions",
    ),
    path(
        "trains-alerts",
        views.trains_alerts,
        name="trains_alerts",
    ),
    path(
        "map-facilities",
        views.map_facilities,
        name="map_facilities",
    ),
    path(
        "about",
        views.about,
        name="about",
    ),
]
