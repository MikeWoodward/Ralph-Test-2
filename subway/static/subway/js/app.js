"use strict";

/**
 * Trains & Alerts page — Leaflet map initialization, line selection,
 * and alert display.
 *
 * On load, populates the line dropdown and draws all subway lines.
 * Selecting a line clears the map and redraws only that line, zoomed
 * to fit its stations. Alerts for the selected line are fetched and
 * rendered in the alerts area; "No current alerts" is shown when the
 * line has none.
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
const alertsArea = document.getElementById("alerts-area");

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
 * Fetch alerts for a given line from the API.
 *
 * @param {string} lineName - Display name of the line (e.g. "Red Line").
 * @returns {Promise<Array<Object>>} Array of alert objects, or empty on error.
 */
async function fetchLineAlerts(lineName) {
    try {
        const encoded = encodeURIComponent(lineName);
        const response = await fetch(`/api/line/${encoded}/alerts/`);
        if (!response.ok) {
            console.error(
                `Failed to fetch alerts for "${lineName}": ${response.status}`,
            );
            return [];
        }
        const data = await response.json();
        return data.alerts ?? [];
    } catch (error) {
        console.error(`Error fetching alerts for "${lineName}":`, error);
        return [];
    }
}

/**
 * Map an MBTA severity number to a CSS class suffix.
 * Higher severity values are more severe in the MBTA API.
 *
 * @param {number} severity - MBTA severity level (1–10).
 * @returns {string} One of "high", "medium", or "low".
 */
function getSeverityLevel(severity) {
    if (severity >= 7) return "high";
    if (severity >= 4) return "medium";
    return "low";
}

/**
 * Render alert items into the alerts area.
 * Shows "No current alerts" when the array is empty.
 *
 * @param {Array<Object>} alerts - Array of {headline, severity} objects.
 * @param {string} lineName - Display name of the selected line.
 */
function renderAlerts(alerts, lineName) {
    alertsArea.innerHTML = "";

    if (alerts.length === 0) {
        const noAlerts = document.createElement("p");
        noAlerts.className = "alerts-none";
        noAlerts.textContent = `No current alerts for ${lineName}.`;
        alertsArea.appendChild(noAlerts);
        return;
    }

    alerts.forEach((alert) => {
        const item = document.createElement("div");
        item.className = "alert-item";

        const badge = document.createElement("span");
        const level = getSeverityLevel(alert.severity);
        badge.className = `alert-severity alert-severity--${level}`;
        badge.textContent = level.toUpperCase();

        const headline = document.createElement("span");
        headline.className = "alert-headline";
        headline.textContent = alert.headline;

        item.appendChild(badge);
        item.appendChild(headline);
        alertsArea.appendChild(item);
    });
}

/** Reset the alerts area to the default placeholder state. */
function clearAlerts() {
    alertsArea.innerHTML =
        '<p class="alerts-placeholder">Select a line to see alerts.</p>';
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

/**
 * Handle dropdown change: draw selected line with alerts, or restore
 * the all-lines view with the placeholder alerts message.
 */
async function handleLineSelection() {
    const selectedLine = lineSelect.value;

    clearCurrentLayers();

    try {
        if (!selectedLine) {
            clearAlerts();
            await drawAllLines(cachedLineNames);
            map.setView(BOSTON_CENTER, DEFAULT_ZOOM);
            return;
        }

        const [, alerts] = await Promise.all([
            drawSelectedLine(selectedLine),
            fetchLineAlerts(selectedLine),
        ]);
        renderAlerts(alerts, selectedLine);
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
