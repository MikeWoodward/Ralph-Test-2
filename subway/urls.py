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
]
