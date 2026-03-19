"use strict";

/**
 * Map & Facilities page — Leaflet map showing all subway lines with
 * a color legend.
 *
 * On page load, fetches all line data from the API, draws every line
 * and its stations on the map, zooms to fit the entire subway system,
 * and populates the legend overlay with line colors and names.
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

/**
 * Build a single legend entry element.
 *
 * @param {string} lineName - Display name (e.g. "Red Line").
 * @param {string} hexColor - Hex color without '#' (e.g. "DA291C").
 * @returns {HTMLElement} The legend-item div element.
 */
function buildLegendItem(lineName, hexColor) {
    const item = document.createElement("div");
    item.className = "legend-item";

    const swatch = document.createElement("span");
    swatch.className = "legend-swatch";
    swatch.style.backgroundColor = `#${hexColor}`;

    const label = document.createElement("span");
    label.className = "legend-label";
    label.textContent = lineName;

    item.appendChild(swatch);
    item.appendChild(label);
    return item;
}

/**
 * Populate the legend overlay with color swatches and line names.
 *
 * @param {Array<{name: string, color: string}>} lineEntries
 */
function populateLegend(lineEntries) {
    const legendEl = document.getElementById("map-legend");
    if (!legendEl) return;

    lineEntries.forEach(({ name, color }) => {
        legendEl.appendChild(buildLegendItem(name, color));
    });
}

/**
 * Fetch all subway lines, draw them on the map, zoom to fit the
 * entire system, and populate the color legend.
 */
async function initializeMap() {
    try {
        const lineNames = await fetchLineNames();
        const lineDataResults = await Promise.all(
            lineNames.map((name) => fetchLineData(name)),
        );

        const allStations = [];
        const legendEntries = [];

        lineDataResults
            .filter((data) => data !== null)
            .forEach((lineData) => {
                drawLine(map, lineData);
                allStations.push(...lineData.stations);
                legendEntries.push({
                    name: lineData.line_name,
                    color: lineData.line_color,
                });
            });

        const bounds = getStationBounds(allStations);
        if (bounds) {
            map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING });
        }

        populateLegend(legendEntries);
    } catch (error) {
        console.error("Error initializing Map & Facilities page:", error);
    }
}

initializeMap();
