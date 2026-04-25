"""Pydantic schemas for MBTA-backed subway responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class FacilitySchema(BaseModel):
    """Represent one station facility label."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str


class StationSummarySchema(BaseModel):
    """Represent summary information for a station marker."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    station_id: str
    name: str
    latitude: float
    longitude: float
    address: str | None = None


class LineSchema(BaseModel):
    """Represent one subway line for map rendering."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str
    color: str
    shapes: list[list[tuple[float, float]]]
    stations: list[StationSummarySchema]


class StationDetailSchema(BaseModel):
    """Represent detailed station data for facilities views."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    station_id: str
    name: str
    latitude: float
    longitude: float
    address: str | None = None
    lines_served: list[str]
    facilities: list[str]


class AlertSchema(BaseModel):
    """Represent one active service alert."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    headline: str
    description: str | None = None
    severity: int | None = None


class PredictionSchema(BaseModel):
    """Represent one predicted train arrival or departure."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    line: str
    destination: str
    arrival_time: datetime | None = None
    departure_time: datetime | None = None
    status: str | None = None
