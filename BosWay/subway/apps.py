"""App configuration for the subway app."""

from django.apps import AppConfig
from django.conf import settings


class SubwayConfig(AppConfig):
    """Configure startup behavior for the subway app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "subway"
    _startup_initialized = False

    def ready(
        self,
    ) -> None:
        """Initialize the shared MBTA client during app startup."""
        if self.__class__._startup_initialized:
            return

        if not getattr(settings, "MBTA_INITIALIZE_ON_STARTUP", True):
            return

        from .services import initialize_service

        initialize_service()
        self.__class__._startup_initialized = True
