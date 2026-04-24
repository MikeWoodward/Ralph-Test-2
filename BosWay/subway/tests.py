"""Focused tests for the BosWay project scaffold."""

import importlib
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.test import override_settings
from django.urls import NoReverseMatch
from django.urls import reverse

from subway import services
from subway.apps import SubwayConfig


class ProjectSetupTest(SimpleTestCase):
    """Verify the project configuration stories completed so far."""

    def test_root_redirects_to_trains_alerts(self) -> None:
        """Ensure the root URL opens the trains and alerts page."""
        response = self.client.get("/")

        self.assertRedirects(
            response,
            reverse("subway:trains_alerts"),
            fetch_redirect_response=False,
        )

    def test_trains_alerts_page_renders_template(self) -> None:
        """Ensure the trains and alerts page renders successfully."""
        response = self.client.get(reverse("subway:trains_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "subway/trains_alerts.html",
        )
        self.assertContains(response, "BosWay - trains &amp; alerts")

    def test_static_asset_is_registered(self) -> None:
        """Ensure the app stylesheet can be resolved by staticfiles."""
        self.assertIsNotNone(finders.find("subway/css/style.css"))

    def test_project_template_and_static_dirs_are_configured(self) -> None:
        """Ensure the project-level template and static directories exist."""
        self.assertIn(
            settings.BASE_DIR / "templates",
            settings.TEMPLATES[0]["DIRS"],
        )
        self.assertIn(
            settings.BASE_DIR / "static",
            settings.STATICFILES_DIRS,
        )

    def test_database_is_disabled(self) -> None:
        """Ensure the app does not depend on a configured database."""
        self.assertEqual(
            settings.DATABASES["default"]["ENGINE"],
            "django.db.backends.dummy",
        )

    def test_database_backed_apps_are_not_installed(self) -> None:
        """Ensure unused database-backed Django apps stay disabled."""
        self.assertNotIn("django.contrib.admin", settings.INSTALLED_APPS)
        self.assertNotIn("django.contrib.auth", settings.INSTALLED_APPS)
        self.assertNotIn(
            "django.contrib.contenttypes",
            settings.INSTALLED_APPS,
        )
        self.assertNotIn("django.contrib.sessions", settings.INSTALLED_APPS)

    def test_admin_urls_are_not_registered(self) -> None:
        """Ensure admin routes stay unavailable without admin support."""
        with self.assertRaises(NoReverseMatch):
            reverse("admin:index")


class ServiceBootstrapTest(SimpleTestCase):
    """Verify shared MBTA service bootstrapping behavior."""

    def setUp(
        self,
    ) -> None:
        """Reset shared singleton state before each test."""
        services._MBTA_CLASS = None
        services._MBTA_SERVICE = None
        services._MBTA_INITIALIZED = False
        SubwayConfig._startup_initialized = False

    def tearDown(
        self,
    ) -> None:
        """Reset shared singleton state after each test."""
        self.setUp()

    def test_repo_environment_loads_from_repo_root(self) -> None:
        """Ensure dotenv loading targets the repo-root configuration file."""
        with patch("subway.services.load_dotenv") as load_dotenv_mock:
            services._load_repo_environment()

        load_dotenv_mock.assert_called_once_with(
            dotenv_path=Path(settings.BASE_DIR).parent / ".env",
            override=False,
        )

    def test_get_mbta_service_returns_singleton_instance(self) -> None:
        """Ensure repeated access reuses one MBTA client instance."""
        fake_mbta_class = self._build_fake_mbta_class()

        with patch("subway.services._load_repo_environment"):
            with patch(
                "subway.services._load_mbta_class",
                return_value=fake_mbta_class,
            ):
                first_instance = services.get_mbta_service()
                second_instance = services.get_mbta_service()

        self.assertIs(first_instance, second_instance)
        self.assertEqual(fake_mbta_class.instances_created, 1)

    def test_initialize_service_runs_only_once(self) -> None:
        """Ensure startup initialization does not run more than once."""
        fake_mbta_class = self._build_fake_mbta_class()

        with patch("subway.services._load_repo_environment"):
            with patch(
                "subway.services._load_mbta_class",
                return_value=fake_mbta_class,
            ):
                first_instance = services.initialize_service()
                second_instance = services.initialize_service()

        self.assertIs(first_instance, second_instance)
        self.assertEqual(fake_mbta_class.initialize_calls, 1)

    @override_settings(MBTA_INITIALIZE_ON_STARTUP=True)
    def test_app_ready_initializes_service_once(self) -> None:
        """Ensure the app config triggers startup init once per process."""
        subway_module = importlib.import_module("subway")
        subway_app = SubwayConfig("subway", subway_module)

        with patch("subway.services.initialize_service") as initialize_mock:
            subway_app.ready()
            subway_app.ready()

        initialize_mock.assert_called_once_with()

    @staticmethod
    def _build_fake_mbta_class() -> type[object]:
        """Create a fake MBTA class for singleton tests.

        Returns:
            A fake MBTA class with instance and initialization counters.
        """

        class FakeMBTA:
            """Minimal stand-in for the real MBTA client."""

            instances_created = 0
            initialize_calls = 0

            def __init__(
                self,
            ) -> None:
                """Track client construction count."""
                type(self).instances_created += 1

            def initialize(
                self,
            ) -> None:
                """Track initialization count."""
                type(self).initialize_calls += 1

        return FakeMBTA
