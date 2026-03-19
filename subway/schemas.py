"""Pydantic schemas for MBTA subway API responses.

These schemas define the data contracts for the JSON API endpoints.
The service layer transforms raw MBTA API data into these models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StationBriefSchema(BaseModel):
    """Brief station info included in line data."""

    station_id: str = Field(
        description="MBTA stop ID (e.g. 'place-knncl')",
    )
    name: str = Field(
        description="Display name of the station",
    )
    latitude: float = Field(
        description="Latitude coordinate",
    )
    longitude: float = Field(
        description="Longitude coordinate",
    )
    address: str | None = Field(
        default=None,
        description="Street address, if available",
    )


class LineSchema(BaseModel):
    """Schema for a subway line returned by GET /api/line/<name>."""

    line_color: str = Field(
        description="Hex color code without '#' (e.g. 'DA291C')",
    )
    shapes: list[list[tuple[float, float]]] = Field(
        description="Polyline coordinates per shape segment",
    )
    stations: list[StationBriefSchema] = Field(
        description="Stations on this line",
    )


class StationDetailSchema(BaseModel):
    """Full station info returned by GET /api/station/<station_id>."""

    id: str = Field(
        description="MBTA stop ID (e.g. 'place-knncl')",
    )
    name: str = Field(
        description="Display name of the station",
    )
    latitude: float = Field(
        description="Latitude coordinate",
    )
    longitude: float = Field(
        description="Longitude coordinate",
    )
    address: str | None = Field(
        default=None,
        description="Street address, if available",
    )
    facilities: list[str] = Field(
        default_factory=list,
        description="Facility descriptions",
    )
    lines_served: list[str] = Field(
        default_factory=list,
        description="Names of subway lines serving this station",
    )


class AlertSchema(BaseModel):
    """Schema for a single alert returned by GET /api/line/<name>/alerts."""

    headline: str = Field(
        description="Alert header text",
    )
    severity: int = Field(
        description="Severity level (lower = more severe)",
    )


class PredictionSchema(BaseModel):
    """Schema for a train prediction returned by GET /api/station/<id>/predictions."""

    route: str = Field(
        description="Route ID (e.g. 'Red', 'Green-B')",
    )
    destination: str = Field(
        description="Trip headsign (e.g. 'Alewife')",
    )
    arrival_time: str | None = Field(
        default=None,
        description="ISO 8601 arrival time, or None",
    )
    departure_time: str | None = Field(
        default=None,
        description="ISO 8601 departure time, or None",
    )
    comments: str | None = Field(
        default=None,
        description="Status text (e.g. 'Boarding'), or None",
    )
