"""DPI awareness helpers for consistent Windows coordinates."""

import logging

logger = logging.getLogger(__name__)

_APPLIED = False


def ensure_dpi_awareness() -> None:
    """Make the process DPI-aware before reading screenshots or window rects."""
    global _APPLIED
    if _APPLIED:
        return
    _APPLIED = True

    try:
        import ctypes

        # Per-monitor DPI awareness keeps win32 window rects and screenshots in
        # the same physical-pixel coordinate space on modern Windows.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        logger.debug("Set process DPI awareness via shcore")
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
            logger.debug("Set process DPI awareness via user32")
        except Exception as exc:
            logger.debug("Unable to set DPI awareness: %s", exc)
