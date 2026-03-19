"use strict";

/**
 * Trains & Alerts page — Leaflet map initialization, line selection,
 * alert display, and station prediction popups.
 *
 * On load, populates the line dropdown and draws all subway lines.
 * Selecting a line clears the map and redraws only that line, zoomed
 * to fit its stations. Alerts for the selected line are fetched and
 * rendered in the alerts area.
 *
 * Clicking a station marker opens a popup with the next train
 * predictions, grouped by route (up to 4 per route).
 *
 * Depends on: map_utils.js (loaded before this script).
 */

const BOSTON_CENTER = [42.3601, -71.0589];
const DEFAULT_ZOOM = 12;
const FIT_BOUNDS_PADDING = [30, 30];
const MAX_PREDICTIONS_PER_ROUTE = 4;
const POPUP_CLOSE_DELAY_MS = 400;

const POPUP_MAX_WIDTH = 320;
const POPUP_MAX_HEIGHT = 280;
const AUTOPAN_PADDING = [50, 50];

const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
    'Data: <a href="https://www.mbta.com/developers/v3-api">MBTA V3 API</a>' +
    ' | Map: &copy; <a href="https://www.openstreetmap.org/copyright">' +
    "OpenStreetMap</a> contributors";

const ROUTE_COLORS = {
    Red: "DA291C",
    Orange: "ED8B00",
    "Green-B": "00843D",
    "Green-C": "00843D",
    "Green-D": "00843D",
    "Green-E": "00843D",
    Blue: "003DA5",
    Mattapan: "DA291C",
};

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
let popupCloseTimeout = null;

/** Cached line names to avoid re-fetching when resetting to all-lines view. */
let cachedLineNames = [];

const lineSelect = document.getElementById("line-select");
const alertsArea = document.getElementById("alerts-area");

// ---------------------------------------------------------------------------
// Popup dismiss-on-mouseout: hovering the popup cancels the close timer
// ---------------------------------------------------------------------------

map.on("popupopen", (e) => {
    const popupEl = e.popup.getElement();
    if (!popupEl) return;
    popupEl.addEventListener("mouseenter", () => {
        if (popupCloseTimeout) {
            clearTimeout(popupCloseTimeout);
            popupCloseTimeout = null;
        }
    });
    popupEl.addEventListener("mouseleave", () => {
        popupCloseTimeout = setTimeout(
            () => map.closePopup(),
            POPUP_CLOSE_DELAY_MS,
        );
    });
});

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

/**
 * Escape HTML special characters to prevent XSS in popup content.
 *
 * @param {string} text - Raw text to escape.
 * @returns {string} HTML-safe string.
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Look up the hex color for an MBTA route ID.
 *
 * @param {string} route - MBTA route ID (e.g. "Red", "Green-B").
 * @returns {string} Hex color without '#'.
 */
function getRouteColor(route) {
    if (ROUTE_COLORS[route]) return ROUTE_COLORS[route];
    if (route.startsWith("Green")) return "00843D";
    return "888888";
}

// ---------------------------------------------------------------------------
// Prediction helpers
// ---------------------------------------------------------------------------

/**
 * Fetch predictions for a station from the API.
 *
 * @param {string} stationId - MBTA station ID (e.g. "place-knncl").
 * @returns {Promise<Array<Object>>} Prediction objects, or empty array on error.
 */
async function fetchPredictions(stationId) {
    try {
        const encoded = encodeURIComponent(stationId);
        const response = await fetch(
            `/api/station/${encoded}/predictions/`,
        );
        if (!response.ok) {
            console.error(
                `Failed to fetch predictions for "${stationId}": ${response.status}`,
            );
            return [];
        }
        const data = await response.json();
        return data.predictions ?? [];
    } catch (error) {
        console.error(
            `Error fetching predictions for "${stationId}":`,
            error,
        );
        return [];
    }
}

/**
 * Format a prediction into a human-readable time string.
 *
 * Uses arrival_time (falling back to departure_time). Shows relative
 * minutes if under an hour, absolute time beyond that, or the
 * prediction's comments field when no time is available.
 *
 * @param {Object} prediction - Object with arrival_time, departure_time, comments.
 * @returns {string} Formatted time string.
 */
function formatPredictionTime(prediction) {
    const time = prediction.arrival_time ?? prediction.departure_time;
    if (!time) return prediction.comments ?? "\u2014";

    const date = new Date(time);
    const diffMin = Math.round((date - new Date()) / 60_000);

    if (diffMin < 1) return prediction.comments ?? "Now";
    if (diffMin < 60) return `${diffMin} min`;

    return date.toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
    });
}

/**
 * Build popup HTML showing predictions grouped by route.
 *
 * @param {string} stationName - Display name of the station.
 * @param {Array<Object>} predictions - Flat array of prediction objects.
 * @returns {string} HTML string for the Leaflet popup.
 */
function buildPredictionPopupHTML(stationName, predictions) {
    let html = `<div class="popup-title">${escapeHtml(stationName)}</div>`;

    if (predictions.length === 0) {
        html +=
            '<p class="popup-no-predictions">No subway predictions</p>';
        return html;
    }

    const grouped = new Map();
    predictions.forEach((pred) => {
        const group = grouped.get(pred.route) ?? [];
        if (group.length < MAX_PREDICTIONS_PER_ROUTE) {
            group.push(pred);
        }
        grouped.set(pred.route, group);
    });

    html += '<div class="popup-predictions">';

    grouped.forEach((preds, route) => {
        const color = getRouteColor(route);
        html += '<div class="popup-route-group">';
        html +=
            `<span class="popup-route-name" style="background:#${color};">` +
            `${escapeHtml(route)}</span>`;
        html += '<ul class="prediction-list">';

        preds.forEach((pred) => {
            const timeStr = formatPredictionTime(pred);
            html +=
                '<li class="prediction-item">' +
                `<span class="prediction-dest">${escapeHtml(pred.destination)}</span>` +
                `<span class="prediction-time">${escapeHtml(timeStr)}</span>` +
                "</li>";
        });

        html += "</ul></div>";
    });

    html += "</div>";
    return html;
}

// ---------------------------------------------------------------------------
// Layer management
// ---------------------------------------------------------------------------

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
 * Attach click and mouseout handlers to every station marker so
 * clicking opens a prediction popup that auto-closes on mouseout.
 *
 * @param {L.LayerGroup} stationsLayer - Layer group of CircleMarkers.
 */
function attachPredictionHandlers(stationsLayer) {
    stationsLayer.eachLayer((marker) => {
        marker.on("click", async () => {
            const { stationId, stationName } = marker.options;

            const loadingHtml =
                `<div class="popup-title">${escapeHtml(stationName)}</div>` +
                '<div class="loading-text">' +
                '<span class="loading-spinner"></span>' +
                "Loading predictions\u2026</div>";

            marker
                .bindPopup(loadingHtml, {
                    maxWidth: POPUP_MAX_WIDTH,
                    maxHeight: POPUP_MAX_HEIGHT,
                    autoPan: true,
                    autoPanPadding: AUTOPAN_PADDING,
                    keepInView: true,
                })
                .openPopup();

            const predictions = await fetchPredictions(stationId);
            const html = buildPredictionPopupHTML(
                stationName,
                predictions,
            );
            marker.setPopupContent(html);
        });

        marker.on("mouseout", () => {
            popupCloseTimeout = setTimeout(
                () => map.closePopup(),
                POPUP_CLOSE_DELAY_MS,
            );
        });

        marker.on("mouseover", () => {
            if (popupCloseTimeout) {
                clearTimeout(popupCloseTimeout);
                popupCloseTimeout = null;
            }
        });
    });
}

// ---------------------------------------------------------------------------
// Alert helpers
// ---------------------------------------------------------------------------

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
        console.error(
            `Error fetching alerts for "${lineName}":`,
            error,
        );
        return [];
    }
}

/**
 * Map an MBTA severity number to a CSS class suffix.
 *
 * @param {number} severity - MBTA severity level (1-10).
 * @returns {string} One of "high", "medium", or "low".
 */
function getSeverityLevel(severity) {
    if (severity >= 7) return "high";
    if (severity >= 4) return "medium";
    return "low";
}

/**
 * Render alert items into the alerts area.
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

// ---------------------------------------------------------------------------
// Line drawing
// ---------------------------------------------------------------------------

/**
 * Fetch data for all lines and draw them on the map, then
 * zoom to fit every station within the viewport.
 *
 * @param {Array<string>} lineNames - Line names to fetch and draw.
 */
async function drawAllLines(lineNames) {
    const lineDataResults = await Promise.all(
        lineNames.map((name) => fetchLineData(name)),
    );

    const allShapesGroup = L.layerGroup();
    const allStationsGroup = L.layerGroup();
    const allStations = [];

    lineDataResults
        .filter((data) => data !== null)
        .forEach((lineData) => {
            const { shapesLayer, stationsLayer } = drawLine(map, lineData);

            shapesLayer.eachLayer((layer) =>
                allShapesGroup.addLayer(layer),
            );
            stationsLayer.eachLayer((layer) =>
                allStationsGroup.addLayer(layer),
            );

            allStations.push(...lineData.stations);

            shapesLayer.remove();
            stationsLayer.remove();
        });

    allShapesGroup.addTo(map);
    allStationsGroup.addTo(map);

    currentShapesLayer = allShapesGroup;
    currentStationsLayer = allStationsGroup;

    const bounds = getStationBounds(allStations);
    if (bounds) {
        map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING });
    }

    attachPredictionHandlers(currentStationsLayer);
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

    attachPredictionHandlers(currentStationsLayer);
}

// ---------------------------------------------------------------------------
// Event handling
// ---------------------------------------------------------------------------

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
            return;
        }

        const [, alerts] = await Promise.all([
            drawSelectedLine(selectedLine),
            fetchLineAlerts(selectedLine),
        ]);
        renderAlerts(alerts, selectedLine);
    } catch (error) {
        console.error(
            `Error handling line selection "${selectedLine}":`,
            error,
        );
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
