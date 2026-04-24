"use strict";

const LINE_NAMES_ENDPOINT = "/api/lines";

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

document.addEventListener("DOMContentLoaded", () => {
    const lineSelect = document.querySelector("#line-select");

    if (!(lineSelect instanceof HTMLSelectElement)) {
        return;
    }

    void populateLineSelect({ lineSelect }).catch(reportDropdownLoadError);
});
