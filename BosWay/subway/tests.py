"""Focused tests for the BosWay project scaffold."""

from datetime import UTC
from datetime import datetime
import importlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import JsonResponse
from django.test import SimpleTestCase
from django.test import override_settings
from django.urls import NoReverseMatch
from django.urls import reverse
from pydantic import ValidationError

from subway import services
from subway.apps import SubwayConfig
from subway.chrome_test_runner import ChromeTestResult
from subway.chrome_test_runner import ChromeTestRun
from subway.chrome_test_runner import write_chrome_test_artifacts
from subway.schemas import AlertSchema
from subway.schemas import FacilitySchema
from subway.schemas import LineSchema
from subway.schemas import PredictionSchema
from subway.schemas import StationDetailSchema
from subway.schemas import StationSummarySchema


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


class SharedPageLayoutTest(SimpleTestCase):
    """Verify the shared BosWay layout for user-facing pages."""

    def test_trains_alerts_page_uses_shared_navigation(self) -> None:
        """Ensure the trains page shows the shared title and nav links."""
        response = self.client.get(reverse("subway:trains_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BosWay - trains &amp; alerts")
        self.assertContains(
            response,
            'href="/trains-alerts"',
        )
        self.assertContains(
            response,
            'href="/map-facilities"',
        )
        self.assertContains(
            response,
            'href="/about"',
        )
        self.assertContains(
            response,
            'site-nav__link--active',
        )

    def test_map_facilities_page_renders_shared_layout(self) -> None:
        """Ensure the map page renders with the shared layout."""
        response = self.client.get(reverse("subway:map_facilities"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "subway/map_facilities.html",
        )
        self.assertContains(response, "BosWay - map &amp; facilities")
        self.assertContains(response, "map &amp; facilities")
        self.assertContains(
            response,
            'href="/trains-alerts"',
        )
        self.assertContains(
            response,
            'href="/about"',
        )

    def test_about_page_renders_shared_layout(self) -> None:
        """Ensure the about page renders with the shared layout."""
        response = self.client.get(reverse("subway:about"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "subway/about.html",
        )
        self.assertContains(response, "BosWay - about")
        self.assertContains(
            response,
            '<h1 class="page-title">about</h1>',
            html=True,
        )
        self.assertContains(
            response,
            'href="/trains-alerts"',
        )
        self.assertContains(
            response,
            'href="/map-facilities"',
        )

    def test_about_page_shows_story_4_1_content(self) -> None:
        """Ensure the About page includes credits and MBTA acknowledgment."""
        response = self.client.get(reverse("subway:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mike Woodward")
        self.assertContains(response, "MBTA V3 API")
        self.assertContains(response, "OpenStreetMap")
        self.assertContains(response, "Leaflet.js")
        self.assertContains(
            response,
            "Massachusetts Bay Transportation Authority data",
        )
        self.assertContains(
            response,
            'href="https://www.mbta.com/schedules/subway"',
        )

    def test_shared_layout_includes_favicon(self) -> None:
        """Ensure every shared page references the app favicon asset."""
        response = self.client.get(reverse("subway:trains_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'rel="icon"',
        )
        self.assertContains(
            response,
            'href="/static/subway/favicon.svg"',
        )


class MapFacilitiesPageTest(SimpleTestCase):
    """Verify the Map and Facilities page network map experience."""

    def test_page_renders_map_container_and_leaflet_assets(self) -> None:
        """Ensure the page includes its map, legend, and Leaflet assets."""
        response = self.client.get(reverse("subway:map_facilities"))
        script_path = finders.find("subway/js/map_facilities.js")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(script_path)
        self.assertContains(
            response,
            'id="map-facilities-map"',
        )
        self.assertContains(
            response,
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        )
        self.assertContains(
            response,
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
        )
        self.assertContains(
            response,
            'src="/static/subway/js/map_facilities.js"',
        )
        self.assertContains(
            response,
            'src="/static/subway/js/map_styles.js"',
        )
        self.assertContains(
            response,
            'id="map-facilities-legend-items"',
        )
        self.assertContains(
            response,
            "Subway lines",
        )

    def test_stylesheet_gives_the_page_a_full_width_map_layout(self) -> None:
        """Ensure the page-specific CSS positions the map and legend."""
        stylesheet_path = finders.find("subway/css/style.css")

        self.assertIsNotNone(stylesheet_path)
        stylesheet_text = Path(stylesheet_path).read_text(encoding="utf-8")

        self.assertIn(".map-facilities-page {", stylesheet_text)
        self.assertIn(".map-facilities-page__map-shell {", stylesheet_text)
        self.assertIn(".map-facilities-page__map {", stylesheet_text)
        self.assertIn("min-height: 75vh;", stylesheet_text)
        self.assertIn(".map-facilities-page__legend {", stylesheet_text)
        self.assertIn("position: absolute;", stylesheet_text)
        self.assertIn("pointer-events: none;", stylesheet_text)
        self.assertIn(".map-facilities-page__legend-swatch {", stylesheet_text)

    def test_script_fetches_all_lines_draws_network_and_fits_bounds(
        self,
    ) -> None:
        """Ensure startup JS renders the full system and legend together."""
        script_path = finders.find("subway/js/map_facilities.js")

        self.assertIsNotNone(script_path)
        script_text = Path(script_path).read_text(encoding="utf-8")

        self.assertIn("const LINE_NAMES_ENDPOINT = ", script_text)
        self.assertIn("const parseLineDetailPayload = ", script_text)
        self.assertIn("Promise.allSettled(", script_text)
        self.assertIn("fetchLineDetail({ lineName })", script_text)
        self.assertIn("window.L.polyline", script_text)
        self.assertIn("window.L.circleMarker", script_text)
        self.assertIn("createLineStyle({ color: lineColor })", script_text)
        self.assertIn(
            "createStationMarkerStyle({ color: lineColor })",
            script_text,
        )
        self.assertIn("window.L.featureGroup(renderedLayers)", script_text)
        self.assertIn("mapFacilitiesMap.fitBounds(", script_text)
        self.assertIn("networkLayerGroup.getBounds()", script_text)
        self.assertIn("const buildLegendEntries = ", script_text)
        self.assertIn(
            '#map-facilities-legend-items',
            script_text,
        )
        self.assertIn("legendSwatch.style.backgroundColor", script_text)
        self.assertIn("renderLegend({ lineDetails: validLineDetails });", script_text)

    def test_shared_map_styles_define_mbta_line_and_station_options(
        self,
    ) -> None:
        """Ensure both map pages share one MBTA visual styling contract."""
        script_path = finders.find("subway/js/map_styles.js")

        self.assertIsNotNone(script_path)
        script_text = Path(script_path).read_text(encoding="utf-8")

        self.assertIn("window.BosWayMapStyles = Object.freeze({", script_text)
        self.assertIn("const LINE_WEIGHT = 4;", script_text)
        self.assertIn("const STATION_MARKER_RADIUS = 7;", script_text)
        self.assertIn("const STATION_MARKER_WEIGHT = 3;", script_text)
        self.assertIn('const STATION_MARKER_FILL_COLOR = "#ffffff";', script_text)
        self.assertIn("color.trim().startsWith(\"#\")", script_text)
        self.assertIn("color.trim().slice(1)", script_text)
        self.assertIn('lineCap: "round"', script_text)
        self.assertIn('lineJoin: "round"', script_text)
        self.assertIn("opacity: 1,", script_text)
        self.assertIn("fillOpacity: 1,", script_text)

    def test_map_facilities_script_opens_station_detail_popups(
        self,
    ) -> None:
        """Ensure station markers fetch and render facilities popups."""
        script_path = finders.find("subway/js/map_facilities.js")
        stylesheet_path = finders.find("subway/css/style.css")

        self.assertIsNotNone(script_path)
        self.assertIsNotNone(stylesheet_path)

        script_text = Path(script_path).read_text(encoding="utf-8")
        stylesheet_text = Path(stylesheet_path).read_text(encoding="utf-8")

        self.assertIn('const STATION_ENDPOINT_BASE = "/api/stations/";', script_text)
        self.assertIn("const fetchStationDetail = async", script_text)
        self.assertIn("stationId: station.station_id", script_text)
        self.assertIn("stationName:", script_text)
        self.assertIn("const createServedLinesSection = ", script_text)
        self.assertIn("const createFacilitiesSection = ", script_text)
        self.assertIn("stationDetail.lines_served", script_text)
        self.assertIn("stationDetail.facilities", script_text)
        self.assertIn(
            'className: "map-facilities-page__station-leaflet-popup"',
            script_text,
        )
        self.assertIn("keepInView: true", script_text)
        self.assertIn('stationLayer.on("click"', script_text)
        self.assertIn('stationLayer.on("mouseover"', script_text)
        self.assertIn("marker.bindPopup(", script_text)
        self.assertIn("fetchStationDetail({ stationId })", script_text)
        self.assertIn(
            ".map-facilities-page__station-leaflet-popup "
            ".leaflet-popup-content {",
            stylesheet_text,
        )
        self.assertIn(
            ".map-facilities-page__station-popup-line-badge {",
            stylesheet_text,
        )
        self.assertIn(
            ".map-facilities-page__station-popup-facilities {",
            stylesheet_text,
        )


class SharedMapExperienceTest(SimpleTestCase):
    """Verify the shared map controls and styling contract."""

    def test_map_pages_share_zoom_controls_popup_bounds_and_shell_styles(
        self,
    ) -> None:
        """Ensure both Leaflet pages keep one shared interaction contract."""
        trains_script_path = finders.find("subway/js/trains_alerts.js")
        map_facilities_script_path = finders.find("subway/js/map_facilities.js")
        stylesheet_path = finders.find("subway/css/style.css")

        self.assertIsNotNone(trains_script_path)
        self.assertIsNotNone(map_facilities_script_path)
        self.assertIsNotNone(stylesheet_path)

        trains_script_text = Path(trains_script_path).read_text(encoding="utf-8")
        map_facilities_script_text = Path(map_facilities_script_path).read_text(
            encoding="utf-8",
        )
        stylesheet_text = Path(stylesheet_path).read_text(encoding="utf-8")

        self.assertIn("zoomControl: true", trains_script_text)
        self.assertIn("zoomControl: true", map_facilities_script_text)
        self.assertIn("keepInView: true", trains_script_text)
        self.assertIn("keepInView: true", map_facilities_script_text)
        self.assertIn("closeOnEscapeKey: true", trains_script_text)
        self.assertIn("closeOnEscapeKey: true", map_facilities_script_text)
        self.assertIn("closeOnClick: true", trains_script_text)
        self.assertIn("closeOnClick: true", map_facilities_script_text)
        self.assertIn("autoPanPadding: window.L.point(", trains_script_text)
        self.assertIn(
            "autoPanPadding: window.L.point(",
            map_facilities_script_text,
        )
        self.assertIn(
            ".trains-page,\n.map-facilities-page {",
            stylesheet_text,
        )
        self.assertIn(
            ".trains-page__controls,\n"
            ".trains-page__alerts,\n"
            ".trains-page__map-shell,\n"
            ".map-facilities-page__map-shell {",
            stylesheet_text,
        )
        self.assertIn(
            ".trains-page__map,\n.map-facilities-page__map {",
            stylesheet_text,
        )
        self.assertIn(
            ".trains-page__prediction-leaflet-popup .leaflet-popup-content,\n"
            ".map-facilities-page__station-leaflet-popup "
            ".leaflet-popup-content {",
            stylesheet_text,
        )


class MapBoundsVerificationTest(SimpleTestCase):
    """Verify the shared full-system bounds cover the subway network."""

    _BOUNDARY_STATIONS = (
        ("Braintree", 42.2078543, -71.0011385),
        ("Eliot", 42.319045, -71.216684),
        ("Newton Centre", 42.329443, -71.192414),
        ("Newton Highlands", 42.322381, -71.205509),
        ("Riverside", 42.337352, -71.252685),
        ("Waban", 42.325845, -71.230609),
        ("Woodland", 42.332902, -71.243362),
    )
    _SYSTEM_BOUNDS_PATTERN = re.compile(
        r"const SUBWAY_SYSTEM_BOUNDS = \[\s*"
        r"\[\s*([-0-9.]+),\s*([-0-9.]+)\s*\],\s*"
        r"\[\s*([-0-9.]+),\s*([-0-9.]+)\s*\],\s*"
        r"\];",
        flags=re.MULTILINE,
    )

    def test_map_scripts_share_matching_full_system_bounds(self) -> None:
        """Ensure both pages use the same fallback subway system bounds."""
        trains_script_text = self._read_static_asset(
            relative_path="subway/js/trains_alerts.js",
        )
        map_facilities_script_text = self._read_static_asset(
            relative_path="subway/js/map_facilities.js",
        )

        self.assertEqual(
            self._extract_system_bounds(script_text=trains_script_text),
            self._extract_system_bounds(
                script_text=map_facilities_script_text,
            ),
        )

    def test_full_system_bounds_cover_known_edge_stations(self) -> None:
        """Ensure reset/default bounds still include the route edge stations."""
        trains_script_text = self._read_static_asset(
            relative_path="subway/js/trains_alerts.js",
        )
        (
            south_west_corner,
            north_east_corner,
        ) = self._extract_system_bounds(
            script_text=trains_script_text,
        )
        min_latitude, min_longitude = south_west_corner
        max_latitude, max_longitude = north_east_corner

        for station_name, latitude, longitude in self._BOUNDARY_STATIONS:
            with self.subTest(station_name=station_name):
                self.assertLessEqual(min_latitude, latitude)
                self.assertLessEqual(latitude, max_latitude)
                self.assertLessEqual(min_longitude, longitude)
                self.assertLessEqual(longitude, max_longitude)

    def _read_static_asset(
        self,
        *,
        relative_path: str,
    ) -> str:
        """Return the source text for one registered static asset."""
        asset_path = finders.find(relative_path)

        self.assertIsNotNone(asset_path)
        return Path(asset_path).read_text(encoding="utf-8")

    def _extract_system_bounds(
        self,
        *,
        script_text: str,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Parse the shared system-bounds constant from a map script."""
        if match := self._SYSTEM_BOUNDS_PATTERN.search(script_text):
            return (
                (float(match.group(1)), float(match.group(2))),
                (float(match.group(3)), float(match.group(4))),
            )

        raise AssertionError(
            "Expected the map script to define SUBWAY_SYSTEM_BOUNDS.",
        )


class TrainsAlertsLayoutTest(SimpleTestCase):
    """Verify the initial Trains and Alerts page layout."""

    def test_page_renders_dropdown_hidden_alerts_and_map(self) -> None:
        """Ensure first load exposes the required layout elements."""
        response = self.client.get(reverse("subway:trains_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'id="line-select"',
        )
        self.assertContains(
            response,
            "Select a subway line to display",
        )
        self.assertContains(
            response,
            'id="alerts-panel"',
        )
        self.assertContains(
            response,
            'aria-live="polite"',
        )
        self.assertContains(
            response,
            'id="trains-map"',
        )

    def test_alerts_panel_is_hidden_and_kept_between_controls_and_map(
        self,
    ) -> None:
        """Ensure the reserved alerts area is hidden on first load."""
        response = self.client.get(reverse("subway:trains_alerts"))
        response_html = response.content.decode("utf-8")

        select_position = response_html.index('id="line-select"')
        alerts_position = response_html.index('id="alerts-panel"')
        map_position = response_html.index('id="trains-map"')

        self.assertLess(select_position, alerts_position)
        self.assertLess(alerts_position, map_position)
        self.assertIn(
            'id="alerts-panel"\n            class="trains-page__alerts"\n'
            '            aria-live="polite"\n            hidden',
            response_html,
        )

    def test_stylesheet_keeps_the_map_large_on_first_load(self) -> None:
        """Ensure the map area claims at least seventy viewport height."""
        stylesheet_path = finders.find("subway/css/style.css")

        self.assertIsNotNone(stylesheet_path)
        stylesheet_text = Path(stylesheet_path).read_text(encoding="utf-8")

        self.assertIn(".trains-page__map {", stylesheet_text)
        self.assertIn("min-height: 70vh;", stylesheet_text)

    def test_page_loads_the_trains_dropdown_script(self) -> None:
        """Ensure the trains page includes its line-loading script."""
        response = self.client.get(reverse("subway:trains_alerts"))
        script_path = finders.find("subway/js/trains_alerts.js")

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(script_path)
        self.assertContains(
            response,
            'src="/static/subway/js/trains_alerts.js"',
        )
        self.assertContains(
            response,
            'src="/static/subway/js/map_styles.js"',
        )

    def test_page_loads_leaflet_assets_for_the_initial_map(self) -> None:
        """Ensure the trains page loads the Leaflet assets it needs."""
        response = self.client.get(reverse("subway:trains_alerts"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
        )
        self.assertContains(
            response,
            "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
        )

    def test_trains_script_initializes_and_fits_the_startup_map(
        self,
    ) -> None:
        """Ensure first-load JS creates a map and fits system bounds."""
        script_path = finders.find("subway/js/trains_alerts.js")

        self.assertIsNotNone(script_path)
        script_text = Path(script_path).read_text(encoding="utf-8")

        self.assertIn("const SUBWAY_SYSTEM_BOUNDS = [", script_text)
        self.assertIn('window.L.map(mapElement, {', script_text)
        self.assertIn("trainsMap.fitBounds(SUBWAY_SYSTEM_BOUNDS", script_text)

    def test_trains_script_renders_only_the_selected_line_and_stations(
        self,
    ) -> None:
        """Ensure the trains script redraws and fits the chosen line."""
        script_path = finders.find("subway/js/trains_alerts.js")

        self.assertIsNotNone(script_path)
        script_text = Path(script_path).read_text(encoding="utf-8")

        self.assertIn('lineSelect.addEventListener("change"', script_text)
        self.assertIn("const LINE_DETAIL_ENDPOINT_BASE = ", script_text)
        self.assertIn("const parseLineDetailPayload = ", script_text)
        self.assertIn("encodeURIComponent(lineName)", script_text)
        self.assertIn("selectedLineLayerGroup.remove()", script_text)
        self.assertIn("window.L.polyline", script_text)
        self.assertIn("window.L.circleMarker", script_text)
        self.assertIn("createLineStyle({ color: lineColor })", script_text)
        self.assertIn(
            "createStationMarkerStyle({ color: lineColor })",
            script_text,
        )
        self.assertIn("window.L.featureGroup(renderedLayers)", script_text)
        self.assertIn(
            "trainsMap.fitBounds(selectedLineLayerGroup.getBounds()",
            script_text,
        )

    def test_trains_script_fetches_and_renders_scrollable_alerts(
        self,
    ) -> None:
        """Ensure line selection also shows a scrollable alerts panel."""
        script_path = finders.find("subway/js/trains_alerts.js")
        stylesheet_path = finders.find("subway/css/style.css")

        self.assertIsNotNone(script_path)
        self.assertIsNotNone(stylesheet_path)

        script_text = Path(script_path).read_text(encoding="utf-8")
        stylesheet_text = Path(stylesheet_path).read_text(encoding="utf-8")

        self.assertIn("const LINE_ALERTS_SUFFIX = ", script_text)
        self.assertIn(
            "fetchLineAlerts({ lineName: selectedLineName })",
            script_text,
        )
        self.assertIn("alertsPanel.hidden = false;", script_text)
        self.assertIn("No alerts for", script_text)
        self.assertIn("Unable to load alerts for", script_text)
        self.assertIn("#alerts-content {", stylesheet_text)
        self.assertIn("max-height: 16rem;", stylesheet_text)
        self.assertIn("overflow-y: auto;", stylesheet_text)

    def test_trains_script_resets_line_state_on_default_selection(
        self,
    ) -> None:
        """Ensure the default dropdown option clears map and alerts state."""
        script_path = finders.find("subway/js/trains_alerts.js")

        self.assertIsNotNone(script_path)
        script_text = Path(script_path).read_text(encoding="utf-8")

        self.assertIn("const resetSelectedLineState = ", script_text)
        self.assertIn("if (!selectedLineName) {", script_text)
        self.assertIn("removeSelectedLineLayer();", script_text)
        self.assertIn("clearAlertsContent({ alertsContent });", script_text)
        self.assertIn("alertsPanel.hidden = true;", script_text)
        self.assertIn("trainsMap.fitBounds(SUBWAY_SYSTEM_BOUNDS", script_text)

    def test_trains_script_opens_station_prediction_popups(
        self,
    ) -> None:
        """Ensure station popups stay visible, dismissible, and scrollable."""
        script_path = finders.find("subway/js/trains_alerts.js")
        stylesheet_path = finders.find("subway/css/style.css")

        self.assertIsNotNone(script_path)
        self.assertIsNotNone(stylesheet_path)
        script_text = Path(script_path).read_text(encoding="utf-8")
        stylesheet_text = Path(stylesheet_path).read_text(encoding="utf-8")

        self.assertIn(
            'const STATION_PREDICTIONS_SUFFIX = "/predictions";',
            script_text,
        )
        self.assertIn("stationId: station.station_id", script_text)
        self.assertIn('stationLayer.on("click"', script_text)
        self.assertIn(
            "fetchStationPredictions({ stationId })",
            script_text,
        )
        self.assertIn("MAX_PREDICTIONS_PER_LINE = 4", script_text)
        self.assertIn("No subway predictions.", script_text)
        self.assertIn("marker.bindPopup(", script_text)
        self.assertIn("keepInView: true", script_text)
        self.assertIn("closeOnEscapeKey: true", script_text)
        self.assertIn("closeOnClick: true", script_text)
        self.assertIn('className: "trains-page__prediction-leaflet-popup"', script_text)
        self.assertIn('marker.on("mouseout"', script_text)
        self.assertIn(
            'popupElement.addEventListener("mouseleave"',
            script_text,
        )
        self.assertIn(
            ".trains-page__prediction-leaflet-popup .leaflet-popup-content,",
            stylesheet_text,
        )
        self.assertIn("max-height: min(18rem, 45dvh);", stylesheet_text)
        self.assertIn("overflow-y: auto;", stylesheet_text)


class LineNamesAPIViewTest(SimpleTestCase):
    """Verify the subway line-name JSON endpoint."""

    def test_line_names_endpoint_returns_json_array(self) -> None:
        """Ensure the endpoint returns the service result as a JSON array."""
        expected_line_names = [
            "Blue Line",
            "Orange Line",
            "Red Line",
        ]

        with patch(
            "subway.views.services.get_line_names",
            return_value=expected_line_names,
        ):
            response = self.client.get(reverse("subway:line_names"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            expected_line_names,
        )

    def test_line_names_endpoint_calls_service_once(self) -> None:
        """Ensure the endpoint delegates exactly once to the MBTA service."""
        with patch(
            "subway.views.services.get_line_names",
            return_value=["Blue Line"],
        ) as get_line_names_mock:
            response = self.client.get(reverse("subway:line_names"))

        self.assertEqual(response.status_code, 200)
        get_line_names_mock.assert_called_once_with()

    def test_line_names_endpoint_returns_empty_array(self) -> None:
        """Ensure the endpoint preserves an empty service response."""
        with patch(
            "subway.views.services.get_line_names",
            return_value=[],
        ):
            response = self.client.get(reverse("subway:line_names"))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            [],
        )

    def test_line_names_endpoint_returns_500_when_service_errors(self) -> None:
        """Ensure line-name failures become JSON 500 responses."""
        with patch(
            "subway.views.services.get_line_names",
            side_effect=RuntimeError("mbta unavailable"),
        ):
            response = self.client.get(reverse("subway:line_names"))

        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Unable to load line names."},
        )


class LineDetailAPIViewTest(SimpleTestCase):
    """Verify the single-line geometry JSON endpoint."""

    def test_line_detail_returns_validated_line_payload(self) -> None:
        """Ensure the endpoint exposes schema-backed line JSON."""
        line_schema = LineSchema(
            name="Red Line",
            color="DA291C",
            shapes=[[(42.395428, -71.142483), (42.365577, -71.103419)]],
            stations=[
                StationSummarySchema(
                    station_id="place-alfcl",
                    name="Alewife",
                    latitude=42.395428,
                    longitude=-71.142483,
                ),
            ],
        )

        with patch(
            "subway.views._validate_line_name_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_line",
                return_value=line_schema,
            ):
                response = self.client.get(
                    reverse(
                        "subway:line_detail",
                        kwargs={"line_name": "Red Line"},
                    ),
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {
                "name": "Red Line",
                "color": "DA291C",
                "shapes": [
                    [
                        [42.395428, -71.142483],
                        [42.365577, -71.103419],
                    ],
                ],
                "stations": [
                    {
                        "station_id": "place-alfcl",
                        "name": "Alewife",
                        "latitude": 42.395428,
                        "longitude": -71.142483,
                        "address": None,
                    },
                ],
            },
        )

    def test_line_detail_passes_the_requested_line_name(self) -> None:
        """Ensure the endpoint delegates with the URL line name."""
        line_schema = LineSchema(
            name="Blue Line",
            color="003DA5",
            shapes=[],
            stations=[],
        )

        with patch(
            "subway.views._validate_line_name_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_line",
                return_value=line_schema,
            ) as get_line_mock:
                response = self.client.get(
                    reverse(
                        "subway:line_detail",
                        kwargs={"line_name": "Blue Line"},
                    ),
                )

        self.assertEqual(response.status_code, 200)
        get_line_mock.assert_called_once_with(line_name="Blue Line")

    def test_line_detail_returns_404_for_unknown_line(self) -> None:
        """Ensure the endpoint reports missing lines clearly."""
        with patch(
            "subway.views._validate_line_name_request",
            return_value=JsonResponse(
                {"error": "Line not found."},
                status=404,
            ),
        ):
            response = self.client.get(
                reverse(
                    "subway:line_detail",
                    kwargs={"line_name": "Silver Line"},
                ),
            )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Line not found."},
        )

    def test_line_detail_returns_500_when_service_errors(self) -> None:
        """Ensure unexpected service failures become JSON 500 responses."""
        with patch(
            "subway.views._validate_line_name_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_line",
                side_effect=RuntimeError("mbta unavailable"),
            ):
                response = self.client.get(
                    reverse(
                        "subway:line_detail",
                        kwargs={"line_name": "Red Line"},
                    ),
                )

        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Unable to load line details."},
        )

    def test_line_detail_returns_400_for_malformed_line_name(self) -> None:
        """Ensure malformed line names are rejected before service lookup."""
        with patch(
            "subway.views.services.is_public_line_name_format_valid",
            return_value=False,
        ):
            with patch(
                "subway.views.services.line_exists",
            ) as line_exists_mock:
                with patch(
                    "subway.views.services.get_line",
                ) as get_line_mock:
                    response = self.client.get(
                        reverse(
                            "subway:line_detail",
                            kwargs={"line_name": "Red<script>"},
                        ),
                    )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Invalid line name."},
        )
        line_exists_mock.assert_not_called()
        get_line_mock.assert_not_called()


class LineAlertsAPIViewTest(SimpleTestCase):
    """Verify the line-alert JSON endpoint."""

    def test_line_alerts_returns_a_json_array(self) -> None:
        """Ensure the endpoint exposes validated alert payloads."""
        alert_schemas = [
            AlertSchema(
                id="alert-1",
                headline="Shuttle buses replace service",
                description="Use shuttle buses between stations.",
                severity=5,
            ),
        ]
        with patch(
            "subway.views._validate_line_name_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_line_alerts",
                return_value=alert_schemas,
            ) as get_line_alerts_mock:
                response = self.client.get(
                    reverse(
                        "subway:line_alerts",
                        kwargs={"line_name": "Orange Line"},
                    ),
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            [
                {
                    "id": "alert-1",
                    "headline": "Shuttle buses replace service",
                    "description": "Use shuttle buses between stations.",
                    "severity": 5,
                },
            ],
        )
        get_line_alerts_mock.assert_called_once_with(
            line_name="Orange Line",
        )

    def test_line_alerts_returns_404_for_unknown_line(self) -> None:
        """Ensure the endpoint rejects missing lines before alert lookup."""
        with patch(
            "subway.views.services.is_public_line_name_format_valid",
            return_value=True,
        ):
            with patch(
                "subway.views.services.line_exists",
                return_value=False,
            ):
                with patch(
                    "subway.views.services.get_line_alerts",
                ) as get_line_alerts_mock:
                    response = self.client.get(
                        reverse(
                            "subway:line_alerts",
                            kwargs={"line_name": "Silver Line"},
                        ),
                    )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Line not found."},
        )
        get_line_alerts_mock.assert_not_called()

    def test_line_alerts_returns_500_when_service_errors(self) -> None:
        """Ensure unexpected alert failures become JSON 500 responses."""
        with patch(
            "subway.views._validate_line_name_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_line_alerts",
                side_effect=RuntimeError("alerts unavailable"),
            ):
                response = self.client.get(
                    reverse(
                        "subway:line_alerts",
                        kwargs={"line_name": "Red Line"},
                    ),
                )

        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Unable to load line alerts."},
        )


class StationDetailAPIViewTest(SimpleTestCase):
    """Verify the station-detail JSON endpoint."""

    def test_station_detail_returns_a_schema_backed_payload(self) -> None:
        """Ensure the endpoint exposes validated station detail JSON."""
        station_schema = StationDetailSchema(
            station_id="place-gover",
            name="Government Center",
            latitude=42.359705,
            longitude=-71.059215,
            address="Cambridge St",
            lines_served=["Blue Line", "Green Line"],
            facilities=["ESCALATOR: Main lobby", "ELEVATOR: Court St"],
        )

        with patch(
            "subway.views._validate_station_id_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_station",
                return_value=station_schema,
            ):
                response = self.client.get(
                    reverse(
                        "subway:station_detail",
                        kwargs={"station_id": "place-gover"},
                    ),
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {
                "station_id": "place-gover",
                "name": "Government Center",
                "latitude": 42.359705,
                "longitude": -71.059215,
                "address": "Cambridge St",
                "lines_served": ["Blue Line", "Green Line"],
                "facilities": [
                    "ESCALATOR: Main lobby",
                    "ELEVATOR: Court St",
                ],
            },
        )

    def test_station_detail_passes_the_requested_station_id(self) -> None:
        """Ensure the endpoint delegates with the URL station identifier."""
        station_schema = StationDetailSchema(
            station_id="place-pktrm",
            name="Park Street",
            latitude=42.35639457,
            longitude=-71.0624242,
            address=None,
            lines_served=["Green Line", "Red Line"],
            facilities=[],
        )

        with patch(
            "subway.views._validate_station_id_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_station",
                return_value=station_schema,
            ) as get_station_mock:
                response = self.client.get(
                    reverse(
                        "subway:station_detail",
                        kwargs={"station_id": "place-pktrm"},
                    ),
                )

        self.assertEqual(response.status_code, 200)
        get_station_mock.assert_called_once_with(station_id="place-pktrm")

    def test_station_detail_returns_404_for_unknown_station(self) -> None:
        """Ensure the endpoint reports missing stations clearly."""
        with patch(
            "subway.views._validate_station_id_request",
            return_value=JsonResponse(
                {"error": "Station not found."},
                status=404,
            ),
        ):
            response = self.client.get(
                reverse(
                    "subway:station_detail",
                    kwargs={"station_id": "place-unknown"},
                ),
            )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Station not found."},
        )

    def test_station_detail_returns_500_when_service_errors(self) -> None:
        """Ensure unexpected station failures become JSON 500 responses."""
        with patch(
            "subway.views._validate_station_id_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_station",
                side_effect=RuntimeError("station unavailable"),
            ):
                response = self.client.get(
                    reverse(
                        "subway:station_detail",
                        kwargs={"station_id": "place-gover"},
                    ),
                )

        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Unable to load station details."},
        )

    def test_station_detail_returns_400_for_malformed_station_id(
        self,
    ) -> None:
        """Ensure malformed station IDs are rejected before lookup."""
        with patch(
            "subway.views.services.is_public_station_id_format_valid",
            return_value=False,
        ):
            with patch(
                "subway.views.services.station_exists",
            ) as station_exists_mock:
                with patch(
                    "subway.views.services.get_station",
                ) as get_station_mock:
                    response = self.client.get(
                        reverse(
                            "subway:station_detail",
                            kwargs={"station_id": "place-gover!"},
                        ),
                    )

        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Invalid station ID."},
        )
        station_exists_mock.assert_not_called()
        get_station_mock.assert_not_called()


class StationPredictionsAPIViewTest(SimpleTestCase):
    """Verify the station-predictions JSON endpoint."""

    def test_station_predictions_returns_a_json_array(self) -> None:
        """Ensure the endpoint exposes validated prediction rows."""
        prediction_schemas = [
            PredictionSchema(
                line="Red",
                destination="Alewife",
                arrival_time="2026-04-23T12:15:00Z",
                departure_time=None,
                status="Boarding",
            ),
        ]

        with patch(
            "subway.views._validate_station_id_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_predictions",
                return_value=prediction_schemas,
            ) as get_predictions_mock:
                response = self.client.get(
                    reverse(
                        "subway:station_predictions",
                        kwargs={"station_id": "place-jfk"},
                    ),
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            [prediction_schemas[0].model_dump(mode="json")],
        )
        get_predictions_mock.assert_called_once_with(
            station_id="place-jfk",
        )

    def test_station_predictions_returns_404_for_unknown_station(
        self,
    ) -> None:
        """Ensure the endpoint rejects missing stations before lookup."""
        with patch(
            "subway.views.services.is_public_station_id_format_valid",
            return_value=True,
        ):
            with patch(
                "subway.views.services.station_exists",
                return_value=False,
            ):
                with patch(
                    "subway.views.services.get_predictions",
                ) as get_predictions_mock:
                    response = self.client.get(
                        reverse(
                            "subway:station_predictions",
                            kwargs={"station_id": "place-unknown"},
                        ),
                    )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Station not found."},
        )
        get_predictions_mock.assert_not_called()

    def test_station_predictions_returns_500_when_service_errors(
        self,
    ) -> None:
        """Ensure unexpected prediction failures become JSON 500 responses."""
        with patch(
            "subway.views._validate_station_id_request",
            return_value=None,
        ):
            with patch(
                "subway.views.services.get_predictions",
                side_effect=RuntimeError("predictions unavailable"),
            ):
                response = self.client.get(
                    reverse(
                        "subway:station_predictions",
                        kwargs={"station_id": "place-brdwy"},
                    ),
                )

        self.assertEqual(response.status_code, 500)
        self.assertJSONEqual(
            response.content.decode("utf-8"),
            {"error": "Unable to load station predictions."},
        )


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


class ServiceSchemaTest(SimpleTestCase):
    """Verify schema-backed MBTA service helpers."""

    def test_get_line_returns_validated_line_schema(self) -> None:
        """Ensure line data is normalized into nested Pydantic models."""
        fake_service = self._build_fake_mbta_service(
            line_payload={
                "line_color": "DA291C",
                "shapes": [[(42.1, -71.1), (42.2, -71.2)]],
                "stations": [
                    {
                        "station_id": "place-alfcl",
                        "name": "Alewife",
                        "latitude": 42.395428,
                        "longitude": -71.142483,
                        "address": "Alewife Brook Pkwy",
                    },
                ],
            },
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            line = services.get_line(line_name="Red Line")

        self.assertIsInstance(line, LineSchema)
        self.assertIsNotNone(line)
        self.assertEqual(line.name, "Red Line")
        self.assertEqual(line.color, "DA291C")
        self.assertIsInstance(line.stations[0], StationSummarySchema)
        self.assertEqual(line.stations[0].station_id, "place-alfcl")

    def test_get_station_returns_detail_with_lines_served(self) -> None:
        """Ensure station detail includes computed line membership."""
        fake_service = self._build_fake_mbta_service(
            station_payload={
                "id": "place-gover",
                "name": "Government Center",
                "latitude": 42.359705,
                "longitude": -71.059215,
                "address": "Cambridge St",
                "facilities": ["ESCALATOR: Main lobby", "ELEVATOR: Court St"],
            },
            lines=[
                {
                    "name": "Blue Line",
                    "stations": [{"station_id": "place-gover"}],
                },
                {
                    "name": "Green Line",
                    "stations": [{"id": "place-gover"}],
                },
            ],
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            station = services.get_station(station_id="place-gover")

        self.assertIsInstance(station, StationDetailSchema)
        self.assertIsNotNone(station)
        self.assertEqual(
            station.lines_served,
            ["Blue Line", "Green Line"],
        )
        self.assertEqual(
            station.facilities,
            ["ESCALATOR: Main lobby", "ELEVATOR: Court St"],
        )

    def test_get_station_facilities_returns_facility_schemas(self) -> None:
        """Ensure facilities are validated into a dedicated schema type."""
        fake_service = self._build_fake_mbta_service(
            station_facilities=["ELEVATOR: Main entrance", "RAMP: Platform"],
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            facilities = services.get_station_facilities(
                station_id="place-pktrm",
            )

        self.assertEqual(len(facilities), 2)
        self.assertTrue(
            all(
                isinstance(facility, FacilitySchema)
                for facility in facilities
            ),
        )
        self.assertEqual(facilities[0].label, "ELEVATOR: Main entrance")

    def test_get_line_alerts_maps_nested_mbta_alert_fields(self) -> None:
        """Ensure nested MBTA alert payloads are flattened consistently."""
        fake_service = self._build_fake_mbta_service(
            alert_payloads=[
                {
                    "id": "alert-1",
                    "attributes": {
                        "header": "Shuttle buses replace service",
                        "description": "Use shuttle buses between stations.",
                        "severity": 5,
                    },
                },
            ],
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            alerts = services.get_line_alerts(line_name="Orange Line")

        self.assertEqual(len(alerts), 1)
        self.assertIsInstance(alerts[0], AlertSchema)
        self.assertEqual(alerts[0].headline, "Shuttle buses replace service")
        self.assertEqual(alerts[0].severity, 5)

    def test_get_line_alerts_falls_back_to_cached_route_alerts(
        self,
    ) -> None:
        """Ensure upstream alert sort failures still return validated alerts."""
        fake_service = self._build_fake_mbta_service(
            line_alerts_error=TypeError("severity comparison failed"),
            lines=[
                {
                    "name": "Green Line",
                    "route_id": ["Green-B", "Green-C"],
                    "stations": [],
                },
            ],
            route_alerts_by_route={
                "Green-B": [
                    {
                        "id": "alert-2",
                        "attributes": {
                            "header": "Service change",
                            "description": "Use shuttle buses.",
                            "severity": None,
                        },
                    },
                ],
                "Green-C": [
                    {
                        "id": "alert-1",
                        "attributes": {
                            "header": "Minor delay",
                            "description": None,
                            "severity": 3,
                        },
                    },
                ],
            },
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            alerts = services.get_line_alerts(line_name="Green Line")

        self.assertEqual(
            [alert.id for alert in alerts],
            ["alert-2", "alert-1"],
        )
        self.assertIsNone(alerts[0].severity)
        self.assertEqual(alerts[1].severity, 3)

    def test_get_predictions_maps_route_and_status_fields(self) -> None:
        """Ensure prediction fields match the app schema contract."""
        fake_service = self._build_fake_mbta_service(
            prediction_payloads=[
                {
                    "route": "Red",
                    "destination": "Alewife",
                    "arrival_time": "2026-04-23T12:15:00Z",
                    "departure_time": None,
                    "comments": "Boarding",
                },
            ],
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            predictions = services.get_predictions(
                station_id="place-jfk",
            )

        self.assertEqual(len(predictions), 1)
        self.assertIsInstance(predictions[0], PredictionSchema)
        self.assertEqual(predictions[0].line, "Red")
        self.assertEqual(predictions[0].status, "Boarding")
        self.assertEqual(
            predictions[0].arrival_time,
            datetime(
                2026,
                4,
                23,
                12,
                15,
                tzinfo=UTC,
            ),
        )

    def test_public_input_format_validators_reject_malformed_values(
        self,
    ) -> None:
        """Ensure the shared validators reject unsafe public inputs."""
        self.assertTrue(
            services.is_public_line_name_format_valid(
                line_name="Red Line",
            ),
        )
        self.assertFalse(
            services.is_public_line_name_format_valid(
                line_name="Red<script>",
            ),
        )
        self.assertTrue(
            services.is_public_station_id_format_valid(
                station_id="place-gover",
            ),
        )
        self.assertFalse(
            services.is_public_station_id_format_valid(
                station_id="place-gover!",
            ),
        )

    def test_line_exists_and_station_exists_use_initialized_cache(
        self,
    ) -> None:
        """Ensure existence checks use cached initialized subway data."""
        fake_service = self._build_fake_mbta_service(
            lines=[
                {
                    "name": "Blue Line",
                    "stations": [
                        {"station_id": "place-gover"},
                    ],
                },
            ],
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            self.assertTrue(services.line_exists(line_name="Blue Line"))
            self.assertFalse(services.line_exists(line_name="Silver Line"))
            self.assertTrue(
                services.station_exists(station_id="place-gover"),
            )
            self.assertFalse(
                services.station_exists(station_id="place-unknown"),
            )

    def test_get_line_raises_validation_error_for_invalid_station_data(
        self,
    ) -> None:
        """Ensure invalid MBTA payloads fail validation quickly."""
        fake_service = self._build_fake_mbta_service(
            line_payload={
                "line_color": "DA291C",
                "shapes": [[(42.1, -71.1)]],
                "stations": [
                    {
                        "station_id": "place-alfcl",
                        "name": "Alewife",
                        "latitude": "not-a-float",
                        "longitude": -71.142483,
                    },
                ],
            },
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            with self.assertRaises(ValidationError):
                services.get_line(line_name="Red Line")

    def test_get_line_raises_type_error_for_non_list_station_payload(
        self,
    ) -> None:
        """Ensure malformed station collections fail with a clear error."""
        fake_service = self._build_fake_mbta_service(
            line_payload={
                "line_color": "DA291C",
                "shapes": [[(42.1, -71.1)]],
                "stations": "not-a-list",
            },
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            with self.assertRaises(TypeError):
                services.get_line(line_name="Red Line")

    def test_get_predictions_rejects_invalid_timestamp_strings(
        self,
    ) -> None:
        """Ensure malformed prediction times fail schema validation."""
        fake_service = self._build_fake_mbta_service(
            prediction_payloads=[
                {
                    "route": "Red",
                    "destination": "Alewife",
                    "arrival_time": "not-a-timestamp",
                    "departure_time": None,
                    "comments": "Boarding",
                },
            ],
        )

        with patch(
            "subway.services.initialize_service",
            return_value=fake_service,
        ):
            with self.assertRaises(ValidationError):
                services.get_predictions(station_id="place-jfk")

    @staticmethod
    def _build_fake_mbta_service(
        *,
        line_names: list[str] | None = None,
        line_payload: dict[str, object] | None = None,
        station_payload: dict[str, object] | None = None,
        station_facilities: list[str] | None = None,
        alert_payloads: list[dict[str, object]] | None = None,
        line_alerts_error: Exception | None = None,
        prediction_payloads: list[dict[str, object]] | None = None,
        lines: list[dict[str, object]] | None = None,
        route_alerts_by_route: dict[str, list[dict[str, object]]] | None = None,
    ) -> object:
        """Create a fake MBTA client with predictable schema payloads.

        Args:
            line_names: Optional line-name list for name lookups.
            line_payload: Optional raw line payload for `get_line`.
            station_payload: Optional raw station payload for `get_station`.
            station_facilities: Optional raw facilities list.
            alert_payloads: Optional raw alerts list.
            line_alerts_error: Optional exception raised by `get_line_alerts`.
            prediction_payloads: Optional raw predictions list.
            lines: Optional cached line payloads for membership checks.
            route_alerts_by_route: Optional raw route-alert lookup for fallback.

        Returns:
            A fake MBTA client object exposing the app's required methods.
        """

        class FakeMBTAService:
            """Small stand-in for the shared MBTA service."""

            def __init__(
                self,
            ) -> None:
                """Store canned payloads for the service wrapper tests."""
                self.lines = lines or []
                self._line_names = line_names or []
                self._line_payload = line_payload
                self._station_payload = station_payload
                self._station_facilities = station_facilities or []
                self._alert_payloads = alert_payloads or []
                self._line_alerts_error = line_alerts_error
                self._prediction_payloads = prediction_payloads or []
                self._route_alerts_by_route = route_alerts_by_route or {}

            def get_line_names(
                self,
            ) -> list[str]:
                """Return the configured fake line names."""
                return self._line_names

            def get_line(
                self,
                *,
                line_name: str,
            ) -> dict[str, object] | None:
                """Return the configured fake line payload."""
                _ = line_name
                return self._line_payload

            def get_station(
                self,
                *,
                station_id: str,
            ) -> dict[str, object] | None:
                """Return the configured fake station payload."""
                _ = station_id
                return self._station_payload

            def get_station_facilities(
                self,
                *,
                station_id: str,
            ) -> list[str]:
                """Return the configured fake station facilities."""
                _ = station_id
                return self._station_facilities

            def get_line_alerts(
                self,
                *,
                line_name: str,
            ) -> list[dict[str, object]]:
                """Return the configured fake line alerts."""
                _ = line_name
                if self._line_alerts_error is not None:
                    raise self._line_alerts_error
                return self._alert_payloads

            def _get_route_alerts(
                self,
                *,
                route: str,
            ) -> list[dict[str, object]]:
                """Return fallback raw alerts for one route."""
                return self._route_alerts_by_route.get(route, [])

            def get_predictions(
                self,
                *,
                station_id: str,
            ) -> list[dict[str, object]]:
                """Return the configured fake station predictions."""
                _ = station_id
                return self._prediction_payloads

        return FakeMBTAService()


class ChromeArtifactWriterTest(SimpleTestCase):
    """Verify the story 6.4 Chrome artifact output format."""

    def test_write_chrome_test_artifacts_writes_json_case_records(
        self,
    ) -> None:
        """Ensure the JSON artifact records each executed test case."""
        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            test_run = self._build_test_run(
                results=(
                    ChromeTestResult(
                        test_id="chrome-001",
                        test_name="Trains page loads",
                        timestamp="2026-04-25T12:00:00+00:00",
                        status="pass",
                    ),
                    ChromeTestResult(
                        test_id="chrome-002",
                        test_name="Alerts render",
                        timestamp="2026-04-25T12:01:00+00:00",
                        status="fail",
                        details="Timeout waiting for alerts.",
                    ),
                ),
            )

            json_path, _ = write_chrome_test_artifacts(
                output_directory=output_directory,
                test_run=test_run,
            )

            self.assertTrue(json_path.exists())
            self.assertEqual(
                json.loads(json_path.read_text(encoding="utf-8")),
                [
                    {
                        "test_id": "chrome-001",
                        "test_name": "Trains page loads",
                        "timestamp": "2026-04-25T12:00:00+00:00",
                        "status": "pass",
                        "details": "",
                    },
                    {
                        "test_id": "chrome-002",
                        "test_name": "Alerts render",
                        "timestamp": "2026-04-25T12:01:00+00:00",
                        "status": "fail",
                        "details": "Timeout waiting for alerts.",
                    },
                ],
            )

    def test_write_chrome_test_artifacts_writes_markdown_summary(
        self,
    ) -> None:
        """Ensure the Markdown artifact reports totals and failures."""
        with TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            test_run = self._build_test_run(
                results=(
                    ChromeTestResult(
                        test_id="chrome-001",
                        test_name="Trains page loads",
                        timestamp="2026-04-25T12:00:00+00:00",
                        status="pass",
                    ),
                    ChromeTestResult(
                        test_id="chrome-002",
                        test_name="Alerts render",
                        timestamp="2026-04-25T12:01:00+00:00",
                        status="fail",
                        details="Timeout waiting for alerts.",
                    ),
                ),
            )

            _, markdown_path = write_chrome_test_artifacts(
                output_directory=output_directory,
                test_run=test_run,
            )
            markdown_text = markdown_path.read_text(encoding="utf-8")

            self.assertTrue(markdown_path.exists())
            self.assertIn("# Chrome Test Summary", markdown_text)
            self.assertIn("- Total tests run: 2", markdown_text)
            self.assertIn("- Total passed: 1", markdown_text)
            self.assertIn("- Total failed: 1", markdown_text)
            self.assertIn("`chrome-002` Alerts render", markdown_text)
            self.assertIn("Timeout waiting for alerts.", markdown_text)

    @staticmethod
    def _build_test_run(
        *,
        results: tuple[ChromeTestResult, ...],
    ) -> ChromeTestRun:
        """Return a small Chrome test run for artifact writer tests.

        Args:
            results: The executed per-case Chrome results.

        Returns:
            A small Chrome test run payload.
        """
        return ChromeTestRun(
            base_url="http://127.0.0.1:8000",
            browser_name="chrome",
            browser_version="135.0.0.0",
            results=results,
        )
