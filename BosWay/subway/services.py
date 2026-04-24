"""Shared MBTA service integration for the subway app."""

from __future__ import annotations

import importlib.util
import linecache
import logging
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any

from dotenv import load_dotenv

from .schemas import AlertSchema
from .schemas import FacilitySchema
from .schemas import LineSchema
from .schemas import PredictionSchema
from .schemas import StationDetailSchema
from .schemas import StationSummarySchema

LOGGER = logging.getLogger(__name__)

_MBTA_CLASS: type[Any] | None = None
_MBTA_SERVICE: Any | None = None
_MBTA_INITIALIZED = False
_SERVICE_LOCK = Lock()
_INITIALIZE_LOCK = Lock()


def _log_exception_details(
    *,
    error: Exception,
) -> None:
    """Log the line number and source text for an exception.

    Args:
        error: The exception that was raised.
    """
    traceback_frame = error.__traceback__
    while traceback_frame and traceback_frame.tb_next:
        traceback_frame = traceback_frame.tb_next

    if traceback_frame is None:
        LOGGER.exception("Unhandled exception: %s", error)
        return

    line_number = traceback_frame.tb_lineno
    file_path = traceback_frame.tb_frame.f_code.co_filename
    source_line = linecache.getline(
        file_path,
        line_number,
    ).strip()
    LOGGER.exception(
        "Unhandled exception at %s:%s: %s | %s",
        file_path,
        line_number,
        source_line or "<source unavailable>",
        error,
    )


def _repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


def _mbta_module_path() -> Path:
    """Return the sibling MBTA client source file path."""
    return _repo_root().parent / "MBTA-API" / "MBTA_class.py"


def _load_repo_environment() -> None:
    """Load server-side environment variables from the repo root."""
    load_dotenv(
        dotenv_path=_repo_root() / ".env",
        override=False,
    )


def _load_mbta_module() -> ModuleType:
    """Load the sibling MBTA module from disk.

    Returns:
        The imported module object containing the MBTA class.

    Raises:
        FileNotFoundError: If the sibling MBTA source file is missing.
        ImportError: If the sibling MBTA module cannot be loaded.
    """
    mbta_source_path = _mbta_module_path()
    if not mbta_source_path.exists():
        raise FileNotFoundError(
            f"MBTA client file not found: {mbta_source_path}",
        )

    spec = importlib.util.spec_from_file_location(
        "subway_external_mbta",
        mbta_source_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load module spec for {mbta_source_path}",
        )

    mbta_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mbta_module)
    return mbta_module


def _load_mbta_class() -> type[Any]:
    """Return the MBTA class from the sibling MBTA project.

    Returns:
        The imported MBTA class.
    """
    global _MBTA_CLASS

    if _MBTA_CLASS is None:
        _MBTA_CLASS = _load_mbta_module().MBTA

    return _MBTA_CLASS


def get_mbta_service() -> Any:
    """Return the shared MBTA client instance for the app.

    Returns:
        The singleton MBTA client instance.
    """
    global _MBTA_SERVICE

    if _MBTA_SERVICE is not None:
        return _MBTA_SERVICE

    with _SERVICE_LOCK:
        if _MBTA_SERVICE is None:
            try:
                _load_repo_environment()
                mbta_class = _load_mbta_class()
                _MBTA_SERVICE = mbta_class()
            except Exception as error:  # noqa: BLE001
                _log_exception_details(error=error)
                raise

    return _MBTA_SERVICE


def initialize_service() -> Any:
    """Initialize the shared MBTA client once at startup.

    Returns:
        The initialized singleton MBTA client instance.
    """
    global _MBTA_INITIALIZED

    mbta_service = get_mbta_service()
    if _MBTA_INITIALIZED:
        return mbta_service

    with _INITIALIZE_LOCK:
        if not _MBTA_INITIALIZED:
            try:
                mbta_service.initialize()
            except Exception as error:  # noqa: BLE001
                _log_exception_details(error=error)
                raise

            _MBTA_INITIALIZED = True

    return mbta_service


def _station_identifier(
    *,
    station_data: dict[str, Any],
) -> str:
    """Return a normalized station identifier from raw MBTA data.

    Args:
        station_data: Raw station payload from the MBTA client.

    Returns:
        The station identifier used across schemas and responses.
    """
    return str(
        station_data.get("station_id")
        or station_data.get("id")
        or "",
    )


def _normalize_station_summary(
    *,
    station_data: dict[str, Any],
) -> StationSummarySchema:
    """Validate a raw station summary payload.

    Args:
        station_data: Raw station dictionary from the MBTA client.

    Returns:
        The validated station summary schema.
    """
    return StationSummarySchema.model_validate(
        {
            "station_id": _station_identifier(
                station_data=station_data,
            ),
            "name": station_data.get("name") or "",
            "latitude": station_data.get("latitude"),
            "longitude": station_data.get("longitude"),
            "address": station_data.get("address") or None,
        },
    )


def _normalize_facility_labels(
    *,
    facility_labels: list[str],
) -> list[FacilitySchema]:
    """Validate raw facility labels into schema objects.

    Args:
        facility_labels: Raw facility labels from the MBTA client.

    Returns:
        A validated facility schema list.
    """
    return [
        FacilitySchema.model_validate({"label": facility_label})
        for facility_label in facility_labels
    ]


def _get_lines_served(
    *,
    station_id: str,
    mbta_service: Any,
) -> list[str]:
    """Return the subway lines that include a station in cached line data.

    Args:
        station_id: The MBTA station identifier.
        mbta_service: The initialized shared MBTA client.

    Returns:
        A sorted list of display line names that serve the station.
    """
    lines_served = [
        str(line.get("name") or "")
        for line in mbta_service.lines
        if any(
            _station_identifier(station_data=station_data) == station_id
            for station_data in line.get("stations", [])
        )
    ]
    return sorted(
        [
            line_name
            for line_name in lines_served
            if line_name
        ],
    )


def get_line_names() -> list[str]:
    """Return the available subway line names from the shared MBTA client.

    Returns:
        A sorted list of display names for the MBTA subway lines.
    """
    mbta_service = initialize_service()
    line_names = mbta_service.get_line_names()
    return sorted(
        [
            str(line_name)
            for line_name in line_names
            if line_name
        ],
    )


def get_line(
    *,
    line_name: str,
) -> LineSchema | None:
    """Return validated data for one subway line.

    Args:
        line_name: The display name of the subway line.

    Returns:
        A validated line schema, or `None` when the line is unknown.
    """
    mbta_service = initialize_service()
    raw_line = mbta_service.get_line(line_name=line_name)
    if raw_line is None:
        return None

    stations = [
        _normalize_station_summary(station_data=station_data)
        for station_data in raw_line.get("stations", [])
    ]
    return LineSchema.model_validate(
        {
            "name": line_name,
            "color": raw_line.get("line_color") or "",
            "shapes": raw_line.get("shapes") or [],
            "stations": stations,
        },
    )


def get_station(
    *,
    station_id: str,
) -> StationDetailSchema | None:
    """Return validated station detail data.

    Args:
        station_id: The MBTA station identifier.

    Returns:
        A validated station detail schema, or `None` when not found.
    """
    mbta_service = initialize_service()
    raw_station = mbta_service.get_station(station_id=station_id)
    if raw_station is None:
        return None

    facilities = _normalize_facility_labels(
        facility_labels=list(raw_station.get("facilities") or []),
    )
    return StationDetailSchema.model_validate(
        {
            "station_id": _station_identifier(
                station_data=raw_station,
            ),
            "name": raw_station.get("name") or "",
            "latitude": raw_station.get("latitude"),
            "longitude": raw_station.get("longitude"),
            "address": raw_station.get("address") or None,
            "lines_served": _get_lines_served(
                station_id=station_id,
                mbta_service=mbta_service,
            ),
            "facilities": [
                facility.label
                for facility in facilities
            ],
        },
    )


def get_station_facilities(
    *,
    station_id: str,
) -> list[FacilitySchema]:
    """Return validated facilities for one station.

    Args:
        station_id: The MBTA station identifier.

    Returns:
        A validated list of station facility schemas.
    """
    mbta_service = initialize_service()
    facility_labels = mbta_service.get_station_facilities(
        station_id=station_id,
    )
    return _normalize_facility_labels(
        facility_labels=list(facility_labels or []),
    )


def get_line_alerts(
    *,
    line_name: str,
) -> list[AlertSchema]:
    """Return validated alerts for one subway line.

    Args:
        line_name: The display name of the subway line.

    Returns:
        A validated list of alerts for the given line.
    """
    mbta_service = initialize_service()
    raw_alerts = mbta_service.get_line_alerts(line_name=line_name)
    return [
        AlertSchema.model_validate(
            {
                "id": raw_alert.get("id") or "",
                "headline": (
                    raw_alert.get("headline")
                    or raw_alert.get("attributes", {}).get("header")
                    or ""
                ),
                "description": (
                    raw_alert.get("description")
                    or raw_alert.get("attributes", {}).get("description")
                ),
                "severity": (
                    raw_alert.get("severity")
                    or raw_alert.get("attributes", {}).get("severity")
                ),
            },
        )
        for raw_alert in raw_alerts
    ]


def get_predictions(
    *,
    station_id: str,
) -> list[PredictionSchema]:
    """Return validated train predictions for one station.

    Args:
        station_id: The MBTA station identifier.

    Returns:
        A validated list of upcoming subway predictions.
    """
    mbta_service = initialize_service()
    raw_predictions = mbta_service.get_predictions(station_id=station_id)
    return [
        PredictionSchema.model_validate(
            {
                "line": (
                    raw_prediction.get("line")
                    or raw_prediction.get("route")
                    or ""
                ),
                "destination": raw_prediction.get("destination") or "",
                "arrival_time": raw_prediction.get("arrival_time"),
                "departure_time": raw_prediction.get("departure_time"),
                "status": (
                    raw_prediction.get("status")
                    or raw_prediction.get("comments")
                ),
            },
        )
        for raw_prediction in raw_predictions
    ]
