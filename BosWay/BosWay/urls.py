"""Root URL routing for the BosWay project."""

from django.urls import include
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path(
        "",
        RedirectView.as_view(
            pattern_name="subway:trains_alerts",
            permanent=False,
        ),
        name="home",
    ),
    path("", include("subway.urls")),
]
