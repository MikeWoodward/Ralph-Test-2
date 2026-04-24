"""Shared MBTA service integration for the subway app."""

from __future__ import annotations

import importlib.util
import linecache
import logging
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any

from dotenv import load_dotenv

LOGGER = logging.getLogger(__name__)

_MBTA_CLASS: type[Any] | None = None
_MBTA_SERVICE: Any | None = None
_MBTA_INITIALIZED = False
_SERVICE_LOCK = Lock()
_INITIALIZE_LOCK = Lock()


def _log_exception_details(
    *,
    error: Exception,
) -> None:
    """Log the line number and source text for an exception.

    Args:
        error: The exception that was raised.
    """
    traceback_frame = error.__traceback__
    while traceback_frame and traceback_frame.tb_next:
        traceback_frame = traceback_frame.tb_next

    if traceback_frame is None:
        LOGGER.exception("Unhandled exception: %s", error)
        return

    line_number = traceback_frame.tb_lineno
    file_path = traceback_frame.tb_frame.f_code.co_filename
    source_line = linecache.getline(
        file_path,
        line_number,
    ).strip()
    LOGGER.exception(
        "Unhandled exception at %s:%s: %s | %s",
        file_path,
        line_number,
        source_line or "<source unavailable>",
        error,
    )


def _repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[2]


def _mbta_module_path() -> Path:
    """Return the sibling MBTA client source file path."""
    return _repo_root().parent / "MBTA-API" / "MBTA_class.py"


def _load_repo_environment() -> None:
    """Load server-side environment variables from the repo root."""
    load_dotenv(
        dotenv_path=_repo_root() / ".env",
        override=False,
    )


def _load_mbta_module() -> ModuleType:
    """Load the sibling MBTA module from disk.

    Returns:
        The imported module object containing the MBTA class.

    Raises:
        FileNotFoundError: If the sibling MBTA source file is missing.
        ImportError: If the sibling MBTA module cannot be loaded.
    """
    mbta_source_path = _mbta_module_path()
    if not mbta_source_path.exists():
        raise FileNotFoundError(
            f"MBTA client file not found: {mbta_source_path}",
        )

    spec = importlib.util.spec_from_file_location(
        "subway_external_mbta",
        mbta_source_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Unable to load module spec for {mbta_source_path}",
        )

    mbta_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mbta_module)
    return mbta_module


def _load_mbta_class() -> type[Any]:
    """Return the MBTA class from the sibling MBTA project.

    Returns:
        The imported MBTA class.
    """
    global _MBTA_CLASS

    if _MBTA_CLASS is None:
        _MBTA_CLASS = _load_mbta_module().MBTA

    return _MBTA_CLASS


def get_mbta_service() -> Any:
    """Return the shared MBTA client instance for the app.

    Returns:
        The singleton MBTA client instance.
    """
    global _MBTA_SERVICE

    if _MBTA_SERVICE is not None:
        return _MBTA_SERVICE

    with _SERVICE_LOCK:
        if _MBTA_SERVICE is None:
            try:
                _load_repo_environment()
                mbta_class = _load_mbta_class()
                _MBTA_SERVICE = mbta_class()
            except Exception as error:  # noqa: BLE001
                _log_exception_details(error=error)
                raise

    return _MBTA_SERVICE


def initialize_service() -> Any:
    """Initialize the shared MBTA client once at startup.

    Returns:
        The initialized singleton MBTA client instance.
    """
    global _MBTA_INITIALIZED

    mbta_service = get_mbta_service()
    if _MBTA_INITIALIZED:
        return mbta_service

    with _INITIALIZE_LOCK:
        if not _MBTA_INITIALIZED:
            try:
                mbta_service.initialize()
            except Exception as error:  # noqa: BLE001
                _log_exception_details(error=error)
                raise

            _MBTA_INITIALIZED = True

    return mbta_service
