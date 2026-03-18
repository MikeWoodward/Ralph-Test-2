"""Thread-safe MBTA singleton for shared use across Django views."""

from __future__ import annotations

import threading

from subway.MBTA_class import MBTA

_mbta_instance: MBTA | None = None
_mbta_lock: threading.Lock = threading.Lock()


def get_mbta() -> MBTA:
    """Return the shared MBTA client, initializing it on first call.

    Uses double-checked locking to ensure thread safety while
    avoiding lock overhead on subsequent calls.

    Returns:
        The initialized MBTA singleton instance.
    """
    global _mbta_instance  # noqa: PLW0603

    if _mbta_instance is None:
        with _mbta_lock:
            if _mbta_instance is None:
                instance = MBTA()
                instance.initialize()
                _mbta_instance = instance

    return _mbta_instance
