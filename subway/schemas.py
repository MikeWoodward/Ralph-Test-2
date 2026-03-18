"""Pydantic models for MBTA subway API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StationSchema(BaseModel):
    """Schema for station data returned by the MBTA class.

    When used inside a LineSchema, facilities will be None since
    line-level station data doesn't include facility information.
    When fetched individually via get_station(), facilities will
    be populated.
    """

    station_id: str
    name: str
    latitude: float
    longitude: float
    address: str | None = None
    facilities: list[str] | None = None


class LineSchema(BaseModel):
    """Schema for subway line data.

    Shapes are lists of coordinate pairs (latitude, longitude)
    representing polyline segments for the line's route.
    """

    name: str | None = None
    line_color: str
    shapes: list[list[tuple[float, float]]]
    stations: list[StationSchema]


class AlertSchema(BaseModel):
    """Schema for MBTA service alert data."""

    headline: str
    severity: int


class PredictionSchema(BaseModel):
    """Schema for train arrival/departure prediction data."""

    route: str
    destination: str
    arrival_time: str | None = None
    departure_time: str | None = None
    comments: str | None = None
