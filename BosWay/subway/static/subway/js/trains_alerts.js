"use strict";

const LINE_NAMES_ENDPOINT = "/api/lines";
const LINE_DETAIL_ENDPOINT_BASE = "/api/lines/";
const LINE_ALERTS_SUFFIX = "/alerts";
const STATION_ENDPOINT_BASE = "/api/stations/";
const STATION_PREDICTIONS_SUFFIX = "/predictions";
const TILE_LAYER_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_LAYER_ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">' +
    "OpenStreetMap</a> contributors";
const SUBWAY_SYSTEM_BOUNDS = [
    [42.2000, -71.2600],
    [42.4400, -70.9800],
];
const MAP_PADDING = [24, 24];
const MAX_PREDICTIONS_PER_LINE = 4;
const POPUP_MAX_WIDTH = 320;
const POPUP_CLOSE_DELAY_MS = 180;
const POPUP_AUTO_PAN_PADDING = 24;
const mapStyles = window.BosWayMapStyles ?? {};
const DEFAULT_LINE_COLOR = mapStyles.DEFAULT_LINE_COLOR ?? "#1f2937";
const normalizeLineColor =
    mapStyles.getLineColor ??
    (({ color }) => {
        if (typeof color !== "string" || color.trim().length === 0) {
            return DEFAULT_LINE_COLOR;
        }

        const normalizedColor = color.trim().startsWith("#")
            ? color.trim().slice(1)
            : color.trim();

        return normalizedColor ? `#${normalizedColor}` : DEFAULT_LINE_COLOR;
    });
const createLineStyle =
    mapStyles.createLineStyle ??
    (({ color }) => ({
        color: normalizeLineColor({ color }),
        lineCap: "round",
        lineJoin: "round",
        opacity: 1,
        weight: 4,
    }));
const createStationMarkerStyle =
    mapStyles.createStationMarkerStyle ??
    (({ color }) => ({
        color: normalizeLineColor({ color }),
        fillColor: "#ffffff",
        fillOpacity: 1,
        lineCap: "round",
        lineJoin: "round",
        opacity: 1,
        radius: 7,
        weight: 3,
    }));

const predictionTimeFormatter = new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
});

let trainsMap = null;
let selectedLineLayerGroup = null;
let activeSelectionRequestId = 0;
let activePopupCloseTimeoutId = null;

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

const reportPredictionLoadError = (error) => {
    const stackFrame =
        typeof error?.stack === "string"
            ? (error.stack.split("\n")[1] ?? "unknown").trim()
            : "unknown";

    console.error(
        "Unable to load station predictions.",
        stackFrame,
        error,
    );
};

const getLineDetailEndpoint = ({ lineName }) =>
    `${LINE_DETAIL_ENDPOINT_BASE}${encodeURIComponent(lineName)}`;

const getLineAlertsEndpoint = ({ lineName }) =>
    `${getLineDetailEndpoint({ lineName })}${LINE_ALERTS_SUFFIX}`;

const getStationPredictionsEndpoint = ({ stationId }) =>
    `${STATION_ENDPOINT_BASE}${encodeURIComponent(stationId)}` +
    `${STATION_PREDICTIONS_SUFFIX}`;

const isFiniteCoordinateValue = (value) =>
    typeof value === "number" && Number.isFinite(value);

const parseCoordinatePair = ({ coordinatePair, context }) => {
    if (!Array.isArray(coordinatePair) || coordinatePair.length !== 2) {
        throw new TypeError(`${context} must contain [latitude, longitude].`);
    }

    const [latitude, longitude] = coordinatePair;

    if (
        !isFiniteCoordinateValue(latitude) ||
        !isFiniteCoordinateValue(longitude)
    ) {
        throw new TypeError(`${context} must contain finite coordinates.`);
    }

    return [latitude, longitude];
};

const parseShapeList = ({ shapes }) => {
    if (!Array.isArray(shapes)) {
        throw new TypeError("Expected the line detail payload to include shapes.");
    }

    return shapes.map((shapeCoordinates, shapeIndex) => {
        if (!Array.isArray(shapeCoordinates)) {
            throw new TypeError(
                `Line shape ${shapeIndex + 1} must be an array of coordinates.`,
            );
        }

        return shapeCoordinates.map((coordinatePair, coordinateIndex) =>
            parseCoordinatePair({
                coordinatePair,
                context:
                    `Line shape ${shapeIndex + 1}, coordinate ` +
                    `${coordinateIndex + 1}`,
            }),
        );
    });
};

const parseStationSummary = ({ station, stationIndex }) => {
    if (
        typeof station !== "object" ||
        station === null ||
        Array.isArray(station)
    ) {
        throw new TypeError(
            `Station ${stationIndex + 1} must be an object payload.`,
        );
    }

    const stationName =
        typeof station.name === "string" && station.name.trim()
            ? station.name.trim()
            : "Selected station";

    if (
        !isFiniteCoordinateValue(station.latitude) ||
        !isFiniteCoordinateValue(station.longitude)
    ) {
        throw new TypeError(
            `Station ${stationIndex + 1} must include finite coordinates.`,
        );
    }

    return {
        latitude: station.latitude,
        longitude: station.longitude,
        name: stationName,
        station_id:
            typeof station.station_id === "string"
                ? station.station_id.trim()
                : "",
    };
};

const parseLineDetailPayload = ({ lineData, requestedLineName }) => {
    if (
        typeof lineData !== "object" ||
        lineData === null ||
        Array.isArray(lineData)
    ) {
        throw new TypeError(
            "Expected the line detail endpoint to return an object.",
        );
    }

    return {
        color:
            typeof lineData.color === "string" ? lineData.color.trim() : "",
        name:
            typeof lineData.name === "string" && lineData.name.trim()
                ? lineData.name.trim()
                : requestedLineName,
        shapes: parseShapeList({ shapes: lineData.shapes }),
        stations: Array.isArray(lineData.stations)
            ? lineData.stations.map((station, stationIndex) =>
                  parseStationSummary({
                      station,
                      stationIndex,
                  }),
              )
            : (() => {
                  throw new TypeError(
                      "Expected the line detail payload to include stations.",
                  );
              })(),
    };
};

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

    const lineData = await response.json();
    return parseLineDetailPayload({
        lineData,
        requestedLineName: lineName,
    });
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

const fetchStationPredictions = async ({ stationId }) => {
    const response = await fetch(getStationPredictionsEndpoint({ stationId }), {
        headers: {
            Accept: "application/json",
        },
    });

    if (!response.ok) {
        throw new Error(
            `Unable to load station predictions (${response.status}).`,
        );
    }

    const predictions = await response.json();

    if (!Array.isArray(predictions)) {
        throw new TypeError(
            "Expected the station predictions endpoint to return an array.",
        );
    }

    return predictions;
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
            window.L.polyline(
                shapeCoordinates,
                createLineStyle({ color: lineColor }),
            ),
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
                    ...createStationMarkerStyle({ color: lineColor }),
                    stationId: station.station_id,
                    stationName:
                        typeof station.name === "string" && station.name.trim()
                            ? station.name.trim()
                            : "Selected station",
                },
            ),
        );

const getPredictionTimestamp = ({ prediction }) => {
    const candidateTimestamp =
        typeof prediction?.arrival_time === "string" &&
        prediction.arrival_time.trim()
            ? prediction.arrival_time
            : prediction?.departure_time;

    if (typeof candidateTimestamp !== "string" || !candidateTimestamp.trim()) {
        return null;
    }

    const timestamp = Date.parse(candidateTimestamp);
    return Number.isFinite(timestamp) ? timestamp : null;
};

const formatPredictionTime = ({ prediction }) => {
    const timestamp = getPredictionTimestamp({ prediction });

    if (timestamp !== null) {
        const minutesUntilArrival = Math.ceil((timestamp - Date.now()) / 60000);

        if (minutesUntilArrival <= 0) {
            return "Due";
        }

        if (minutesUntilArrival < 60) {
            return `${minutesUntilArrival} min`;
        }

        return predictionTimeFormatter.format(new Date(timestamp));
    }

    if (typeof prediction?.status === "string" && prediction.status.trim()) {
        return prediction.status.trim();
    }

    return "Time unavailable";
};

const sortPredictions = ({ predictions }) =>
    [...predictions].sort((leftPrediction, rightPrediction) => {
        const leftTimestamp = getPredictionTimestamp({
            prediction: leftPrediction,
        });
        const rightTimestamp = getPredictionTimestamp({
            prediction: rightPrediction,
        });

        if (leftTimestamp !== null && rightTimestamp !== null) {
            return leftTimestamp - rightTimestamp;
        }

        if (leftTimestamp !== null) {
            return -1;
        }

        if (rightTimestamp !== null) {
            return 1;
        }

        return formatPredictionTime({ prediction: leftPrediction }).localeCompare(
            formatPredictionTime({ prediction: rightPrediction }),
        );
    });

const groupPredictionsByLine = ({ predictions }) =>
    sortPredictions({ predictions }).reduce((predictionGroups, prediction) => {
        const lineName =
            typeof prediction?.line === "string" ? prediction.line.trim() : "";

        if (!lineName) {
            return predictionGroups;
        }

        const groupedPredictions = predictionGroups.get(lineName) ?? [];

        if (groupedPredictions.length >= MAX_PREDICTIONS_PER_LINE) {
            return predictionGroups;
        }

        predictionGroups.set(lineName, [...groupedPredictions, prediction]);
        return predictionGroups;
    }, new Map());

const createPredictionPopupMessage = ({ className, text }) => {
    const message = document.createElement("p");
    message.className = className;
    message.textContent = text;
    return message;
};

const createPredictionPopupRoot = ({ stationName }) => {
    const popupRoot = document.createElement("section");
    popupRoot.className = "trains-page__prediction-popup";

    const title = document.createElement("h3");
    title.className = "trains-page__prediction-title";
    title.textContent = stationName;
    popupRoot.append(title);

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

const getPredictionPopupOptions = () => ({
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
    className: "trains-page__prediction-leaflet-popup",
    maxHeight: Math.max(180, Math.floor(window.innerHeight * 0.45)),
    maxWidth: POPUP_MAX_WIDTH,
});

const createPredictionGroup = ({ lineName, predictions }) => {
    const group = document.createElement("section");
    group.className = "trains-page__prediction-group";

    const heading = document.createElement("h4");
    heading.className = "trains-page__prediction-line";
    heading.textContent = lineName;
    group.append(heading);

    const predictionList = document.createElement("ul");
    predictionList.className = "trains-page__prediction-list";

    predictions.forEach((prediction) => {
        const predictionItem = document.createElement("li");
        predictionItem.className = "trains-page__prediction-item";

        const destination = document.createElement("span");
        destination.className = "trains-page__prediction-destination";
        destination.textContent =
            typeof prediction?.destination === "string" &&
            prediction.destination.trim()
                ? prediction.destination.trim()
                : "Destination unavailable";

        const time = document.createElement("span");
        time.className = "trains-page__prediction-time";
        time.textContent = formatPredictionTime({ prediction });

        predictionItem.append(destination, time);
        predictionList.append(predictionItem);
    });

    group.append(predictionList);
    return group;
};

const buildPredictionPopupContent = ({ stationName, predictions }) => {
    const popupRoot = createPredictionPopupRoot({ stationName });
    const predictionGroups = groupPredictionsByLine({ predictions });

    if (predictionGroups.size === 0) {
        popupRoot.append(
            createPredictionPopupMessage({
                className: "trains-page__prediction-status",
                text: "No subway predictions.",
            }),
        );
        return popupRoot;
    }

    Array.from(predictionGroups.entries())
        .sort(([leftLineName], [rightLineName]) =>
            leftLineName.localeCompare(rightLineName),
        )
        .forEach(([lineName, linePredictions]) => {
            popupRoot.append(
                createPredictionGroup({
                    lineName,
                    predictions: linePredictions,
                }),
            );
        });

    return popupRoot;
};

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

const openStationPredictionsPopup = async ({ marker }) => {
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

    const nextPredictionRequestId =
        Number.isInteger(marker.options.predictionRequestId)
            ? marker.options.predictionRequestId + 1
            : 1;

    marker.options.predictionRequestId = nextPredictionRequestId;
    marker.bindPopup(
        (() => {
            const popupRoot = createPredictionPopupRoot({ stationName });
            popupRoot.append(
                createPredictionPopupMessage({
                    className: "trains-page__prediction-status",
                    text: "Loading subway predictions...",
                }),
            );
            return popupRoot;
        })(),
        getPredictionPopupOptions(),
    );
    marker.openPopup();

    try {
        const predictions = await fetchStationPredictions({ stationId });

        if (marker.options.predictionRequestId !== nextPredictionRequestId) {
            return;
        }

        marker.setPopupContent(
            buildPredictionPopupContent({
                stationName,
                predictions,
            }),
        );
    } catch (error) {
        if (marker.options.predictionRequestId !== nextPredictionRequestId) {
            return;
        }

        marker.setPopupContent(
            (() => {
                const popupRoot = createPredictionPopupRoot({ stationName });
                popupRoot.append(
                    createPredictionPopupMessage({
                        className:
                            "trains-page__prediction-status " +
                            "trains-page__prediction-status--error",
                        text: "Unable to load subway predictions.",
                    }),
                );
                return popupRoot;
            })(),
        );
        reportPredictionLoadError(error);
    }
};

const attachStationPredictionHandlers = ({ stationLayers }) => {
    stationLayers.forEach((stationLayer) => {
        attachPopupDismissHandlers({ marker: stationLayer });
        stationLayer.on("click", () => {
            void openStationPredictionsPopup({
                marker: stationLayer,
            });
        });
    });
};

const renderSelectedLine = ({ lineData }) => {
    if (!trainsMap || typeof window.L === "undefined") {
        return;
    }

    const lineColor = createLineStyle({ color: lineData?.color }).color;
    const stationLayers = buildStationLayers({ lineData, lineColor });

    attachStationPredictionHandlers({ stationLayers });
    const renderedLayers = [
        ...buildShapeLayers({ lineData, lineColor }),
        ...stationLayers,
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

        removeSelectedLineLayer();
        if (trainsMap) {
            trainsMap.fitBounds(SUBWAY_SYSTEM_BOUNDS, {
                padding: MAP_PADDING,
            });
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
