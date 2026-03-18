from django.urls import path

from . import views

urlpatterns = [
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
]
