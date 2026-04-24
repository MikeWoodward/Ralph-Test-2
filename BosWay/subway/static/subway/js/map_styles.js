"use strict";

(() => {
    const DEFAULT_LINE_COLOR = "#1f2937";
    const LINE_WEIGHT = 4;
    const STATION_MARKER_RADIUS = 7;
    const STATION_MARKER_WEIGHT = 3;
    const STATION_MARKER_FILL_COLOR = "#ffffff";

    const getLineColor = ({ color }) =>
        typeof color === "string" && color.trim().length > 0
            ? `#${color.trim()}`
            : DEFAULT_LINE_COLOR;

    const createLineStyle = ({ color }) => ({
        color: getLineColor({ color }),
        lineCap: "round",
        lineJoin: "round",
        opacity: 1,
        weight: LINE_WEIGHT,
    });

    const createStationMarkerStyle = ({ color }) => ({
        color: getLineColor({ color }),
        fillColor: STATION_MARKER_FILL_COLOR,
        fillOpacity: 1,
        lineCap: "round",
        lineJoin: "round",
        opacity: 1,
        radius: STATION_MARKER_RADIUS,
        weight: STATION_MARKER_WEIGHT,
    });

    window.BosWayMapStyles = Object.freeze({
        DEFAULT_LINE_COLOR,
        LINE_WEIGHT,
        STATION_MARKER_FILL_COLOR,
        STATION_MARKER_RADIUS,
        STATION_MARKER_WEIGHT,
        createLineStyle,
        createStationMarkerStyle,
        getLineColor,
    });
})();
