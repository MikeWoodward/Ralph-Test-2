from django.urls import path

from . import views

urlpatterns = [
    # Page routes
    path(
        "",
        views.trains_alerts,
        name="trains_alerts",
    ),
    path(
        "map/",
        views.map_facilities,
        name="map_facilities",
    ),
    path(
        "about/",
        views.about,
        name="about",
    ),
    # API routes
    path(
        "api/lines",
        views.api_lines,
        name="api_lines",
    ),
    path(
        "api/line/<str:line_name>",
        views.api_line,
        name="api_line",
    ),
    path(
        "api/alerts/<str:line_name>",
        views.api_alerts,
        name="api_alerts",
    ),
    path(
        "api/predictions/<str:station_id>",
        views.api_predictions,
        name="api_predictions",
    ),
    path(
        "api/station/<str:station_id>",
        views.api_station,
        name="api_station",
    ),
]
