"""Tests for the MBTA subway service layer and API views.

These are integration tests that hit the live MBTA V3 API.
Requires a valid MBTA_V3_API_KEY in the project root .env file.
"""

import json

from django.test import SimpleTestCase

from subway.schemas import (
    AlertSchema,
    LineSchema,
    PredictionSchema,
    StationDetailSchema,
)
from subway.services import (
    get_line,
    get_line_alerts,
    get_line_names,
    get_predictions,
    get_station,
)


class ServiceLayerTest(SimpleTestCase):
    """Verify service functions return data matching Pydantic schemas."""

    def test_get_line_names_returns_sorted_strings(self) -> None:
        names = get_line_names()
        self.assertIsInstance(names, list)
        self.assertGreater(len(names), 0)
        self.assertTrue(
            all(isinstance(n, str) for n in names),
        )
        self.assertEqual(names, sorted(names))

    def test_get_line_returns_line_schema(self) -> None:
        line = get_line(line_name="Red Line")
        self.assertIsNotNone(line)
        self.assertIsInstance(line, LineSchema)
        self.assertTrue(len(line.line_color) > 0)
        self.assertGreater(len(line.stations), 0)

    def test_get_line_returns_none_for_unknown(self) -> None:
        self.assertIsNone(
            get_line(line_name="Nonexistent Line"),
        )

    def test_get_line_alerts_returns_alert_schemas(self) -> None:
        alerts = get_line_alerts(line_name="Red Line")
        self.assertIsInstance(alerts, list)
        self.assertTrue(
            all(isinstance(a, AlertSchema) for a in alerts),
        )

    def test_get_station_returns_detail_with_lines_served(
        self,
    ) -> None:
        station = get_station(station_id="place-knncl")
        self.assertIsNotNone(station)
        self.assertIsInstance(station, StationDetailSchema)
        self.assertGreater(
            len(station.lines_served), 0,
            "lines_served must be computed by the service layer",
        )

    def test_get_station_returns_none_for_unknown(self) -> None:
        self.assertIsNone(
            get_station(station_id="place-xxxxx"),
        )

    def test_get_predictions_returns_prediction_schemas(
        self,
    ) -> None:
        preds = get_predictions(station_id="place-knncl")
        self.assertIsInstance(preds, list)
        self.assertTrue(
            all(isinstance(p, PredictionSchema) for p in preds),
        )


class LineAPIViewsTest(SimpleTestCase):
    """Integration tests for line-related JSON API endpoints (story 3.2)."""

    def test_api_lines_returns_200_with_line_names(self) -> None:
        """GET /api/lines/ returns a JSON list of line names."""
        response = self.client.get("/api/lines/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("lines", data)
        self.assertIsInstance(data["lines"], list)
        self.assertGreater(len(data["lines"]), 0)
        self.assertTrue(
            all(isinstance(name, str) for name in data["lines"]),
        )

    def test_api_line_detail_returns_200_for_valid_line(
        self,
    ) -> None:
        """GET /api/line/Red%20Line/ returns line data with expected keys."""
        response = self.client.get("/api/line/Red%20Line/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["line_name"], "Red Line")
        self.assertIn("line_color", data)
        self.assertIn("shapes", data)
        self.assertIn("stations", data)
        self.assertTrue(len(data["line_color"]) > 0)
        self.assertGreater(len(data["stations"]), 0)

    def test_api_line_detail_returns_404_for_invalid_line(
        self,
    ) -> None:
        """GET /api/line/Nonexistent%20Line/ returns 404."""
        response = self.client.get(
            "/api/line/Nonexistent%20Line/",
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_api_line_alerts_returns_200_with_alerts_array(
        self,
    ) -> None:
        """GET /api/line/Red%20Line/alerts/ returns alerts array."""
        response = self.client.get(
            "/api/line/Red%20Line/alerts/",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["line_name"], "Red Line")
        self.assertIn("alerts", data)
        self.assertIsInstance(data["alerts"], list)
        for alert in data["alerts"]:
            self.assertIn("headline", alert)
            self.assertIn("severity", alert)

    def test_api_line_alerts_returns_404_for_invalid_line(
        self,
    ) -> None:
        """GET /api/line/Nonexistent%20Line/alerts/ returns 404."""
        response = self.client.get(
            "/api/line/Nonexistent%20Line/alerts/",
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("error", data)


class TrainsAlertsPageTest(SimpleTestCase):
    """Verify the Trains & Alerts page renders with all required elements (story 5.1)."""

    def test_page_returns_200(self) -> None:
        """GET /trains-alerts/ returns 200."""
        response = self.client.get("/trains-alerts/")
        self.assertEqual(response.status_code, 200)

    def test_page_uses_correct_template(self) -> None:
        """Page renders via trains_alerts.html extending base.html."""
        response = self.client.get("/trains-alerts/")
        self.assertTemplateUsed(response, "subway/trains_alerts.html")
        self.assertTemplateUsed(response, "subway/base.html")

    def test_page_has_line_dropdown(self) -> None:
        """Page contains a select element for choosing a subway line."""
        response = self.client.get("/trains-alerts/")
        content = response.content.decode()
        self.assertIn('id="line-select"', content)
        self.assertIn("<select", content)

    def test_page_has_alerts_area(self) -> None:
        """Page contains an alerts display area above the map."""
        response = self.client.get("/trains-alerts/")
        content = response.content.decode()
        self.assertIn('id="alerts-area"', content)
        self.assertIn("alerts-area", content)

    def test_page_has_map_container(self) -> None:
        """Page contains a Leaflet map container div."""
        response = self.client.get("/trains-alerts/")
        content = response.content.decode()
        self.assertIn('id="map"', content)
        self.assertIn("map-container", content)

    def test_page_loads_leaflet(self) -> None:
        """Page includes Leaflet CSS and JS from CDN."""
        response = self.client.get("/trains-alerts/")
        content = response.content.decode()
        self.assertIn("leaflet.css", content)
        self.assertIn("leaflet.js", content)

    def test_page_loads_app_js(self) -> None:
        """Page includes the app.js script."""
        response = self.client.get("/trains-alerts/")
        content = response.content.decode()
        self.assertIn("app.js", content)

    def test_active_page_context(self) -> None:
        """Active nav tab is set to trains-alerts."""
        response = self.client.get("/trains-alerts/")
        content = response.content.decode()
        self.assertIn("nav-tab--active", content)


class MapFacilitiesPageTest(SimpleTestCase):
    """Verify the Map & Facilities page renders with all required elements (story 5.2)."""

    def test_page_returns_200(self) -> None:
        """GET /map-facilities/ returns 200."""
        response = self.client.get("/map-facilities/")
        self.assertEqual(response.status_code, 200)

    def test_page_uses_correct_template(self) -> None:
        """Page renders via map_facilities.html extending base.html."""
        response = self.client.get("/map-facilities/")
        self.assertTemplateUsed(
            response, "subway/map_facilities.html",
        )
        self.assertTemplateUsed(response, "subway/base.html")

    def test_page_has_full_width_map_container(self) -> None:
        """Page contains a Leaflet map container with full-width class."""
        response = self.client.get("/map-facilities/")
        content = response.content.decode()
        self.assertIn('id="map"', content)
        self.assertIn("map-container", content)
        self.assertIn("map-container--full", content)

    def test_page_has_legend_overlay(self) -> None:
        """Page reserves space for a color legend overlay."""
        response = self.client.get("/map-facilities/")
        content = response.content.decode()
        self.assertIn('id="map-legend"', content)
        self.assertIn("map-legend", content)

    def test_page_loads_leaflet(self) -> None:
        """Page includes Leaflet CSS and JS from CDN."""
        response = self.client.get("/map-facilities/")
        content = response.content.decode()
        self.assertIn("leaflet.css", content)
        self.assertIn("leaflet.js", content)

    def test_page_loads_map_facilities_js(self) -> None:
        """Page includes the map_facilities.js script."""
        response = self.client.get("/map-facilities/")
        content = response.content.decode()
        self.assertIn("map_facilities.js", content)

    def test_active_page_context(self) -> None:
        """Active nav tab is set to map-facilities."""
        response = self.client.get("/map-facilities/")
        content = response.content.decode()
        self.assertIn("nav-tab--active", content)

    def test_legend_has_heading(self) -> None:
        """Legend container includes a heading for subway lines."""
        response = self.client.get("/map-facilities/")
        content = response.content.decode()
        self.assertIn("Subway Lines", content)


class AboutPageTest(SimpleTestCase):
    """Verify the About page renders with all required elements (story 5.3)."""

    def test_page_returns_200(self) -> None:
        """GET /about/ returns 200."""
        response = self.client.get("/about/")
        self.assertEqual(response.status_code, 200)

    def test_page_uses_correct_template(self) -> None:
        """Page renders via about.html extending base.html."""
        response = self.client.get("/about/")
        self.assertTemplateUsed(response, "subway/about.html")
        self.assertTemplateUsed(response, "subway/base.html")

    def test_page_lists_mbta_api(self) -> None:
        """Page mentions MBTA V3 API with a link."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("MBTA V3 API", content)
        self.assertIn(
            "https://www.mbta.com/developers/v3-api", content,
        )

    def test_page_lists_leaflet(self) -> None:
        """Page mentions Leaflet.js with a link."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("Leaflet", content)
        self.assertIn("https://leafletjs.com/", content)

    def test_page_lists_openstreetmap(self) -> None:
        """Page mentions OpenStreetMap with a link."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("OpenStreetMap", content)
        self.assertIn(
            "https://www.openstreetmap.org/copyright", content,
        )

    def test_page_shows_author(self) -> None:
        """Page displays the author name."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("Mike Woodward", content)

    def test_active_page_context(self) -> None:
        """Active nav tab is set to about."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("nav-tab--active", content)

    def test_all_service_links_open_in_new_tab(self) -> None:
        """External service links have target=_blank for safety."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn('target="_blank"', content)
        self.assertIn('rel="noopener"', content)


class StationAPIViewsTest(SimpleTestCase):
    """Integration tests for station-related JSON API endpoints (story 3.3)."""

    def test_api_station_detail_returns_200_for_valid_station(
        self,
    ) -> None:
        """GET /api/station/place-knncl/ returns station JSON with expected keys."""
        response = self.client.get("/api/station/place-knncl/")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("id", data)
        self.assertEqual(data["id"], "place-knncl")
        self.assertIn("name", data)
        self.assertIn("latitude", data)
        self.assertIn("longitude", data)
        self.assertIn("facilities", data)
        self.assertIsInstance(data["facilities"], list)
        self.assertIn("lines_served", data)
        self.assertIsInstance(data["lines_served"], list)
        self.assertGreater(
            len(data["lines_served"]), 0,
            "Station should serve at least one line",
        )

    def test_api_station_detail_returns_404_for_invalid_station(
        self,
    ) -> None:
        """GET /api/station/place-xxxxx/ returns 404."""
        response = self.client.get("/api/station/place-xxxxx/")
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_api_station_predictions_returns_200_with_predictions_array(
        self,
    ) -> None:
        """GET /api/station/place-knncl/predictions/ returns predictions array."""
        response = self.client.get(
            "/api/station/place-knncl/predictions/",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["station_id"], "place-knncl")
        self.assertIn("predictions", data)
        self.assertIsInstance(data["predictions"], list)
        for pred in data["predictions"]:
            self.assertIn("route", pred)
            self.assertIn("destination", pred)

    def test_api_station_predictions_returns_404_for_invalid_station(
        self,
    ) -> None:
        """GET /api/station/place-xxxxx/predictions/ returns 404."""
        response = self.client.get(
            "/api/station/place-xxxxx/predictions/",
        )
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn("error", data)
