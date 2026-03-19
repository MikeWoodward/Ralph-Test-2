"use strict";

/**
 * Trains & Alerts page — Leaflet map initialization and interaction.
 *
 * On load, populates the line dropdown and draws all subway lines.
 * Selecting a line clears the map and redraws only that line, zoomed
 * to fit its stations. Resetting to "Choose a line" restores all lines.
 *
 * Depends on: map_utils.js (loaded before this script).
 */

const BOSTON_CENTER = [42.3601, -71.0589];
const DEFAULT_ZOOM = 12;
const FIT_BOUNDS_PADDING = [30, 30];

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

let currentShapesLayer = null;
let currentStationsLayer = null;

/** Cached line names to avoid re-fetching when resetting to all-lines view. */
let cachedLineNames = [];

const lineSelect = document.getElementById("line-select");

/** Remove any currently drawn line/station layers from the map. */
function clearCurrentLayers() {
    if (currentShapesLayer) {
        currentShapesLayer.remove();
        currentShapesLayer = null;
    }
    if (currentStationsLayer) {
        currentStationsLayer.remove();
        currentStationsLayer = null;
    }
}

/**
 * Fetch data for all lines and draw them on the map.
 *
 * @param {Array<string>} lineNames - Line names to fetch and draw.
 */
async function drawAllLines(lineNames) {
    const lineDataResults = await Promise.all(
        lineNames.map((name) => fetchLineData(name)),
    );

    const allShapesGroup = L.layerGroup();
    const allStationsGroup = L.layerGroup();

    lineDataResults
        .filter((data) => data !== null)
        .forEach((lineData) => {
            const { shapesLayer, stationsLayer } = drawLine(map, lineData);

            shapesLayer.eachLayer((layer) => allShapesGroup.addLayer(layer));
            stationsLayer.eachLayer((layer) =>
                allStationsGroup.addLayer(layer),
            );

            shapesLayer.remove();
            stationsLayer.remove();
        });

    allShapesGroup.addTo(map);
    allStationsGroup.addTo(map);

    currentShapesLayer = allShapesGroup;
    currentStationsLayer = allStationsGroup;
}

/**
 * Fetch a single line's data, draw it, and zoom to fit its stations.
 *
 * @param {string} lineName - Display name of the line to draw.
 */
async function drawSelectedLine(lineName) {
    const lineData = await fetchLineData(lineName);
    if (!lineData) {
        console.error(`No data returned for line "${lineName}"`);
        return;
    }

    const { shapesLayer, stationsLayer } = drawLine(map, lineData);
    currentShapesLayer = shapesLayer;
    currentStationsLayer = stationsLayer;

    const bounds = getStationBounds(lineData.stations);
    if (bounds) {
        map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING });
    }
}

/** Handle dropdown change: draw selected line or restore all-lines view. */
async function handleLineSelection() {
    const selectedLine = lineSelect.value;

    clearCurrentLayers();

    try {
        if (!selectedLine) {
            await drawAllLines(cachedLineNames);
            map.setView(BOSTON_CENTER, DEFAULT_ZOOM);
            return;
        }

        await drawSelectedLine(selectedLine);
    } catch (error) {
        console.error(`Error handling line selection "${selectedLine}":`, error);
    }
}

/** Populate dropdown and draw all lines on page load. */
async function initialize() {
    try {
        cachedLineNames = await fetchLineNames();

        cachedLineNames.forEach((name) => {
            const option = document.createElement("option");
            option.value = name;
            option.textContent = name;
            lineSelect.appendChild(option);
        });

        await drawAllLines(cachedLineNames);
    } catch (error) {
        console.error("Error initializing Trains & Alerts page:", error);
    }
}

lineSelect.addEventListener("change", handleLineSelection);
initialize();
