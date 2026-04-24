"use strict";

const LINE_NAMES_ENDPOINT = "/api/lines";
const LINE_DETAIL_ENDPOINT_BASE = "/api/lines/";
const TILE_LAYER_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_LAYER_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">' +
    "OpenStreetMap</a> contributors";
const SUBWAY_SYSTEM_BOUNDS = [
    [42.2279, -71.1912],
    [42.4368, -70.9860],
];
const MAP_PADDING = [24, 24];
const DEFAULT_LINE_COLOR = "#1f2937";
const LINE_WEIGHT = 4;
const STATION_MARKER_RADIUS = 6;
const STATION_MARKER_WEIGHT = 2;

let mapFacilitiesMap = null;
let networkLayerGroup = null;

const reportMapFacilitiesError = ({ message, error }) => {
    const stackFrame =
        typeof error?.stack === "string"
            ? (error.stack.split("\n")[1] ?? "unknown").trim()
            : "unknown";

    console.error(message, stackFrame, error);
};

const getLineDetailEndpoint = ({ lineName }) =>
    `${LINE_DETAIL_ENDPOINT_BASE}${encodeURIComponent(lineName)}`;

const getLineColor = ({ color }) =>
    typeof color === "string" && color.trim().length > 0
        ? `#${color.trim()}`
        : DEFAULT_LINE_COLOR;

const fetchLineNames = async () => {
    const response = await fetch(LINE_NAMES_ENDPOINT, {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(`Unable to load subway lines (${response.status}).`);
    }

    const lineNames = await response.json();

    if (!Array.isArray(lineNames)) {
        throw new TypeError(
            "Expected the line names endpoint to return an array.",
        );
    }

    return lineNames.filter(
        (lineName) =>
            typeof lineName === "string" && lineName.trim().length > 0,
    );
};

const fetchLineDetail = async ({ lineName }) => {
    const response = await fetch(getLineDetailEndpoint({ lineName }), {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(
            `Unable to load subway line details (${response.status}).`,
        );
    }

    return response.json();
};

const buildShapeLayers = ({ lineData, lineColor }) =>
    (Array.isArray(lineData?.shapes) ? lineData.shapes : [])
        .filter(
            (shapeCoordinates) =>
                Array.isArray(shapeCoordinates) && shapeCoordinates.length > 0,
        )
        .map((shapeCoordinates) =>
            window.L.polyline(shapeCoordinates, {
                color: lineColor,
                weight: LINE_WEIGHT,
                opacity: 0.9,
                lineJoin: "round",
                lineCap: "round",
            }),
        );

const getStationKey = ({ station }) => {
    const stationId =
        typeof station?.station_id === "string" ? station.station_id.trim() : "";

    if (stationId) {
        return stationId;
    }

    return `${station?.latitude}:${station?.longitude}`;
};

const collectUniqueStations = ({ lineDetails }) =>
    lineDetails.reduce((stationEntries, lineData) => {
        const lineColor = getLineColor({ color: lineData?.color });

        (Array.isArray(lineData?.stations) ? lineData.stations : [])
            .filter(
                (station) =>
                    Number.isFinite(station?.latitude) &&
                    Number.isFinite(station?.longitude),
            )
            .forEach((station) => {
                const stationKey = getStationKey({ station });

                if (!stationEntries.has(stationKey)) {
                    stationEntries.set(stationKey, {
                        lineColor,
                        station,
                    });
                }
            });

        return stationEntries;
    }, new Map());

const buildStationLayers = ({ lineDetails }) =>
    Array.from(collectUniqueStations({ lineDetails }).values()).map(
        ({ lineColor, station }) =>
            window.L.circleMarker(
                [station.latitude, station.longitude],
                {
                    radius: STATION_MARKER_RADIUS,
                    color: lineColor,
                    weight: STATION_MARKER_WEIGHT,
                    fillColor: "#ffffff",
                    fillOpacity: 1,
                },
            ),
    );

const removeNetworkLayerGroup = () => {
    if (networkLayerGroup) {
        networkLayerGroup.remove();
        networkLayerGroup = null;
    }
};

const buildLegendEntries = ({ lineDetails }) =>
    lineDetails.reduce((legendEntries, lineData) => {
        const lineName =
            typeof lineData?.name === "string" ? lineData.name.trim() : "";

        if (!lineName || legendEntries.some((entry) => entry.name === lineName)) {
            return legendEntries;
        }

        legendEntries.push({
            color: getLineColor({ color: lineData?.color }),
            name: lineName,
        });

        return legendEntries;
    }, []);

const renderLegend = ({ lineDetails }) => {
    const legendItemsElement = document.querySelector(
        "#map-facilities-legend-items",
    );

    if (!(legendItemsElement instanceof HTMLUListElement)) {
        return;
    }

    legendItemsElement.replaceChildren();

    buildLegendEntries({ lineDetails }).forEach((legendEntry) => {
        const legendItem = document.createElement("li");
        legendItem.className = "map-facilities-page__legend-item";

        const legendSwatch = document.createElement("span");
        legendSwatch.className = "map-facilities-page__legend-swatch";
        legendSwatch.style.backgroundColor = legendEntry.color;
        legendSwatch.setAttribute("aria-hidden", "true");

        const legendLabel = document.createElement("span");
        legendLabel.className = "map-facilities-page__legend-label";
        legendLabel.textContent = legendEntry.name;

        legendItem.append(legendSwatch, legendLabel);
        legendItemsElement.append(legendItem);
    });
};

const renderFullNetwork = ({ lineDetails }) => {
    if (!mapFacilitiesMap || typeof window.L === "undefined") {
        return;
    }

    const renderedLayers = lineDetails.flatMap((lineData) => {
        const lineColor = getLineColor({ color: lineData?.color });
        return buildShapeLayers({ lineData, lineColor });
    });

    renderedLayers.push(...buildStationLayers({ lineDetails }));

    removeNetworkLayerGroup();
    networkLayerGroup = window.L.featureGroup(renderedLayers).addTo(
        mapFacilitiesMap,
    );

    if (networkLayerGroup.getBounds().isValid()) {
        mapFacilitiesMap.fitBounds(networkLayerGroup.getBounds(), {
            padding: MAP_PADDING,
        });
        return;
    }

    mapFacilitiesMap.fitBounds(SUBWAY_SYSTEM_BOUNDS, {
        padding: MAP_PADDING,
    });
};

const initializeMap = ({ mapElement }) => {
    if (mapFacilitiesMap || typeof window.L === "undefined") {
        return;
    }

    mapFacilitiesMap = window.L.map(mapElement, {
        zoomControl: true,
    });

    window.L.tileLayer(TILE_LAYER_URL, {
        attribution: TILE_LAYER_ATTRIBUTION,
        maxZoom: 19,
    }).addTo(mapFacilitiesMap);

    window.requestAnimationFrame(() => {
        mapFacilitiesMap.invalidateSize();
        mapFacilitiesMap.fitBounds(SUBWAY_SYSTEM_BOUNDS, {
            padding: MAP_PADDING,
        });
    });
};

const loadAndRenderFullNetwork = async () => {
    const lineNames = await fetchLineNames();

    if (lineNames.length === 0) {
        if (mapFacilitiesMap) {
            mapFacilitiesMap.fitBounds(SUBWAY_SYSTEM_BOUNDS, {
                padding: MAP_PADDING,
            });
        }

        return;
    }

    const lineDetails = await Promise.all(
        lineNames.map((lineName) => fetchLineDetail({ lineName })),
    );

    const validLineDetails = lineDetails.filter(
        (lineData) => typeof lineData === "object" && lineData !== null,
    );

    renderLegend({ lineDetails: validLineDetails });
    renderFullNetwork({ lineDetails: validLineDetails });
};

document.addEventListener("DOMContentLoaded", () => {
    const mapElement = document.querySelector("#map-facilities-map");

    if (!(mapElement instanceof HTMLDivElement)) {
        return;
    }

    try {
        initializeMap({ mapElement });
    } catch (error) {
        reportMapFacilitiesError({
            message: "Unable to initialize the map and facilities view.",
            error,
        });
    }

    void loadAndRenderFullNetwork().catch((error) => {
        reportMapFacilitiesError({
            message: "Unable to load the full subway network.",
            error,
        });
    });
});
