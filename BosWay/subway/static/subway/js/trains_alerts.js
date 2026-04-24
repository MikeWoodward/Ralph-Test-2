"use strict";

const LINE_NAMES_ENDPOINT = "/api/lines";
const LINE_DETAIL_ENDPOINT_BASE = "/api/lines/";
const LINE_ALERTS_SUFFIX = "/alerts";
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
let activeSelectionRequestId = 0;

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

const getLineAlertsEndpoint = ({ lineName }) =>
    `${getLineDetailEndpoint({ lineName })}${LINE_ALERTS_SUFFIX}`;

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

const fetchLineAlerts = async ({ lineName }) => {
    const response = await fetch(getLineAlertsEndpoint({ lineName }), {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(
            `Unable to load subway line alerts (${response.status}).`,
        );
    }

    const alerts = await response.json();

    if (!Array.isArray(alerts)) {
        throw new TypeError(
            "Expected the line alerts endpoint to return an array.",
        );
    }

    return alerts;
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

const clearAlertsContent = ({ alertsContent }) => {
    alertsContent.replaceChildren();
};

const hideAlertsPanel = ({ alertsPanel }) => {
    alertsPanel.hidden = true;
};

const showAlertsPanel = ({ alertsPanel }) => {
    alertsPanel.hidden = false;
};

const createAlertsMessage = ({ className, text }) => {
    const message = document.createElement("p");
    message.className = className;
    message.textContent = text;
    return message;
};

const createSeverityBadge = ({ severity }) => {
    if (!Number.isInteger(severity)) {
        return null;
    }

    const badge = document.createElement("span");
    badge.className = "trains-page__alert-severity";
    badge.textContent = `Severity ${severity}`;
    return badge;
};

const createAlertItem = ({ alert }) => {
    const alertItem = document.createElement("article");
    alertItem.className = "trains-page__alert-item";

    const header = document.createElement("div");
    header.className = "trains-page__alert-header";

    const headline = document.createElement("h3");
    headline.className = "trains-page__alert-headline";
    headline.textContent = alert.headline;
    header.append(headline);

    const severityBadge = createSeverityBadge({ severity: alert.severity });

    if (severityBadge) {
        header.append(severityBadge);
    }

    alertItem.append(header);

    if (typeof alert.description === "string" && alert.description.trim()) {
        const description = document.createElement("p");
        description.className = "trains-page__alert-description";
        description.textContent = alert.description.trim();
        alertItem.append(description);
    }

    return alertItem;
};

const renderAlertsLoadingState = ({ alertsPanel, alertsContent, lineName }) => {
    showAlertsPanel({ alertsPanel });
    clearAlertsContent({ alertsContent });
    alertsContent.append(
        createAlertsMessage({
            className: "trains-page__alerts-status",
            text: `Loading alerts for ${lineName}...`,
        }),
    );
};

const renderAlerts = ({ alertsPanel, alertsContent, alerts, lineName }) => {
    showAlertsPanel({ alertsPanel });
    clearAlertsContent({ alertsContent });

    if (alerts.length === 0) {
        alertsContent.append(
            createAlertsMessage({
                className: "trains-page__alerts-status",
                text: `No alerts for ${lineName}.`,
            }),
        );
        return;
    }

    const alertList = document.createElement("div");
    alertList.className = "trains-page__alerts-list";

    alerts.forEach((alert) => {
        if (typeof alert?.headline !== "string" || !alert.headline.trim()) {
            return;
        }

        alertList.append(
            createAlertItem({
                alert: {
                    description: alert.description,
                    headline: alert.headline.trim(),
                    severity: alert.severity,
                },
            }),
        );
    });

    if (alertList.childElementCount === 0) {
        alertsContent.append(
            createAlertsMessage({
                className: "trains-page__alerts-status",
                text: `No alerts for ${lineName}.`,
            }),
        );
        return;
    }

    alertsContent.append(alertList);
};

const renderAlertsErrorState = ({ alertsPanel, alertsContent, lineName }) => {
    showAlertsPanel({ alertsPanel });
    clearAlertsContent({ alertsContent });
    alertsContent.append(
        createAlertsMessage({
            className: "trains-page__alerts-status trains-page__alerts-status--error",
            text: `Unable to load alerts for ${lineName}.`,
        }),
    );
};

const resetSelectedLineState = ({ alertsContent, alertsPanel }) => {
    activeSelectionRequestId += 1;
    removeSelectedLineLayer();
    clearAlertsContent({ alertsContent });
    hideAlertsPanel({ alertsPanel });

    if (trainsMap) {
        trainsMap.fitBounds(SUBWAY_SYSTEM_BOUNDS, {
            padding: MAP_PADDING,
        });
    }
};

const handleLineSelection = async ({
    alertsContent,
    alertsPanel,
    lineSelect,
}) => {
    const selectedLineName = lineSelect.value.trim();

    if (!selectedLineName) {
        resetSelectedLineState({
            alertsContent,
            alertsPanel,
        });
        return;
    }

    activeSelectionRequestId += 1;
    const selectionRequestId = activeSelectionRequestId;
    renderAlertsLoadingState({
        alertsPanel,
        alertsContent,
        lineName: selectedLineName,
    });

    try {
        const [lineData, alerts] = await Promise.all([
            fetchLineDetail({ lineName: selectedLineName }),
            fetchLineAlerts({ lineName: selectedLineName }),
        ]);

        if (selectionRequestId !== activeSelectionRequestId) {
            return;
        }

        renderSelectedLine({ lineData });
        renderAlerts({
            alertsPanel,
            alertsContent,
            alerts,
            lineName: selectedLineName,
        });
    } catch (error) {
        if (selectionRequestId !== activeSelectionRequestId) {
            return;
        }

        renderAlertsErrorState({
            alertsPanel,
            alertsContent,
            lineName: selectedLineName,
        });
        throw error;
    }
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
    const alertsPanel = document.querySelector("#alerts-panel");
    const alertsContent = document.querySelector("#alerts-content");
    const mapElement = document.querySelector("#trains-map");

    if (!(lineSelect instanceof HTMLSelectElement)) {
        return;
    }

    if (!(alertsPanel instanceof HTMLElement)) {
        return;
    }

    if (!(alertsContent instanceof HTMLDivElement)) {
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
        void handleLineSelection({
            alertsContent,
            alertsPanel,
            lineSelect,
        }).catch(reportSelectedLineError);
    });

    void populateLineSelect({ lineSelect }).catch(reportDropdownLoadError);
});
