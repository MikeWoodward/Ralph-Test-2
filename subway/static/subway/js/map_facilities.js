"use strict";

/**
 * Map & Facilities page — Leaflet map showing all subway lines with
 * a color legend. Clicking or hovering a station marker opens a popup
 * with station name, lines served (as colored badges), and facilities.
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
const POPUP_CLOSE_DELAY_MS = 400;

const POPUP_MAX_WIDTH = 320;
const POPUP_MAX_HEIGHT = 280;
const AUTOPAN_PADDING = [50, 50];

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

let popupCloseTimeout = null;

/** Map of line name to hex color, populated during initialization. */
const lineColorMap = new Map();

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
 * Look up the hex color for a line name from cached line data.
 *
 * @param {string} lineName - Display name (e.g. "Red Line").
 * @returns {string} Hex color without '#', or gray fallback.
 */
function getLineColor(lineName) {
    return lineColorMap.get(lineName) ?? "888888";
}

// ---------------------------------------------------------------------------
// Station detail helpers
// ---------------------------------------------------------------------------

/**
 * Fetch station detail from the API.
 *
 * @param {string} stationId - MBTA station ID (e.g. "place-knncl").
 * @returns {Promise<Object|null>} Station data object, or null on error.
 */
async function fetchStationDetail(stationId) {
    try {
        const encoded = encodeURIComponent(stationId);
        const response = await fetch(`/api/station/${encoded}/`);
        if (!response.ok) {
            console.error(
                `Failed to fetch station "${stationId}": ${response.status}`,
            );
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(
            `Error fetching station "${stationId}":`,
            error,
        );
        return null;
    }
}

/**
 * Build popup HTML showing station name, lines served, and facilities.
 *
 * @param {Object} stationData - Station detail from the API.
 * @returns {string} HTML string for the Leaflet popup.
 */
function buildStationPopupHTML(stationData) {
    let html = `<div class="popup-title">${escapeHtml(stationData.name)}</div>`;

    const linesServed = stationData.lines_served ?? [];
    if (linesServed.length > 0) {
        html += '<div class="popup-section">';
        html += '<div class="popup-section-label">Lines Served</div>';
        html += '<div class="popup-lines">';
        linesServed.forEach((lineName) => {
            const color = getLineColor(lineName);
            html +=
                `<span class="popup-line-badge" style="background:#${color};">` +
                `${escapeHtml(lineName)}</span>`;
        });
        html += "</div></div>";
    }

    const facilities = stationData.facilities ?? [];
    if (facilities.length > 0) {
        html += '<div class="popup-section">';
        html += '<div class="popup-section-label">Facilities</div>';
        html += '<ul class="popup-facilities">';
        facilities.forEach((facility) => {
            html += `<li>${escapeHtml(facility)}</li>`;
        });
        html += "</ul></div>";
    } else {
        html += '<div class="popup-section">';
        html += '<p class="text-muted">No facilities listed</p>';
        html += "</div>";
    }

    return html;
}

/**
 * Attach click and mouseover handlers to station markers for
 * showing station detail popups.
 *
 * @param {L.LayerGroup} stationsLayer - Layer group of CircleMarkers.
 */
function attachStationHandlers(stationsLayer) {
    stationsLayer.eachLayer((marker) => {
        const openStationPopup = async () => {
            const { stationId, stationName } = marker.options;

            if (popupCloseTimeout) {
                clearTimeout(popupCloseTimeout);
                popupCloseTimeout = null;
            }

            const loadingHtml =
                `<div class="popup-title">${escapeHtml(stationName)}</div>` +
                '<div class="loading-text">' +
                '<span class="loading-spinner"></span>' +
                "Loading station info\u2026</div>";

            marker
                .bindPopup(loadingHtml, {
                    maxWidth: POPUP_MAX_WIDTH,
                    maxHeight: POPUP_MAX_HEIGHT,
                    autoPan: true,
                    autoPanPadding: AUTOPAN_PADDING,
                    keepInView: true,
                })
                .openPopup();

            const stationData = await fetchStationDetail(stationId);
            if (stationData) {
                marker.setPopupContent(buildStationPopupHTML(stationData));
            } else {
                marker.setPopupContent(
                    `<div class="popup-title">${escapeHtml(stationName)}</div>` +
                    '<p class="text-muted">Unable to load station details</p>',
                );
            }
        };

        marker.on("click", openStationPopup);

        marker.on("mouseover", () => {
            if (popupCloseTimeout) {
                clearTimeout(popupCloseTimeout);
                popupCloseTimeout = null;
            }
            if (!marker.isPopupOpen()) {
                openStationPopup();
            }
        });

        marker.on("mouseout", () => {
            popupCloseTimeout = setTimeout(
                () => map.closePopup(),
                POPUP_CLOSE_DELAY_MS,
            );
        });
    });
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Initialization
// ---------------------------------------------------------------------------

/**
 * Fetch all subway lines, draw them on the map, zoom to fit the
 * entire system, populate the color legend, and wire up station
 * popup handlers.
 */
async function initializeMap() {
    try {
        const lineNames = await fetchLineNames();
        const lineDataResults = await Promise.all(
            lineNames.map((name) => fetchLineData(name)),
        );

        const allStations = [];
        const legendEntries = [];
        const stationLayers = [];

        lineDataResults
            .filter((data) => data !== null)
            .forEach((lineData) => {
                const { stationsLayer } = drawLine(map, lineData);
                allStations.push(...lineData.stations);
                legendEntries.push({
                    name: lineData.line_name,
                    color: lineData.line_color,
                });
                lineColorMap.set(lineData.line_name, lineData.line_color);
                stationLayers.push(stationsLayer);
            });

        const bounds = getStationBounds(allStations);
        if (bounds) {
            map.fitBounds(bounds, { padding: FIT_BOUNDS_PADDING });
        }

        populateLegend(legendEntries);
        stationLayers.forEach((layer) => attachStationHandlers(layer));
    } catch (error) {
        console.error("Error initializing Map & Facilities page:", error);
    }
}

initializeMap();
