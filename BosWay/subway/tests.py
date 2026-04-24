"""Focused tests for the BosWay project scaffold."""

import importlib
from pathlib import Path
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
            [
                {
                    "line": "Red",
                    "destination": "Alewife",
                    "arrival_time": "2026-04-23T12:15:00Z",
                    "departure_time": None,
                    "status": "Boarding",
                },
            ],
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

    @staticmethod
    def _build_fake_mbta_service(
        *,
        line_names: list[str] | None = None,
        line_payload: dict[str, object] | None = None,
        station_payload: dict[str, object] | None = None,
        station_facilities: list[str] | None = None,
        alert_payloads: list[dict[str, object]] | None = None,
        prediction_payloads: list[dict[str, object]] | None = None,
        lines: list[dict[str, object]] | None = None,
    ) -> object:
        """Create a fake MBTA client with predictable schema payloads.

        Args:
            line_names: Optional line-name list for name lookups.
            line_payload: Optional raw line payload for `get_line`.
            station_payload: Optional raw station payload for `get_station`.
            station_facilities: Optional raw facilities list.
            alert_payloads: Optional raw alerts list.
            prediction_payloads: Optional raw predictions list.
            lines: Optional cached line payloads for membership checks.

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
                self._prediction_payloads = prediction_payloads or []

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
                return self._alert_payloads

            def get_predictions(
                self,
                *,
                station_id: str,
            ) -> list[dict[str, object]]:
                """Return the configured fake station predictions."""
                _ = station_id
                return self._prediction_payloads

        return FakeMBTAService()
