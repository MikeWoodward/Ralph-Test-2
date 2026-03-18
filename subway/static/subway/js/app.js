/* MBTA Subway App - Main JavaScript */
"use strict";

const MBTA_APP = {
    trainsMap: null,
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

document.addEventListener("DOMContentLoaded", () => {
    initTrainsMap();
});
