"""Focused tests for the BosWay project scaffold."""

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.urls import reverse


class ProjectSetupTest(SimpleTestCase):
    """Verify the story 1.1 Django project scaffold."""

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
