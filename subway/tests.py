"""Tests for the MBTA subway service layer and API views.

These are integration tests that hit the live MBTA V3 API.
Requires a valid MBTA_V3_API_KEY in the project root .env file.
"""

import json
import re

from django.test import SimpleTestCase
from pydantic import ValidationError

from subway.schemas import (
    AlertSchema,
    LineSchema,
    PredictionSchema,
    StationBriefSchema,
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

    def test_page_documents_mbta_license(self) -> None:
        """About page references the MassDOT Developers License Agreement."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("MassDOT Developers License Agreement", content)

    def test_page_documents_osm_tile_usage_policy(self) -> None:
        """About page links to the OSM tile usage policy."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn(
            "operations.osmfoundation.org/policies/tiles/", content,
        )

    def test_page_documents_leaflet_license(self) -> None:
        """About page links to the Leaflet BSD 2-Clause license."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("BSD 2-Clause License", content)
        self.assertIn(
            "github.com/Leaflet/Leaflet/blob/main/LICENSE", content,
        )

    def test_page_has_attribution_section(self) -> None:
        """About page includes a section explaining map attribution."""
        response = self.client.get("/about/")
        content = response.content.decode()
        self.assertIn("Attribution", content)
        self.assertIn("attribution", content.lower())


class ZoomToFitTest(SimpleTestCase):
    """Validate every line has station coordinates suitable for fitBounds (story 8.2).

    Ensures that each subway line returns stations with valid latitude/longitude
    values within the greater Boston area, and that the Map & Facilities page and
    Trains & Alerts page can compute fitBounds from those coordinates.
    """

    BOSTON_LAT_MIN = 42.15
    BOSTON_LAT_MAX = 42.55
    BOSTON_LNG_MIN = -71.30
    BOSTON_LNG_MAX = -70.85

    def test_every_line_has_at_least_one_station(self) -> None:
        """Each line must have >=1 station so fitBounds can compute bounds."""
        line_names = get_line_names()
        for name in line_names:
            line = get_line(line_name=name)
            self.assertIsNotNone(
                line,
                f"Line '{name}' returned None",
            )
            self.assertGreater(
                len(line.stations), 0,
                f"Line '{name}' has no stations — fitBounds would fail",
            )

    def test_every_station_has_valid_coordinates(self) -> None:
        """All stations must have numeric latitude and longitude."""
        line_names = get_line_names()
        for name in line_names:
            line = get_line(line_name=name)
            for station in line.stations:
                self.assertIsInstance(
                    station.latitude, float,
                    f"Station '{station.name}' on '{name}' has "
                    f"non-float latitude: {station.latitude!r}",
                )
                self.assertIsInstance(
                    station.longitude, float,
                    f"Station '{station.name}' on '{name}' has "
                    f"non-float longitude: {station.longitude!r}",
                )

    def test_station_coordinates_within_boston_area(self) -> None:
        """Station coordinates should fall within greater Boston bounds."""
        line_names = get_line_names()
        for name in line_names:
            line = get_line(line_name=name)
            for station in line.stations:
                self.assertGreaterEqual(
                    station.latitude, self.BOSTON_LAT_MIN,
                    f"Station '{station.name}' latitude {station.latitude} "
                    f"is south of expected Boston area",
                )
                self.assertLessEqual(
                    station.latitude, self.BOSTON_LAT_MAX,
                    f"Station '{station.name}' latitude {station.latitude} "
                    f"is north of expected Boston area",
                )
                self.assertGreaterEqual(
                    station.longitude, self.BOSTON_LNG_MIN,
                    f"Station '{station.name}' longitude {station.longitude} "
                    f"is west of expected Boston area",
                )
                self.assertLessEqual(
                    station.longitude, self.BOSTON_LNG_MAX,
                    f"Station '{station.name}' longitude {station.longitude} "
                    f"is east of expected Boston area",
                )

    def test_api_line_detail_returns_stations_with_coordinates(
        self,
    ) -> None:
        """API line detail endpoint returns station objects with lat/lng for JS fitBounds."""
        line_names = get_line_names()
        for name in line_names:
            response = self.client.get(
                f"/api/line/{name.replace(' ', '%20')}/",
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            stations = data.get("stations", [])
            self.assertGreater(
                len(stations), 0,
                f"API returned no stations for '{name}'",
            )
            for station in stations:
                self.assertIn(
                    "latitude", station,
                    f"Station missing latitude in API response for '{name}'",
                )
                self.assertIn(
                    "longitude", station,
                    f"Station missing longitude in API response for '{name}'",
                )

    def test_all_lines_combined_produce_valid_bounds(self) -> None:
        """Collecting stations from all lines yields a valid bounding box."""
        line_names = get_line_names()
        all_lats = []
        all_lngs = []
        for name in line_names:
            line = get_line(line_name=name)
            for station in line.stations:
                all_lats.append(station.latitude)
                all_lngs.append(station.longitude)

        self.assertGreater(
            len(all_lats), 0,
            "No station coordinates found across all lines",
        )
        lat_range = max(all_lats) - min(all_lats)
        lng_range = max(all_lngs) - min(all_lngs)
        self.assertGreater(
            lat_range, 0,
            "All stations have the same latitude",
        )
        self.assertGreater(
            lng_range, 0,
            "All stations have the same longitude",
        )


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


class TypeCorrectnessTest(SimpleTestCase):
    """Verify field-level type correctness of service return values and API responses.

    Goes beyond instance checks to validate that every field in returned
    Pydantic models and JSON payloads has the expected Python/JSON type.
    """

    HEX_COLOR_RE = re.compile(r"^[0-9A-Fa-f]{6}$")

    # -- Service layer field types --

    def test_line_schema_field_types(self) -> None:
        """LineSchema fields have correct Python types after validation."""
        line = get_line(line_name="Red Line")
        self.assertIsInstance(line.line_color, str)
        self.assertRegex(
            line.line_color,
            self.HEX_COLOR_RE,
            "line_color must be a 6-digit hex string",
        )
        self.assertIsInstance(line.shapes, list)
        for segment in line.shapes:
            self.assertIsInstance(segment, list)
            for point in segment:
                self.assertIsInstance(point, tuple)
                self.assertEqual(len(point), 2)
                self.assertIsInstance(point[0], float)
                self.assertIsInstance(point[1], float)

        self.assertIsInstance(line.stations, list)
        for station in line.stations:
            self.assertIsInstance(station, StationBriefSchema)

    def test_station_brief_schema_field_types(self) -> None:
        """StationBriefSchema fields within a line have correct types."""
        line = get_line(line_name="Red Line")
        station = line.stations[0]
        self.assertIsInstance(station.station_id, str)
        self.assertGreater(len(station.station_id), 0)
        self.assertIsInstance(station.name, str)
        self.assertGreater(len(station.name), 0)
        self.assertIsInstance(station.latitude, float)
        self.assertIsInstance(station.longitude, float)
        self.assertIn(
            type(station.address), (str, type(None)),
        )

    def test_station_detail_schema_field_types(self) -> None:
        """StationDetailSchema fields have correct Python types."""
        station = get_station(station_id="place-knncl")
        self.assertIsInstance(station.id, str)
        self.assertIsInstance(station.name, str)
        self.assertIsInstance(station.latitude, float)
        self.assertIsInstance(station.longitude, float)
        self.assertIn(
            type(station.address), (str, type(None)),
        )
        self.assertIsInstance(station.facilities, list)
        for facility in station.facilities:
            self.assertIsInstance(facility, str)
        self.assertIsInstance(station.lines_served, list)
        for line_name in station.lines_served:
            self.assertIsInstance(line_name, str)

    def test_alert_schema_field_types(self) -> None:
        """AlertSchema fields have correct Python types for every alert."""
        for name in get_line_names():
            alerts = get_line_alerts(line_name=name)
            for alert in alerts:
                self.assertIsInstance(
                    alert.headline, str,
                    f"Alert headline on '{name}' is not str",
                )
                self.assertIsInstance(
                    alert.severity, int,
                    f"Alert severity on '{name}' is not int",
                )

    def test_prediction_schema_field_types(self) -> None:
        """PredictionSchema fields have correct Python types."""
        preds = get_predictions(station_id="place-knncl")
        for pred in preds:
            self.assertIsInstance(pred.route, str)
            self.assertIsInstance(pred.destination, str)
            self.assertIn(
                type(pred.arrival_time), (str, type(None)),
            )
            self.assertIn(
                type(pred.departure_time), (str, type(None)),
            )
            self.assertIn(
                type(pred.comments), (str, type(None)),
            )

    # -- API response JSON field types --

    def test_api_lines_json_types(self) -> None:
        """GET /api/lines/ returns JSON with list of strings."""
        data = json.loads(
            self.client.get("/api/lines/").content,
        )
        self.assertIsInstance(data, dict)
        self.assertIsInstance(data["lines"], list)
        for name in data["lines"]:
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)

    def test_api_line_detail_json_types(self) -> None:
        """GET /api/line/<name>/ returns JSON with correct field types."""
        data = json.loads(
            self.client.get("/api/line/Red%20Line/").content,
        )
        self.assertIsInstance(data["line_name"], str)
        self.assertIsInstance(data["line_color"], str)
        self.assertRegex(data["line_color"], self.HEX_COLOR_RE)
        self.assertIsInstance(data["shapes"], list)
        self.assertIsInstance(data["stations"], list)
        station = data["stations"][0]
        self.assertIsInstance(station["station_id"], str)
        self.assertIsInstance(station["name"], str)
        self.assertIsInstance(station["latitude"], float)
        self.assertIsInstance(station["longitude"], float)

    def test_api_line_alerts_json_types(self) -> None:
        """GET /api/line/<name>/alerts/ returns JSON with correct field types."""
        data = json.loads(
            self.client.get(
                "/api/line/Red%20Line/alerts/",
            ).content,
        )
        self.assertIsInstance(data["line_name"], str)
        self.assertIsInstance(data["alerts"], list)
        for alert in data["alerts"]:
            self.assertIsInstance(alert["headline"], str)
            self.assertIsInstance(alert["severity"], int)

    def test_api_station_detail_json_types(self) -> None:
        """GET /api/station/<id>/ returns JSON with correct field types."""
        data = json.loads(
            self.client.get("/api/station/place-knncl/").content,
        )
        self.assertIsInstance(data["id"], str)
        self.assertIsInstance(data["name"], str)
        self.assertIsInstance(data["latitude"], float)
        self.assertIsInstance(data["longitude"], float)
        self.assertIsInstance(data["facilities"], list)
        for f in data["facilities"]:
            self.assertIsInstance(f, str)
        self.assertIsInstance(data["lines_served"], list)
        for ls in data["lines_served"]:
            self.assertIsInstance(ls, str)

    def test_api_station_predictions_json_types(self) -> None:
        """GET /api/station/<id>/predictions/ returns JSON with correct field types."""
        data = json.loads(
            self.client.get(
                "/api/station/place-knncl/predictions/",
            ).content,
        )
        self.assertIsInstance(data["station_id"], str)
        self.assertIsInstance(data["predictions"], list)
        for pred in data["predictions"]:
            self.assertIsInstance(pred["route"], str)
            self.assertIsInstance(pred["destination"], str)
            self.assertIn(
                type(pred.get("arrival_time")),
                (str, type(None)),
            )
            self.assertIn(
                type(pred.get("departure_time")),
                (str, type(None)),
            )

    def test_api_404_error_json_types(self) -> None:
        """404 responses return JSON with a string 'error' field."""
        error_urls = [
            "/api/line/Nonexistent%20Line/",
            "/api/line/Nonexistent%20Line/alerts/",
            "/api/station/place-xxxxx/",
            "/api/station/place-xxxxx/predictions/",
        ]
        for url in error_urls:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, 404,
                f"Expected 404 for {url}",
            )
            data = json.loads(response.content)
            self.assertIsInstance(
                data["error"], str,
                f"Error field is not a string for {url}",
            )


class SchemaValidationTest(SimpleTestCase):
    """Verify Pydantic schemas reject data with wrong types.

    Ensures the data contracts are enforced so type mismatches
    are caught at the validation boundary.
    """

    def test_line_schema_rejects_non_string_color(self) -> None:
        """LineSchema rejects non-string line_color."""
        with self.assertRaises(ValidationError):
            LineSchema(
                line_color=123456,
                shapes=[],
                stations=[],
            )

    def test_line_schema_rejects_non_list_shapes(self) -> None:
        """LineSchema rejects shapes that aren't a list."""
        with self.assertRaises(ValidationError):
            LineSchema(
                line_color="DA291C",
                shapes="not-a-list",
                stations=[],
            )

    def test_station_brief_rejects_non_float_latitude(self) -> None:
        """StationBriefSchema rejects non-numeric latitude."""
        with self.assertRaises(ValidationError):
            StationBriefSchema(
                station_id="place-test",
                name="Test",
                latitude="not-a-float",
                longitude=-71.0,
            )

    def test_station_detail_rejects_non_list_facilities(self) -> None:
        """StationDetailSchema rejects facilities that aren't a list."""
        with self.assertRaises(ValidationError):
            StationDetailSchema(
                id="place-test",
                name="Test",
                latitude=42.36,
                longitude=-71.06,
                facilities="not-a-list",
            )

    def test_alert_schema_rejects_non_int_severity(self) -> None:
        """AlertSchema rejects non-integer severity."""
        with self.assertRaises(ValidationError):
            AlertSchema(
                headline="Test alert",
                severity="high",
            )

    def test_prediction_schema_rejects_missing_required_fields(
        self,
    ) -> None:
        """PredictionSchema rejects data missing required route and destination."""
        with self.assertRaises(ValidationError):
            PredictionSchema(
                route="Red",
            )
        with self.assertRaises(ValidationError):
            PredictionSchema(
                destination="Alewife",
            )

    def test_prediction_schema_accepts_optional_none_fields(
        self,
    ) -> None:
        """PredictionSchema accepts None for optional time/comments fields."""
        pred = PredictionSchema(
            route="Red",
            destination="Alewife",
            arrival_time=None,
            departure_time=None,
            comments=None,
        )
        self.assertIsNone(pred.arrival_time)
        self.assertIsNone(pred.departure_time)
        self.assertIsNone(pred.comments)

    def test_station_detail_schema_accepts_optional_defaults(
        self,
    ) -> None:
        """StationDetailSchema defaults optional fields correctly."""
        station = StationDetailSchema(
            id="place-test",
            name="Test Station",
            latitude=42.36,
            longitude=-71.06,
        )
        self.assertIsNone(station.address)
        self.assertEqual(station.facilities, [])
        self.assertEqual(station.lines_served, [])
