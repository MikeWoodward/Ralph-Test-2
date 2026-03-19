"use strict";

/**
 * Trains & Alerts page — Leaflet map initialization and interaction.
 *
 * Initializes an OpenStreetMap-backed Leaflet map centered on the Boston
 * MBTA subway system, fetches all line data, and renders lines as colored
 * polylines with station markers.
 *
 * Depends on: map_utils.js (loaded before this script).
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

/** Tracks drawn layers so they can be cleared on line change (story 7.1). */
let currentShapesLayer = null;
let currentStationsLayer = null;

/**
 * Fetch all subway lines and draw them on the map.
 * This provides the initial visual rendering; story 7.1 will refine
 * to draw only the selected line from the dropdown.
 */
async function loadAndDrawAllLines() {
    try {
        const lineNames = await fetchLineNames();

        const lineDataPromises = lineNames.map((name) => fetchLineData(name));
        const lineDataResults = await Promise.all(lineDataPromises);

        const allShapesGroup = L.layerGroup();
        const allStationsGroup = L.layerGroup();

        lineDataResults
            .filter((data) => data !== null)
            .forEach((lineData) => {
                const { shapesLayer, stationsLayer } = drawLine(map, lineData);

                shapesLayer.eachLayer((layer) => allShapesGroup.addLayer(layer));
                stationsLayer.eachLayer((layer) => allStationsGroup.addLayer(layer));

                shapesLayer.remove();
                stationsLayer.remove();
            });

        allShapesGroup.addTo(map);
        allStationsGroup.addTo(map);

        currentShapesLayer = allShapesGroup;
        currentStationsLayer = allStationsGroup;
    } catch (error) {
        console.error("Error loading subway lines:", error);
    }
}

loadAndDrawAllLines();
