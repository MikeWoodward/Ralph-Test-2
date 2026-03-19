"""Service layer for the MBTA subway app.

Provides a singleton MBTA client and wrapper functions that transform
raw API data into validated Pydantic models.  The MBTA instance is
created at module level (cheap — just loads the API key), while the
expensive ``initialize()`` call is deferred to first use.
"""

from __future__ import annotations

import logging

from subway.MBTA_class import MBTA
from subway.schemas import (
    AlertSchema,
    LineSchema,
    PredictionSchema,
    StationDetailSchema,
)

logger = logging.getLogger(__name__)

_mbta_client: MBTA = MBTA()
_initialized: bool = False


def _ensure_initialized() -> None:
    """Trigger MBTA client initialization on first use (~3 s of API calls)."""
    global _initialized
    if not _initialized:
        logger.info(
            "Initializing MBTA client (this takes a few seconds)…",
        )
        _mbta_client.initialize()
        logger.info(
            "MBTA client ready — %d lines loaded.",
            len(_mbta_client.lines),
        )
        _initialized = True


def get_line_names() -> list[str]:
    """Return all subway line names sorted alphabetically.

    Returns:
        Sorted list of line display names
        (e.g. ``['Blue Line', 'Green Line', …]``).
    """
    _ensure_initialized()
    return _mbta_client.get_line_names()


def get_line(
    *,
    line_name: str,
) -> LineSchema | None:
    """Return line data validated against ``LineSchema``.

    Args:
        line_name: Display name of the line (e.g. ``'Red Line'``).

    Returns:
        Validated ``LineSchema`` or ``None`` if the line is not found.
    """
    _ensure_initialized()
    data = _mbta_client.get_line(line_name=line_name)
    if data is None:
        return None
    return LineSchema.model_validate(data)


def get_line_alerts(
    *,
    line_name: str,
) -> list[AlertSchema]:
    """Return alerts for a line, transformed from raw MBTA API format.

    Raw alerts nest data under ``attributes``; this function extracts
    ``attributes.header`` -> ``headline`` and
    ``attributes.severity`` -> ``severity``.

    Args:
        line_name: Display name of the line (e.g. ``'Red Line'``).

    Returns:
        List of validated ``AlertSchema`` instances sorted by severity.
    """
    _ensure_initialized()
    raw_alerts = _mbta_client.get_line_alerts(line_name=line_name)
    return [
        AlertSchema(
            headline=alert.get("attributes", {}).get(
                "header", "Unknown",
            ),
            severity=alert.get("attributes", {}).get(
                "severity", 0,
            ),
        )
        for alert in raw_alerts
    ]


def get_station(
    *,
    station_id: str,
) -> StationDetailSchema | None:
    """Return station details with computed ``lines_served``.

    The MBTA class does not return ``lines_served``; this function
    computes it by checking which cached lines include the station.

    Args:
        station_id: MBTA stop ID (e.g. ``'place-knncl'``).

    Returns:
        Validated ``StationDetailSchema`` or ``None`` if not found.
    """
    _ensure_initialized()
    data = _mbta_client.get_station(station_id=station_id)
    if data is None:
        return None

    lines_served = [
        line["name"]
        for line in _mbta_client.lines
        if any(
            station["station_id"] == station_id
            for station in line.get("stations", [])
        )
    ]
    data["lines_served"] = lines_served
    return StationDetailSchema.model_validate(data)


def get_predictions(
    *,
    station_id: str,
) -> list[PredictionSchema]:
    """Return train predictions validated against ``PredictionSchema``.

    Prediction dicts from the MBTA class are already flat and match
    the schema directly — no transformation is needed.

    Args:
        station_id: MBTA stop ID (e.g. ``'place-knncl'``).

    Returns:
        List of validated ``PredictionSchema`` instances.
    """
    _ensure_initialized()
    raw_predictions = _mbta_client.get_predictions(
        station_id=station_id,
    )
    return [
        PredictionSchema.model_validate(prediction)
        for prediction in raw_predictions
    ]
