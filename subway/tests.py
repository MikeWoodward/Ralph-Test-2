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
