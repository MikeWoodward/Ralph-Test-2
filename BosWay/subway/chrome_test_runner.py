"""Browser-based Chrome verification for BosWay core user journeys."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import subprocess
import time
import traceback
from typing import Any
from typing import Callable
from typing import Iterator
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import urlopen

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.selenium_manager import SeleniumManager
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_BROWSER_TEST_TIMEOUT_SECONDS = 20
DEFAULT_SERVER_STARTUP_TIMEOUT_SECONDS = 30
DEFAULT_WINDOW_SIZE = "1600,1200"
DEFAULT_CHROME_BINARY = Path(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


@dataclass(frozen=True, slots=True)
class ChromeTestCase:
    """One browser-based Chrome verification case."""

    test_id: str
    name: str
    runner: Callable[[webdriver.Chrome, str], None]


@dataclass(frozen=True, slots=True)
class ChromeTestResult:
    """One executed Chrome test case result."""

    test_id: str
    test_name: str
    timestamp: str
    status: str
    details: str = ""


@dataclass(frozen=True, slots=True)
class ChromeTestRun:
    """The full result set for one Chrome browser run."""

    base_url: str
    browser_name: str
    browser_version: str
    results: tuple[ChromeTestResult, ...]


def _normalize_base_url(
    *,
    base_url: str,
) -> str:
    """Return a normalized base URL without a trailing slash.

    Args:
        base_url: The user-provided base URL for the BosWay app.

    Returns:
        The normalized base URL string.
    """
    return base_url.rstrip("/")


def _format_exception_details(
    *,
    error: Exception,
) -> str:
    """Return one readable exception summary with line context.

    Args:
        error: The browser-test exception that was raised.

    Returns:
        A concise error summary including the failing line number when present.
    """
    traceback_summary = traceback.extract_tb(error.__traceback__)

    if traceback_summary:
        failing_frame = traceback_summary[-1]
        source_line = failing_frame.line or "source unavailable"
        return (
            f"{type(error).__name__} at line {failing_frame.lineno}: "
            f"{source_line} | {error}"
        )

    return f"{type(error).__name__}: {error}"


def _wait_for_condition(
    driver: webdriver.Chrome,
    *,
    description: str,
    predicate: Callable[[webdriver.Chrome], Any],
    timeout_seconds: int = DEFAULT_BROWSER_TEST_TIMEOUT_SECONDS,
) -> Any:
    """Wait until one browser predicate returns a truthy value.

    Args:
        driver: The active Chrome WebDriver instance.
        description: Human-readable wait description for failures.
        predicate: A callable that returns a truthy completion value.
        timeout_seconds: Maximum wait time in seconds.

    Returns:
        The truthy value returned by the predicate.

    Raises:
        TimeoutException: If the condition does not complete in time.
    """
    try:
        return WebDriverWait(driver, timeout_seconds).until(predicate)
    except TimeoutException as error:
        raise TimeoutException(
            f"Timed out while waiting for {description}.",
        ) from error


def discover_chrome_binary() -> Path:
    """Locate the installed Google Chrome binary.

    Returns:
        The path to the Google Chrome executable.

    Raises:
        FileNotFoundError: If Google Chrome cannot be located.
    """
    configured_binary = os.environ.get("GOOGLE_CHROME_BIN", "").strip()

    if configured_binary:
        configured_binary_path = Path(configured_binary).expanduser()
        if configured_binary_path.exists():
            return configured_binary_path

    if DEFAULT_CHROME_BINARY.exists():
        return DEFAULT_CHROME_BINARY

    candidate_binary = shutil.which("google-chrome") or shutil.which(
        "google-chrome-stable",
    )
    if candidate_binary:
        return Path(candidate_binary)

    raise FileNotFoundError(
        "Google Chrome was not found. Set GOOGLE_CHROME_BIN if needed.",
    )


def _is_server_reachable(
    *,
    base_url: str,
) -> bool:
    """Return whether the BosWay server is already reachable.

    Args:
        base_url: The app base URL to probe.

    Returns:
        `True` when the server responds successfully, otherwise `False`.
    """
    try:
        with urlopen(
            f"{_normalize_base_url(base_url=base_url)}/trains-alerts",
            timeout=2,
        ) as response:
            return 200 <= response.status < 400
    except (HTTPError, URLError):
        return False


def _build_runserver_command(
    *,
    base_url: str,
    python_executable: Path,
) -> list[str]:
    """Build the fallback Django dev-server command.

    Args:
        base_url: The desired BosWay base URL.
        python_executable: The Python interpreter to use.

    Returns:
        The subprocess command used to launch Django runserver.
    """
    parsed_base_url = urlparse(_normalize_base_url(base_url=base_url))
    host = parsed_base_url.hostname or "127.0.0.1"
    port = parsed_base_url.port or 8000

    return [
        str(python_executable),
        "manage.py",
        "runserver",
        f"{host}:{port}",
        "--noreload",
    ]


@contextmanager
def _temporary_server(
    *,
    base_url: str,
    project_directory: Path,
    python_executable: Path,
) -> Iterator[subprocess.Popen[str] | None]:
    """Yield a reusable local server process when needed.

    Args:
        base_url: The BosWay base URL that should be reachable.
        project_directory: The Django project directory containing `manage.py`.
        python_executable: The Python interpreter used for `runserver`.

    Yields:
        `None` when an existing server is reused, otherwise the spawned
        `runserver` process.

    Raises:
        RuntimeError: If the requested server cannot be started in time.
    """
    if _is_server_reachable(base_url=base_url):
        yield None
        return

    parsed_base_url = urlparse(_normalize_base_url(base_url=base_url))
    if parsed_base_url.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError(
            "The requested base URL is unavailable and cannot be auto-started.",
        )

    runserver_process = subprocess.Popen(
        _build_runserver_command(
            base_url=base_url,
            python_executable=python_executable,
        ),
        cwd=project_directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        deadline = time.monotonic() + DEFAULT_SERVER_STARTUP_TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            if runserver_process.poll() is not None:
                raise RuntimeError(
                    "The fallback Django server exited before becoming ready.",
                )

            if _is_server_reachable(base_url=base_url):
                yield runserver_process
                return

            time.sleep(0.5)

        raise RuntimeError("Timed out while starting the fallback Django server.")
    finally:
        if runserver_process.poll() is None:
            runserver_process.terminate()
            try:
                runserver_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                runserver_process.kill()
                runserver_process.wait(timeout=5)


def build_chrome_driver(
    *,
    chrome_binary: Path,
    headless: bool,
) -> webdriver.Chrome:
    """Create a Selenium Chrome driver bound to Google Chrome.

    Args:
        chrome_binary: The installed Google Chrome executable path.
        headless: Whether to run Chrome in headless mode.

    Returns:
        The configured Chrome WebDriver instance.
    """
    chrome_options = ChromeOptions()
    chrome_options.binary_location = str(chrome_binary)
    chrome_options.add_argument(f"--window-size={DEFAULT_WINDOW_SIZE}")
    chrome_options.add_argument("--disable-search-engine-choice-screen")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_experimental_option(
        "excludeSwitches",
        ["enable-logging"],
    )

    if headless:
        chrome_options.add_argument("--headless=new")

    original_path = os.environ.get("PATH", "")
    filtered_path_entries = [
        path_entry
        for path_entry in original_path.split(os.pathsep)
        if path_entry and not (Path(path_entry) / "chromedriver").exists()
    ]

    try:
        os.environ["PATH"] = os.pathsep.join(filtered_path_entries)
        driver_paths = SeleniumManager().binary_paths(
            [
                "--browser",
                "chrome",
                "--browser-path",
                str(chrome_binary),
            ],
        )
        chrome_service = ChromeService(
            executable_path=driver_paths["driver_path"],
        )
        chrome_driver = webdriver.Chrome(
            options=chrome_options,
            service=chrome_service,
        )
    finally:
        os.environ["PATH"] = original_path

    chrome_driver.set_page_load_timeout(DEFAULT_BROWSER_TEST_TIMEOUT_SECONDS)
    return chrome_driver


def _wait_for_title(
    driver: webdriver.Chrome,
    *,
    expected_title: str,
) -> None:
    """Wait until the page title matches the expected BosWay title.

    Args:
        driver: The active Chrome WebDriver instance.
        expected_title: The expected document title.
    """
    _wait_for_condition(
        driver,
        description=f"title {expected_title!r}",
        predicate=lambda browser: browser.title == expected_title,
    )


def _wait_for_line_select_options(
    driver: webdriver.Chrome,
) -> None:
    """Wait until the trains page line dropdown is populated.

    Args:
        driver: The active Chrome WebDriver instance.
    """
    _wait_for_condition(
        driver,
        description="line-select options to load",
        predicate=lambda browser: len(
            Select(
                browser.find_element(By.ID, "line-select"),
            ).options,
        )
        > 1,
    )


def _count_station_marker_paths(
    driver: webdriver.Chrome,
    *,
    map_selector: str,
) -> int:
    """Return the number of rendered station marker SVG paths.

    Args:
        driver: The active Chrome WebDriver instance.
        map_selector: The CSS selector for the target Leaflet map container.

    Returns:
        The count of station marker SVG paths rendered in the map.
    """
    return int(
        driver.execute_script(
            """
            const mapSelector = arguments[0];
            return document.querySelectorAll(
                `${mapSelector} .leaflet-overlay-pane svg path[fill="#ffffff"]`
            ).length;
            """,
            map_selector,
        ),
    )


def _find_station_marker(
    driver: webdriver.Chrome,
    *,
    map_selector: str,
) -> Any:
    """Return the first visible station marker inside one Leaflet map.

    Args:
        driver: The active Chrome WebDriver instance.
        map_selector: The CSS selector for the target Leaflet map container.

    Returns:
        The first station marker WebElement.
    """
    marker_selector = (
        f'{map_selector} .leaflet-overlay-pane svg path[fill="#ffffff"]'
    )

    _wait_for_condition(
        driver,
        description=f"station markers inside {map_selector}",
        predicate=lambda browser: _count_station_marker_paths(
            browser,
            map_selector=map_selector,
        )
        > 0,
    )
    marker_elements = driver.find_elements(By.CSS_SELECTOR, marker_selector)

    if not marker_elements:
        raise AssertionError(
            f"Expected at least one station marker in {map_selector}.",
        )

    return marker_elements[0]


def _dispatch_marker_click(
    driver: webdriver.Chrome,
    *,
    marker: Any,
) -> None:
    """Dispatch a DOM click event on one Leaflet station marker.

    Args:
        driver: The active Chrome WebDriver instance.
        marker: The station marker WebElement to activate.
    """
    driver.execute_script(
        """
        const marker = arguments[0];
        marker.dispatchEvent(
            new MouseEvent("click", {
                bubbles: true,
                cancelable: true,
                view: window,
            })
        );
        """,
        marker,
    )


def _wait_for_alerts_content(
    driver: webdriver.Chrome,
) -> None:
    """Wait until the selected-line alerts panel finishes loading.

    Args:
        driver: The active Chrome WebDriver instance.
    """
    _wait_for_condition(
        driver,
        description="alerts content to render",
        predicate=lambda browser: (
            not browser.execute_script(
                "return document.querySelector('#alerts-panel').hidden;",
            )
            and "Loading alerts for"
            not in browser.find_element(By.ID, "alerts-content").text
            and browser.find_element(By.ID, "alerts-content").text.strip()
        ),
    )


def _open_trains_page(
    driver: webdriver.Chrome,
    *,
    base_url: str,
) -> None:
    """Open the trains page and wait for the dropdown to populate.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    driver.get(f"{_normalize_base_url(base_url=base_url)}/trains-alerts")
    _wait_for_title(driver, expected_title="BosWay - trains & alerts")
    _wait_for_line_select_options(driver)


def _open_map_facilities_page(
    driver: webdriver.Chrome,
    *,
    base_url: str,
) -> None:
    """Open the map and facilities page and wait for its legend.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    driver.get(f"{_normalize_base_url(base_url=base_url)}/map-facilities")
    _wait_for_title(driver, expected_title="BosWay - map & facilities")
    _wait_for_condition(
        driver,
        description="map legend entries to render",
        predicate=lambda browser: len(
            browser.find_elements(
                By.CSS_SELECTOR,
                "#map-facilities-legend-items li",
            ),
        )
        > 0,
    )


def _case_trains_page_loads_and_populates_dropdown(
    driver: webdriver.Chrome,
    base_url: str,
) -> None:
    """Verify the trains page loads and shows the MBTA line list.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    _open_trains_page(
        driver,
        base_url=base_url,
    )
    line_select = Select(driver.find_element(By.ID, "line-select"))
    option_values = [option.text.strip() for option in line_select.options]

    if "Select a subway line to display" not in option_values:
        raise AssertionError("The default trains-page option is missing.")

    if "Red Line" not in option_values:
        raise AssertionError("The trains-page dropdown is missing Red Line.")


def _case_selected_line_renders_map_and_alerts(
    driver: webdriver.Chrome,
    base_url: str,
) -> None:
    """Verify a line selection renders stations and alerts.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    _open_trains_page(
        driver,
        base_url=base_url,
    )
    line_select = Select(driver.find_element(By.ID, "line-select"))
    line_select.select_by_visible_text("Red Line")

    _wait_for_alerts_content(driver)
    _wait_for_condition(
        driver,
        description="selected-line station markers to render",
        predicate=lambda browser: _count_station_marker_paths(
            browser,
            map_selector="#trains-map",
        )
        > 0,
    )

    if line_select.first_selected_option.text.strip() != "Red Line":
        raise AssertionError("The selected dropdown value did not stay on Red Line.")


def _case_station_predictions_popup_opens(
    driver: webdriver.Chrome,
    base_url: str,
) -> None:
    """Verify the trains page opens a station predictions popup.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    _open_trains_page(
        driver,
        base_url=base_url,
    )
    Select(driver.find_element(By.ID, "line-select")).select_by_visible_text(
        "Red Line",
    )
    _wait_for_alerts_content(driver)
    station_marker = _find_station_marker(
        driver,
        map_selector="#trains-map",
    )
    _dispatch_marker_click(
        driver,
        marker=station_marker,
    )

    _wait_for_condition(
        driver,
        description="station prediction popup to render",
        predicate=lambda browser: (
            (popup_root := browser.find_element(
                By.CSS_SELECTOR,
                ".trains-page__prediction-popup",
            ))
            and "Loading subway predictions..." not in popup_root.text
            and popup_root.text.strip()
        ),
    )


def _case_map_facilities_loads_network_and_legend(
    driver: webdriver.Chrome,
    base_url: str,
) -> None:
    """Verify the full network and legend render on the map page.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    _open_map_facilities_page(
        driver,
        base_url=base_url,
    )
    _wait_for_condition(
        driver,
        description="full-network station markers to render",
        predicate=lambda browser: _count_station_marker_paths(
            browser,
            map_selector="#map-facilities-map",
        )
        > 0,
    )


def _case_map_facilities_station_popup_opens(
    driver: webdriver.Chrome,
    base_url: str,
) -> None:
    """Verify the map page opens a station facilities popup.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    _open_map_facilities_page(
        driver,
        base_url=base_url,
    )
    station_marker = _find_station_marker(
        driver,
        map_selector="#map-facilities-map",
    )
    ActionChains(driver).move_to_element(station_marker).click().perform()

    _wait_for_condition(
        driver,
        description="station facilities popup to render",
        predicate=lambda browser: (
            (popup_root := browser.find_element(
                By.CSS_SELECTOR,
                ".map-facilities-page__station-popup",
            ))
            and "Loading station facilities..." not in popup_root.text
            and "Lines served" in popup_root.text
            and "Facilities" in popup_root.text
        ),
    )


def _case_about_page_shows_required_credits(
    driver: webdriver.Chrome,
    base_url: str,
) -> None:
    """Verify the About page shows the required credit content.

    Args:
        driver: The active Chrome WebDriver instance.
        base_url: The BosWay base URL.
    """
    driver.get(f"{_normalize_base_url(base_url=base_url)}/about")
    _wait_for_title(driver, expected_title="BosWay - about")
    page_text = driver.find_element(By.TAG_NAME, "body").text

    required_snippets = (
        "Mike Woodward",
        "MBTA V3 API",
        "OpenStreetMap",
        "Leaflet.js",
        "the MBTA subway schedules page",
    )

    for required_snippet in required_snippets:
        if required_snippet not in page_text:
            raise AssertionError(
                f"The About page is missing {required_snippet!r}.",
            )


def build_chrome_test_cases() -> tuple[ChromeTestCase, ...]:
    """Return the PRD-aligned Chrome browser cases for story 6.4.

    Returns:
        The ordered set of Chrome test cases to execute.
    """
    return (
        ChromeTestCase(
            test_id="chrome-001",
            name="Trains page loads and populates the line dropdown",
            runner=_case_trains_page_loads_and_populates_dropdown,
        ),
        ChromeTestCase(
            test_id="chrome-002",
            name="Selecting a line renders stations and alerts",
            runner=_case_selected_line_renders_map_and_alerts,
        ),
        ChromeTestCase(
            test_id="chrome-003",
            name="Station predictions popup opens on the trains page",
            runner=_case_station_predictions_popup_opens,
        ),
        ChromeTestCase(
            test_id="chrome-004",
            name="Map and facilities page renders the network and legend",
            runner=_case_map_facilities_loads_network_and_legend,
        ),
        ChromeTestCase(
            test_id="chrome-005",
            name="Station facilities popup opens on the map page",
            runner=_case_map_facilities_station_popup_opens,
        ),
        ChromeTestCase(
            test_id="chrome-006",
            name="About page shows credits and MBTA acknowledgment",
            runner=_case_about_page_shows_required_credits,
        ),
    )


def write_chrome_test_artifacts(
    *,
    output_directory: Path,
    test_run: ChromeTestRun,
) -> tuple[Path, Path]:
    """Write machine-readable and markdown Chrome test artifacts.

    Args:
        output_directory: The target `test-results` directory.
        test_run: The executed Chrome test run.

    Returns:
        The JSON and Markdown artifact paths.
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "chrome-tests.json"
    markdown_path = output_directory / "chrome-tests.md"

    json_path.write_text(
        json.dumps(
            [asdict(result) for result in test_run.results],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    total_tests = len(test_run.results)
    failed_results = [
        result for result in test_run.results if result.status == "fail"
    ]
    passed_count = total_tests - len(failed_results)
    markdown_lines = [
        "# Chrome Test Summary",
        "",
        f"- Base URL: `{test_run.base_url}`",
        f"- Browser: `{test_run.browser_name} {test_run.browser_version}`",
        f"- Total tests run: {total_tests}",
        f"- Total passed: {passed_count}",
        f"- Total failed: {len(failed_results)}",
        "",
        "## Executed Test Cases",
        "",
        "| ID | Name | Status | Timestamp |",
        "| --- | --- | --- | --- |",
    ]
    markdown_lines.extend(
        [
            (
                f"| `{result.test_id}` | {result.test_name} | "
                f"`{result.status}` | `{result.timestamp}` |"
            )
            for result in test_run.results
        ],
    )
    markdown_lines.extend(
        [
            "",
            "## Failed Test Cases",
            "",
        ],
    )

    if failed_results:
        markdown_lines.extend(
            [
                (
                    f"- `{result.test_id}` {result.test_name}: "
                    f"{result.details}"
                )
                for result in failed_results
            ],
        )
    else:
        markdown_lines.append("- None.")

    markdown_path.write_text(
        "\n".join(markdown_lines) + "\n",
        encoding="utf-8",
    )

    return json_path, markdown_path


def run_chrome_test_suite(
    *,
    base_url: str,
    headless: bool,
    output_directory: Path,
    project_directory: Path,
    python_executable: Path,
) -> ChromeTestRun:
    """Run the BosWay Chrome browser suite and persist its artifacts.

    Args:
        base_url: The BosWay base URL.
        headless: Whether to run Chrome in headless mode.
        output_directory: The target `test-results` directory.
        project_directory: The Django project directory containing `manage.py`.
        python_executable: The Python interpreter used for fallback `runserver`.

    Returns:
        The full executed Chrome test run.
    """
    chrome_binary = discover_chrome_binary()
    normalized_base_url = _normalize_base_url(base_url=base_url)
    results: list[ChromeTestResult] = []

    with _temporary_server(
        base_url=normalized_base_url,
        project_directory=project_directory,
        python_executable=python_executable,
    ):
        chrome_driver = build_chrome_driver(
            chrome_binary=chrome_binary,
            headless=headless,
        )
        try:
            browser_name = str(chrome_driver.capabilities.get("browserName", "chrome"))
            browser_version = str(
                chrome_driver.capabilities.get("browserVersion", "unknown"),
            )

            for test_case in build_chrome_test_cases():
                timestamp = datetime.now(tz=UTC).isoformat()
                try:
                    test_case.runner(chrome_driver, normalized_base_url)
                except Exception as error:
                    results.append(
                        ChromeTestResult(
                            test_id=test_case.test_id,
                            test_name=test_case.name,
                            timestamp=timestamp,
                            status="fail",
                            details=_format_exception_details(error=error),
                        ),
                    )
                else:
                    results.append(
                        ChromeTestResult(
                            test_id=test_case.test_id,
                            test_name=test_case.name,
                            timestamp=timestamp,
                            status="pass",
                        ),
                    )

            test_run = ChromeTestRun(
                base_url=normalized_base_url,
                browser_name=browser_name,
                browser_version=browser_version,
                results=tuple(results),
            )
            write_chrome_test_artifacts(
                output_directory=output_directory,
                test_run=test_run,
            )
            return test_run
        finally:
            chrome_driver.quit()

    raise RuntimeError("The Chrome test suite did not execute.")
