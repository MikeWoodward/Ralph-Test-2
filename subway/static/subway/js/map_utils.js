"use strict";

/**
 * Shared Leaflet map utilities for drawing MBTA subway lines and stations.
 *
 * Both the Trains & Alerts page (app.js) and Map & Facilities page
 * (map_facilities.js) import these helpers to render lines and stations
 * with a consistent visual style matching MBTA conventions.
 */

const POLYLINE_WEIGHT = 4;
const POLYLINE_OPACITY = 0.85;

const STATION_RADIUS = 6;
const STATION_FILL_COLOR = "#ffffff";
const STATION_FILL_OPACITY = 1;
const STATION_BORDER_WEIGHT = 3;

/**
 * Draw a line's shape segments as thick colored polylines on the map.
 *
 * @param {L.Map} map - Leaflet map instance.
 * @param {Array<Array<Array<number>>>} shapes - Nested array of [lat, lng] coordinate pairs per segment.
 * @param {string} hexColor - Hex color without '#' (e.g. "DA291C").
 * @param {Object} [options] - Optional Leaflet polyline options overrides.
 * @returns {L.LayerGroup} Layer group containing all polyline segments (already added to map).
 */
function drawLineShapes(map, shapes, hexColor, options = {}) {
    const color = `#${hexColor}`;
    const defaults = {
        color,
        weight: POLYLINE_WEIGHT,
        opacity: POLYLINE_OPACITY,
        lineJoin: "round",
        lineCap: "round",
    };
    const mergedOptions = { ...defaults, ...options };

    const layerGroup = L.layerGroup();

    shapes.forEach((segment) => {
        const latLngs = segment.map(([lat, lng]) => [lat, lng]);
        L.polyline(latLngs, mergedOptions).addTo(layerGroup);
    });

    layerGroup.addTo(map);
    return layerGroup;
}

/**
 * Draw stations as CircleMarkers with a colored border and white fill.
 *
 * Each marker stores the station's metadata (id, name) in its `options`
 * so click handlers in page-specific scripts can access them.
 *
 * @param {L.Map} map - Leaflet map instance.
 * @param {Array<Object>} stations - Station objects with station_id, name, latitude, longitude.
 * @param {string} hexColor - Hex color without '#' (e.g. "DA291C").
 * @param {Object} [options] - Optional Leaflet circleMarker options overrides.
 * @returns {L.LayerGroup} Layer group containing all station markers (already added to map).
 */
function drawStationMarkers(map, stations, hexColor, options = {}) {
    const color = `#${hexColor}`;
    const defaults = {
        radius: STATION_RADIUS,
        fillColor: STATION_FILL_COLOR,
        fillOpacity: STATION_FILL_OPACITY,
        color,
        weight: STATION_BORDER_WEIGHT,
        opacity: 1,
    };
    const mergedOptions = { ...defaults, ...options };

    const layerGroup = L.layerGroup();

    stations.forEach((station) => {
        const marker = L.circleMarker(
            [station.latitude, station.longitude],
            {
                ...mergedOptions,
                stationId: station.station_id,
                stationName: station.name,
            },
        );
        marker.addTo(layerGroup);
    });

    layerGroup.addTo(map);
    return layerGroup;
}

/**
 * Fetch line data from the API for a given line name.
 *
 * @param {string} lineName - Display name of the line (e.g. "Red Line").
 * @returns {Promise<Object|null>} Line data object or null on error.
 */
async function fetchLineData(lineName) {
    try {
        const encoded = encodeURIComponent(lineName);
        const response = await fetch(`/api/line/${encoded}/`);
        if (!response.ok) {
            console.error(`Failed to fetch line "${lineName}": ${response.status}`);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(`Error fetching line "${lineName}":`, error);
        return null;
    }
}

/**
 * Fetch all line names from the API.
 *
 * @returns {Promise<Array<string>>} Array of line name strings, or empty array on error.
 */
async function fetchLineNames() {
    try {
        const response = await fetch("/api/lines/");
        if (!response.ok) {
            console.error(`Failed to fetch line names: ${response.status}`);
            return [];
        }
        const data = await response.json();
        return data.lines ?? [];
    } catch (error) {
        console.error("Error fetching line names:", error);
        return [];
    }
}

/**
 * Draw a complete subway line (shapes + station markers) on the map.
 *
 * @param {L.Map} map - Leaflet map instance.
 * @param {Object} lineData - API response with line_color, shapes, stations.
 * @param {Object} [polylineOptions] - Optional polyline overrides.
 * @param {Object} [markerOptions] - Optional circleMarker overrides.
 * @returns {{ shapesLayer: L.LayerGroup, stationsLayer: L.LayerGroup }}
 */
function drawLine(map, lineData, polylineOptions = {}, markerOptions = {}) {
    const shapesLayer = drawLineShapes(
        map,
        lineData.shapes,
        lineData.line_color,
        polylineOptions,
    );
    const stationsLayer = drawStationMarkers(
        map,
        lineData.stations,
        lineData.line_color,
        markerOptions,
    );
    return { shapesLayer, stationsLayer };
}

/**
 * Compute a Leaflet LatLngBounds from an array of station objects.
 *
 * @param {Array<Object>} stations - Station objects with latitude, longitude.
 * @returns {L.LatLngBounds|null} Bounds enclosing all stations, or null if empty.
 */
function getStationBounds(stations) {
    if (!stations || stations.length === 0) return null;
    const latLngs = stations.map((s) => [s.latitude, s.longitude]);
    return L.latLngBounds(latLngs);
}
