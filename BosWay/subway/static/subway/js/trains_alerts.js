"use strict";

const LINE_NAMES_ENDPOINT = "/api/lines";
const TILE_LAYER_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_LAYER_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">' +
    "OpenStreetMap</a> contributors";
const SUBWAY_SYSTEM_BOUNDS = [
    [42.2279, -71.1912],
    [42.4368, -70.9860],
];
const MAP_PADDING = [24, 24];

let trainsMap = null;

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

    void populateLineSelect({ lineSelect }).catch(reportDropdownLoadError);
});
