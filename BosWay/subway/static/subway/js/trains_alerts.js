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

let trainsMap = null;
let selectedLineLayerGroup = null;

const buildLineOption = (lineName) => {
    const lineOption = document.createElement("option");
    lineOption.value = lineName;
    lineOption.textContent = lineName;
    return lineOption;
};

const clearLoadedLineOptions = ({ lineSelect }) => {
    const loadedOptions = Array.from(lineSelect.options).filter(
        (lineOption) => lineOption.value !== "",
    );

    loadedOptions.forEach((lineOption) => {
        lineOption.remove();
    });
};

const reportDropdownLoadError = (error) => {
    const stackFrame =
        typeof error?.stack === "string"
            ? (error.stack.split("\n")[1] ?? "unknown").trim()
            : "unknown";

    console.error("Unable to load subway line options.", stackFrame, error);
};

const reportMapLoadError = (error) => {
    const stackFrame =
        typeof error?.stack === "string"
            ? (error.stack.split("\n")[1] ?? "unknown").trim()
            : "unknown";

    console.error("Unable to initialize the subway map.", stackFrame, error);
};

const reportSelectedLineError = (error) => {
    const stackFrame =
        typeof error?.stack === "string"
            ? (error.stack.split("\n")[1] ?? "unknown").trim()
            : "unknown";

    console.error("Unable to render the selected subway line.", stackFrame, error);
};

const getLineDetailEndpoint = ({ lineName }) =>
    `${LINE_DETAIL_ENDPOINT_BASE}${encodeURIComponent(lineName)}`;

const getLineColor = ({ color }) =>
    typeof color === "string" && color.trim().length > 0
        ? `#${color.trim()}`
        : DEFAULT_LINE_COLOR;

const fetchLineDetail = async ({ lineName }) => {
    const response = await fetch(getLineDetailEndpoint({ lineName }), {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(
            `Unable to load the selected subway line (${response.status}).`,
        );
    }

    return response.json();
};

const removeSelectedLineLayer = () => {
    if (selectedLineLayerGroup) {
        selectedLineLayerGroup.remove();
        selectedLineLayerGroup = null;
    }
};

const buildShapeLayers = ({ lineData, lineColor }) =>
    (Array.isArray(lineData.shapes) ? lineData.shapes : [])
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

const buildStationLayers = ({ lineData, lineColor }) =>
    (Array.isArray(lineData.stations) ? lineData.stations : [])
        .filter(
            (station) =>
                Number.isFinite(station?.latitude) &&
                Number.isFinite(station?.longitude),
        )
        .map((station) =>
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

const renderSelectedLine = ({ lineData }) => {
    if (!trainsMap || typeof window.L === "undefined") {
        return;
    }

    const lineColor = getLineColor({ color: lineData?.color });
    const renderedLayers = [
        ...buildShapeLayers({ lineData, lineColor }),
        ...buildStationLayers({ lineData, lineColor }),
    ];

    removeSelectedLineLayer();
    selectedLineLayerGroup = window.L.featureGroup(renderedLayers).addTo(
        trainsMap,
    );

    if (selectedLineLayerGroup.getBounds().isValid()) {
        trainsMap.fitBounds(selectedLineLayerGroup.getBounds(), {
            padding: MAP_PADDING,
        });
    }
};

const handleLineSelection = async ({ lineSelect }) => {
    const selectedLineName = lineSelect.value.trim();

    if (!selectedLineName) {
        return;
    }

    const lineData = await fetchLineDetail({ lineName: selectedLineName });
    renderSelectedLine({ lineData });
};

const populateLineSelect = async ({ lineSelect }) => {
    if (lineSelect.dataset.lineOptionsLoaded === "true") {
        return;
    }

    const response = await fetch(LINE_NAMES_ENDPOINT, {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(
            `Unable to load subway lines (${response.status}).`,
        );
    }

    const lineNames = await response.json();

    if (!Array.isArray(lineNames)) {
        throw new TypeError(
            "Expected the line names endpoint to return an array.",
        );
    }

    clearLoadedLineOptions({ lineSelect });

    lineNames
        .filter(
            (lineName) =>
                typeof lineName === "string" && lineName.trim().length > 0,
        )
        .forEach((lineName) => {
            lineSelect.append(buildLineOption(lineName));
        });

    lineSelect.dataset.lineOptionsLoaded = "true";
};

const initializeMap = ({ mapElement }) => {
    if (trainsMap || typeof window.L === "undefined") {
        return;
    }

    trainsMap = window.L.map(mapElement, {
        zoomControl: true,
    });

    window.L.tileLayer(TILE_LAYER_URL, {
        attribution: TILE_LAYER_ATTRIBUTION,
        maxZoom: 19,
    }).addTo(trainsMap);

    window.requestAnimationFrame(() => {
        trainsMap.invalidateSize();
        trainsMap.fitBounds(SUBWAY_SYSTEM_BOUNDS, {
            padding: MAP_PADDING,
        });
    });
};

document.addEventListener("DOMContentLoaded", () => {
    const lineSelect = document.querySelector("#line-select");
    const mapElement = document.querySelector("#trains-map");

    if (!(lineSelect instanceof HTMLSelectElement)) {
        return;
    }

    if (!(mapElement instanceof HTMLDivElement)) {
        return;
    }

    try {
        initializeMap({ mapElement });
    } catch (error) {
        reportMapLoadError(error);
    }

    lineSelect.addEventListener("change", () => {
        void handleLineSelection({ lineSelect }).catch(reportSelectedLineError);
    });

    void populateLineSelect({ lineSelect }).catch(reportDropdownLoadError);
});
