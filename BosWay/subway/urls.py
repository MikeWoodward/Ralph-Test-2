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
        "trains-alerts",
        views.trains_alerts,
        name="trains_alerts",
    ),
]
