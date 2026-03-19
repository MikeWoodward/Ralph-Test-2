"""Tests for the MBTA subway service layer.

These are integration tests that hit the live MBTA V3 API.
Requires a valid MBTA_V3_API_KEY in the project root .env file.
"""

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
