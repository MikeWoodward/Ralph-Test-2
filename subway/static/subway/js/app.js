"use strict";

/**
 * Trains & Alerts page — Leaflet map initialization and interaction.
 *
 * Initializes an OpenStreetMap-backed Leaflet map centered on the Boston
 * MBTA subway system. Subsequent stories add line rendering, alerts, and
 * station popups on top of this base map.
 */

const BOSTON_CENTER = [42.3601, -71.0589];
const DEFAULT_ZOOM = 12;

const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">' +
    "OpenStreetMap</a> contributors";

const map = L.map("map", {
    center: BOSTON_CENTER,
    zoom: DEFAULT_ZOOM,
    zoomControl: true,
});

L.tileLayer(TILE_URL, {
    attribution: TILE_ATTRIBUTION,
    maxZoom: 19,
}).addTo(map);
