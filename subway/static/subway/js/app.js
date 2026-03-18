/* MBTA Subway App - Main JavaScript */
"use strict";

const MBTA_APP = {
    trainsMap: null,
    lineLayerGroup: null,
};

const BOSTON_CENTER = [42.36, -71.06];

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

            L.circleMarker([station.latitude, station.longitude], {
                radius: 6,
                color: lineColor,
                weight: 2.5,
                fillColor: "#ffffff",
                fillOpacity: 1,
                opacity: 1,
            })
                .bindTooltip(station.name, {
                    direction: "top",
                    offset: [0, -8],
                })
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

document.addEventListener("DOMContentLoaded", () => {
    initTrainsMap();
    initLineSelector();

    document.addEventListener("lineSelected", (e) => {
        const { lineName } = e.detail;
        if (lineName) {
            renderLineOnMap(lineName);
            renderAlerts(lineName);
        }
    });
});
