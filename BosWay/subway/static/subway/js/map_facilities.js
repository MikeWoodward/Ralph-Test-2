"use strict";

const LINE_NAMES_ENDPOINT = "/api/lines";
const LINE_DETAIL_ENDPOINT_BASE = "/api/lines/";
const STATION_ENDPOINT_BASE = "/api/stations/";
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
const POPUP_MAX_WIDTH = 320;
const POPUP_CLOSE_DELAY_MS = 180;
const POPUP_AUTO_PAN_PADDING = 24;

let mapFacilitiesMap = null;
let networkLayerGroup = null;
let lineColorByName = new Map();
let activePopupCloseTimeoutId = null;

const reportMapFacilitiesError = ({ message, error }) => {
    const stackFrame =
        typeof error?.stack === "string"
            ? (error.stack.split("\n")[1] ?? "unknown").trim()
            : "unknown";

    console.error(message, stackFrame, error);
};

const getLineDetailEndpoint = ({ lineName }) =>
    `${LINE_DETAIL_ENDPOINT_BASE}${encodeURIComponent(lineName)}`;

const getStationDetailEndpoint = ({ stationId }) =>
    `${STATION_ENDPOINT_BASE}${encodeURIComponent(stationId)}`;

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

const fetchStationDetail = async ({ stationId }) => {
    const response = await fetch(getStationDetailEndpoint({ stationId }), {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(
            `Unable to load station details (${response.status}).`,
        );
    }

    const stationDetail = await response.json();

    if (
        typeof stationDetail !== "object" ||
        stationDetail === null ||
        Array.isArray(stationDetail)
    ) {
        throw new TypeError(
            "Expected the station detail endpoint to return an object.",
        );
    }

    return stationDetail;
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
                    stationId: station.station_id,
                    stationName:
                        typeof station.name === "string" && station.name.trim()
                            ? station.name.trim()
                            : "Selected station",
                },
            ),
    );

const buildLineColorByName = ({ lineDetails }) =>
    lineDetails.reduce((lineColorMap, lineData) => {
        const lineName =
            typeof lineData?.name === "string" ? lineData.name.trim() : "";

        if (!lineName) {
            return lineColorMap;
        }

        lineColorMap.set(
            lineName,
            getLineColor({ color: lineData?.color }),
        );
        return lineColorMap;
    }, new Map());

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

const createStationPopupRoot = ({ stationName }) => {
    const popupRoot = document.createElement("section");
    popupRoot.className = "map-facilities-page__station-popup";

    const title = document.createElement("h3");
    title.className = "map-facilities-page__station-popup-title";
    title.textContent = stationName;
    popupRoot.append(title);

    return popupRoot;
};

const createStationPopupMessage = ({ className, text }) => {
    const message = document.createElement("p");
    message.className = className;
    message.textContent = text;
    return message;
};

const createStationPopupSection = ({ titleText }) => {
    const section = document.createElement("section");
    section.className = "map-facilities-page__station-popup-section";

    const title = document.createElement("h4");
    title.className = "map-facilities-page__station-popup-section-title";
    title.textContent = titleText;

    section.append(title);
    return section;
};

const createServedLinesSection = ({ linesServed }) => {
    const linesSection = createStationPopupSection({
        titleText: "Lines served",
    });

    if (linesServed.length === 0) {
        linesSection.append(
            createStationPopupMessage({
                className: "map-facilities-page__station-popup-status",
                text: "No subway lines listed for this station.",
            }),
        );
        return linesSection;
    }

    const linesList = document.createElement("div");
    linesList.className = "map-facilities-page__station-popup-lines";

    linesServed.forEach((lineName) => {
        const lineBadge = document.createElement("span");
        lineBadge.className = "map-facilities-page__station-popup-line-badge";
        lineBadge.style.backgroundColor =
            lineColorByName.get(lineName) ?? DEFAULT_LINE_COLOR;
        lineBadge.textContent = lineName;
        linesList.append(lineBadge);
    });

    linesSection.append(linesList);
    return linesSection;
};

const createFacilitiesSection = ({ facilities }) => {
    const facilitiesSection = createStationPopupSection({
        titleText: "Facilities",
    });

    if (facilities.length === 0) {
        facilitiesSection.append(
            createStationPopupMessage({
                className: "map-facilities-page__station-popup-status",
                text: "No facilities listed for this station.",
            }),
        );
        return facilitiesSection;
    }

    const facilitiesList = document.createElement("ul");
    facilitiesList.className = "map-facilities-page__station-popup-facilities";

    facilities.forEach((facilityLabel) => {
        const facilityItem = document.createElement("li");
        facilityItem.textContent = facilityLabel;
        facilitiesList.append(facilityItem);
    });

    facilitiesSection.append(facilitiesList);
    return facilitiesSection;
};

const buildStationPopupContent = ({ stationDetail, fallbackStationName }) => {
    const stationName =
        typeof stationDetail?.name === "string" && stationDetail.name.trim()
            ? stationDetail.name.trim()
            : fallbackStationName;
    const linesServed = Array.isArray(stationDetail?.lines_served)
        ? stationDetail.lines_served.filter(
              (lineName) =>
                  typeof lineName === "string" && lineName.trim().length > 0,
          )
        : [];
    const facilities = Array.isArray(stationDetail?.facilities)
        ? stationDetail.facilities.filter(
              (facilityLabel) =>
                  typeof facilityLabel === "string" &&
                  facilityLabel.trim().length > 0,
          )
        : [];
    const popupRoot = createStationPopupRoot({ stationName });

    popupRoot.append(
        createServedLinesSection({ linesServed }),
        createFacilitiesSection({ facilities }),
    );

    return popupRoot;
};

const cancelScheduledPopupClose = () => {
    if (activePopupCloseTimeoutId !== null) {
        window.clearTimeout(activePopupCloseTimeoutId);
        activePopupCloseTimeoutId = null;
    }
};

const schedulePopupClose = ({ marker }) => {
    cancelScheduledPopupClose();
    activePopupCloseTimeoutId = window.setTimeout(() => {
        marker.closePopup();
        activePopupCloseTimeoutId = null;
    }, POPUP_CLOSE_DELAY_MS);
};

const getStationPopupOptions = () => ({
    autoClose: true,
    closeButton: true,
    closeOnClick: true,
    closeOnEscapeKey: true,
    keepInView: true,
    autoPan: true,
    autoPanPadding: window.L.point(
        POPUP_AUTO_PAN_PADDING,
        POPUP_AUTO_PAN_PADDING,
    ),
    className: "map-facilities-page__station-leaflet-popup",
    maxHeight: Math.max(180, Math.floor(window.innerHeight * 0.45)),
    maxWidth: POPUP_MAX_WIDTH,
});

const attachPopupDismissHandlers = ({ marker }) => {
    marker.on("mouseover", cancelScheduledPopupClose);
    marker.on("mouseout", () => {
        if (marker.isPopupOpen()) {
            schedulePopupClose({ marker });
        }
    });
    marker.on("popupopen", ({ popup }) => {
        cancelScheduledPopupClose();
        const popupElement = popup.getElement();

        if (!(popupElement instanceof HTMLElement)) {
            return;
        }

        popupElement.addEventListener("mouseenter", cancelScheduledPopupClose);
        popupElement.addEventListener("mouseleave", () => {
            schedulePopupClose({ marker });
        });
    });
    marker.on("popupclose", cancelScheduledPopupClose);
};

const openStationDetailPopup = async ({ marker }) => {
    const stationId =
        typeof marker?.options?.stationId === "string"
            ? marker.options.stationId.trim()
            : "";
    const stationName =
        typeof marker?.options?.stationName === "string" &&
        marker.options.stationName.trim()
            ? marker.options.stationName.trim()
            : "Selected station";

    if (!stationId) {
        return;
    }

    const nextRequestId = Number.isInteger(marker.options.stationDetailRequestId)
        ? marker.options.stationDetailRequestId + 1
        : 1;

    marker.options.stationDetailRequestId = nextRequestId;
    marker.bindPopup(
        (() => {
            const popupRoot = createStationPopupRoot({ stationName });
            popupRoot.append(
                createStationPopupMessage({
                    className: "map-facilities-page__station-popup-status",
                    text: "Loading station facilities...",
                }),
            );
            return popupRoot;
        })(),
        getStationPopupOptions(),
    );
    marker.openPopup();

    try {
        const stationDetail = await fetchStationDetail({ stationId });

        if (marker.options.stationDetailRequestId !== nextRequestId) {
            return;
        }

        marker.setPopupContent(
            buildStationPopupContent({
                stationDetail,
                fallbackStationName: stationName,
            }),
        );
    } catch (error) {
        if (marker.options.stationDetailRequestId !== nextRequestId) {
            return;
        }

        marker.setPopupContent(
            (() => {
                const popupRoot = createStationPopupRoot({ stationName });
                popupRoot.append(
                    createStationPopupMessage({
                        className:
                            "map-facilities-page__station-popup-status " +
                            "map-facilities-page__station-popup-status--error",
                        text: "Unable to load station facilities.",
                    }),
                );
                return popupRoot;
            })(),
        );
        reportMapFacilitiesError({
            message: "Unable to load station facilities.",
            error,
        });
    }
};

const attachStationDetailHandlers = ({ stationLayers }) => {
    stationLayers.forEach((stationLayer) => {
        attachPopupDismissHandlers({ marker: stationLayer });
        stationLayer.on("click", () => {
            if (!stationLayer.isPopupOpen()) {
                void openStationDetailPopup({
                    marker: stationLayer,
                });
            }
        });
        stationLayer.on("mouseover", () => {
            if (!stationLayer.isPopupOpen()) {
                void openStationDetailPopup({
                    marker: stationLayer,
                });
            }
        });
    });
};

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

    lineColorByName = buildLineColorByName({ lineDetails });
    const stationLayers = buildStationLayers({ lineDetails });
    attachStationDetailHandlers({ stationLayers });
    const renderedLayers = lineDetails.flatMap((lineData) => {
        const lineColor = getLineColor({ color: lineData?.color });
        return buildShapeLayers({ lineData, lineColor });
    });

    renderedLayers.push(...stationLayers);

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
