/* MBTA Subway App - Main JavaScript */
"use strict";

const MBTA_APP = {
    trainsMap: null,
    facilitiesMap: null,
    lineLayerGroup: null,
    popupCloseTimer: null,
};

const BOSTON_CENTER = [42.36, -71.06];

/** Cancel any pending popup auto-close timer. */
function clearPopupCloseTimer() {
    if (MBTA_APP.popupCloseTimer) {
        clearTimeout(MBTA_APP.popupCloseTimer);
        MBTA_APP.popupCloseTimer = null;
    }
}

/**
 * Schedule the map popup to close after a delay. Any existing pending
 * close is cancelled first so multiple calls don't stack.
 *
 * @param {L.Map} map - The Leaflet map whose popup should close.
 * @param {number} [delay=350] - Milliseconds before closing.
 */
function schedulePopupClose(map, delay = 350) {
    clearPopupCloseTimer();
    MBTA_APP.popupCloseTimer = setTimeout(() => {
        map.closePopup();
        MBTA_APP.popupCloseTimer = null;
    }, delay);
}

/**
 * Format an ISO-8601 arrival time as a human-friendly relative string.
 * Returns "Arriving" for trains due within the current minute, or
 * "N min" for future arrivals.
 *
 * @param {string|null} isoString - ISO-8601 datetime, or null.
 * @returns {string} Formatted time string.
 */
function formatArrivalTime(isoString) {
    if (!isoString) return "—";
    const diffMin = Math.round((new Date(isoString) - new Date()) / 60000);
    if (diffMin <= 0) return "Arriving";
    if (diffMin === 1) return "1 min";
    return `${diffMin} min`;
}

/**
 * Fetch predictions for a station and display them in a Leaflet popup
 * bound to the given marker. Groups predictions by route and shows up
 * to 4 per route. Shows "No subway predictions" when the API returns
 * an empty array.
 *
 * @param {L.CircleMarker} marker - The station marker to bind the popup to.
 * @param {string} stationId - MBTA stop ID (e.g. "place-knncl").
 * @param {string} stationName - Human-readable station name.
 */
async function fetchAndShowPredictions(marker, stationId, stationName) {
    const map = MBTA_APP.trainsMap;
    if (!map) return;

    const loadingHtml =
        `<div class="prediction-popup">` +
        `<div class="prediction-station-name">${stationName}</div>` +
        `<p class="prediction-loading">Loading predictions\u2026</p>` +
        `</div>`;

    marker.unbindPopup();
    marker.bindPopup(loadingHtml, {
        autoPan: true,
        maxWidth: 320,
        minWidth: 220,
    });
    marker.openPopup();

    try {
        const response = await fetch(
            `/api/predictions/${encodeURIComponent(stationId)}`
        );
        if (!response.ok) {
            throw new Error(`Predictions API returned ${response.status}`);
        }
        const predictions = await response.json();

        if (!predictions.length) {
            marker.setPopupContent(
                `<div class="prediction-popup">` +
                `<div class="prediction-station-name">${stationName}</div>` +
                `<p class="prediction-none">No subway predictions</p>` +
                `</div>`
            );
            return;
        }

        const grouped = {};
        predictions.forEach((pred) => {
            if (!grouped[pred.route]) grouped[pred.route] = [];
            if (grouped[pred.route].length < 4) {
                grouped[pred.route].push(pred);
            }
        });

        let html =
            `<div class="prediction-popup">` +
            `<div class="prediction-station-name">${stationName}</div>`;

        Object.entries(grouped).forEach(([route, preds]) => {
            html +=
                `<div class="prediction-route-group">` +
                `<div class="prediction-route-name">${route}</div>` +
                `<table class="prediction-table">` +
                `<thead><tr><th>Destination</th><th>Arrives</th></tr></thead>` +
                `<tbody>`;

            preds.forEach((pred) => {
                const arrival = formatArrivalTime(pred.arrival_time);
                html +=
                    `<tr>` +
                    `<td>${pred.destination}</td>` +
                    `<td class="prediction-time">${arrival}</td>` +
                    `</tr>`;
            });

            html += `</tbody></table></div>`;
        });

        html += `</div>`;
        marker.setPopupContent(html);
    } catch (error) {
        console.error("Failed to fetch predictions:", error);
        marker.setPopupContent(
            `<div class="prediction-popup">` +
            `<div class="prediction-station-name">${stationName}</div>` +
            `<p class="prediction-error">Unable to load predictions.</p>` +
            `</div>`
        );
    }
}

/**
 * Initialise the Leaflet map on the Trains & Alerts page.
 *
 * Fetches every subway line from the API and computes a bounding box
 * from all station coordinates so the initial zoom fits the entire
 * subway system.
 */
async function initTrainsMap() {
    const mapEl = document.getElementById("trains-map");
    if (!mapEl) return;

    const map = L.map("trains-map", {
        center: BOSTON_CENTER,
        zoom: 13,
        zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
    }).addTo(map);

    try {
        const response = await fetch("/api/lines");
        if (!response.ok) throw new Error(`/api/lines returned ${response.status}`);
        const lineNames = await response.json();

        const allCoords = [];

        await Promise.all(
            lineNames.map(async (name) => {
                const lineResp = await fetch(
                    `/api/line/${encodeURIComponent(name)}`
                );
                if (!lineResp.ok) return;
                const lineData = await lineResp.json();

                lineData.stations?.forEach((station) => {
                    if (station.latitude && station.longitude) {
                        allCoords.push([station.latitude, station.longitude]);
                    }
                });
            })
        );

        if (allCoords.length > 0) {
            map.fitBounds(L.latLngBounds(allCoords), { padding: [20, 20] });
        }
    } catch (error) {
        console.error("Failed to calculate subway system bounds:", error);
    }

    MBTA_APP.trainsMap = map;

    map.on("popupopen", (e) => {
        const popupEl = e.popup.getElement();
        if (!popupEl) return;
        popupEl.addEventListener("mouseenter", clearPopupCloseTimer);
        popupEl.addEventListener("mouseleave", () => {
            schedulePopupClose(map, 200);
        });
    });
}

/**
 * Populate the line-select dropdown with subway line names fetched
 * from /api/lines.  Attaches a change listener that dispatches a
 * custom "lineSelected" event on the document for other modules to
 * react to.
 */
async function initLineSelector() {
    const select = document.getElementById("line-select");
    if (!select) return;

    try {
        const response = await fetch("/api/lines");
        if (!response.ok) {
            throw new Error(`/api/lines returned ${response.status}`);
        }
        const lineNames = await response.json();

        lineNames.forEach((name) => {
            const option = document.createElement("option");
            option.value = name;
            option.textContent = name;
            select.appendChild(option);
        });

        select.addEventListener("change", () => {
            document.dispatchEvent(
                new CustomEvent("lineSelected", {
                    detail: { lineName: select.value },
                })
            );
        });
    } catch (error) {
        console.error("Failed to populate line selector:", error);
    }
}

/**
 * Fetch and render a subway line on the Trains & Alerts map.
 *
 * Draws each shape segment as a thick colored polyline and each
 * station as a circle marker with the line color stroke and white
 * fill, following the official MBTA subway-map visual style.
 * Clears previously drawn layers before rendering.
 *
 * @param {string} lineName - Display name of the line (e.g. "Red Line").
 */
async function renderLineOnMap(lineName) {
    const map = MBTA_APP.trainsMap;
    if (!map) return;

    if (MBTA_APP.lineLayerGroup) {
        MBTA_APP.lineLayerGroup.clearLayers();
        map.removeLayer(MBTA_APP.lineLayerGroup);
    }

    MBTA_APP.lineLayerGroup = L.layerGroup().addTo(map);

    try {
        const response = await fetch(
            `/api/line/${encodeURIComponent(lineName)}`
        );
        if (!response.ok) {
            throw new Error(`/api/line/${lineName} returned ${response.status}`);
        }
        const lineData = await response.json();
        const lineColor = `#${lineData.line_color}`;

        const allCoords = [];

        lineData.shapes.forEach((shapeCoords) => {
            if (shapeCoords.length < 2) return;

            const latLngs = shapeCoords.map(([lat, lng]) => [lat, lng]);
            allCoords.push(...latLngs);
            L.polyline(latLngs, {
                color: lineColor,
                weight: 5,
                opacity: 0.9,
                lineCap: "round",
                lineJoin: "round",
            }).addTo(MBTA_APP.lineLayerGroup);
        });

        lineData.stations.forEach((station) => {
            if (!station.latitude || !station.longitude) return;

            const stationMarker = L.circleMarker(
                [station.latitude, station.longitude],
                {
                    radius: 6,
                    color: lineColor,
                    weight: 2.5,
                    fillColor: "#ffffff",
                    fillOpacity: 1,
                    opacity: 1,
                }
            )
                .bindTooltip(station.name, {
                    direction: "top",
                    offset: [0, -8],
                })
                .on("click", () => {
                    fetchAndShowPredictions(
                        stationMarker,
                        station.station_id,
                        station.name
                    );
                })
                .on("mouseout", () => schedulePopupClose(map))
                .on("mouseover", clearPopupCloseTimer)
                .addTo(MBTA_APP.lineLayerGroup);
        });

        if (allCoords.length > 0) {
            map.fitBounds(L.latLngBounds(allCoords), { padding: [40, 40] });
        }
    } catch (error) {
        console.error("Failed to render line on map:", error);
    }
}

/**
 * Fetch and display alerts for a subway line in the alerts container.
 *
 * Renders each alert as a card with headline and severity badge.
 * Shows "No current alerts" when the API returns an empty array.
 *
 * @param {string} lineName - Display name of the line (e.g. "Red Line").
 */
async function renderAlerts(lineName) {
    const container = document.getElementById("alerts-container");
    if (!container) return;

    container.innerHTML = '<p class="alerts-loading">Loading alerts…</p>';

    try {
        const response = await fetch(
            `/api/alerts/${encodeURIComponent(lineName)}`
        );
        if (!response.ok) {
            throw new Error(
                `/api/alerts/${lineName} returned ${response.status}`
            );
        }
        const alerts = await response.json();

        if (!alerts.length) {
            container.innerHTML =
                `<div class="alerts-header">${lineName} — Alerts</div>` +
                '<p class="alerts-none">No current alerts for this line.</p>';
            return;
        }

        const severityLabel = (severity) => {
            if (severity >= 7) return "severe";
            if (severity >= 4) return "moderate";
            return "minor";
        };

        const alertCards = alerts
            .map(
                (alert) =>
                    `<div class="alert-card alert-${severityLabel(alert.severity)}">` +
                    `<span class="alert-severity">${severityLabel(alert.severity)}</span>` +
                    `<span class="alert-headline">${alert.headline}</span>` +
                    `</div>`
            )
            .join("");

        container.innerHTML =
            `<div class="alerts-header">${lineName} — Alerts</div>` +
            alertCards;
    } catch (error) {
        console.error("Failed to fetch alerts:", error);
        container.innerHTML =
            '<p class="alerts-error">Unable to load alerts.</p>';
    }
}

/**
 * Add a semi-transparent legend control to a Leaflet map showing
 * a colored swatch and name for each subway line.
 *
 * @param {L.Map} map - The Leaflet map to add the legend to.
 * @param {{ name: string, color: string }[]} items - Line name/color pairs.
 */
function addMapLegend(map, items) {
    const legend = L.control({ position: "bottomright" });

    legend.onAdd = () => {
        const div = L.DomUtil.create("div", "map-legend");
        div.innerHTML =
            '<div class="map-legend-title">Subway Lines</div>' +
            items
                .map(
                    ({ name, color }) =>
                        `<div class="map-legend-item">` +
                        `<span class="map-legend-swatch" style="background:${color}"></span>` +
                        `<span class="map-legend-label">${name}</span>` +
                        `</div>`
                )
                .join("");
        return div;
    };

    legend.addTo(map);
}

/**
 * Initialise the Leaflet map on the Map & Facilities page,
 * rendering every subway line simultaneously with correct colors
 * and station markers.  Fits the map bounds to the entire system.
 */
async function initFacilitiesMap() {
    const mapEl = document.getElementById("facilities-map");
    if (!mapEl) return;

    const map = L.map("facilities-map", {
        center: BOSTON_CENTER,
        zoom: 13,
        zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
    }).addTo(map);

    MBTA_APP.facilitiesMap = map;

    try {
        const response = await fetch("/api/lines");
        if (!response.ok) throw new Error(`/api/lines returned ${response.status}`);
        const lineNames = await response.json();

        const allCoords = [];

        const lineDataList = await Promise.all(
            lineNames.map(async (name) => {
                const lineResp = await fetch(
                    `/api/line/${encodeURIComponent(name)}`
                );
                if (!lineResp.ok) return null;
                return lineResp.json();
            })
        );

        lineDataList.forEach((lineData) => {
            if (!lineData) return;
            const lineColor = `#${lineData.line_color}`;

            lineData.shapes.forEach((shapeCoords) => {
                if (shapeCoords.length < 2) return;
                const latLngs = shapeCoords.map(([lat, lng]) => [lat, lng]);
                allCoords.push(...latLngs);
                L.polyline(latLngs, {
                    color: lineColor,
                    weight: 5,
                    opacity: 0.9,
                    lineCap: "round",
                    lineJoin: "round",
                }).addTo(map);
            });

            lineData.stations.forEach((station) => {
                if (!station.latitude || !station.longitude) return;
                allCoords.push([station.latitude, station.longitude]);

                L.circleMarker(
                    [station.latitude, station.longitude],
                    {
                        radius: 6,
                        color: lineColor,
                        weight: 2.5,
                        fillColor: "#ffffff",
                        fillOpacity: 1,
                        opacity: 1,
                    }
                )
                    .bindTooltip(station.name, {
                        direction: "top",
                        offset: [0, -8],
                    })
                    .addTo(map);
            });
        });

        if (allCoords.length > 0) {
            map.fitBounds(L.latLngBounds(allCoords), { padding: [20, 20] });
        }

        const legendItems = lineNames
            .map((name, i) => {
                const data = lineDataList[i];
                return data ? { name, color: `#${data.line_color}` } : null;
            })
            .filter(Boolean);

        if (legendItems.length > 0) {
            addMapLegend(map, legendItems);
        }
    } catch (error) {
        console.error("Failed to initialise facilities map:", error);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initTrainsMap();
    initLineSelector();
    initFacilitiesMap();

    document.addEventListener("lineSelected", (e) => {
        const { lineName } = e.detail;
        if (lineName) {
            renderLineOnMap(lineName);
            renderAlerts(lineName);
        }
    });
});
