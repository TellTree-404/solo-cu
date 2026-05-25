"""Mouse and keyboard automation via pyautogui."""

import logging
import time

import pyautogui
import pyperclip
import win32con
import win32gui

from .config import (
    ACTION_DELAY,
    FOCUS_SETTLE_DELAY,
    PYAUTOGUI_FAILSAFE,
    SETTLE_DELAY,
    TYPE_PRE_DELAY,
)
from .dpi import ensure_dpi_awareness
from .screen import scale_to_original

ensure_dpi_awareness()
pyautogui.FAILSAFE = PYAUTOGUI_FAILSAFE

logger = logging.getLogger(__name__)

_last_focused_window: dict | None = None


def _ensure_original(
    x: int, y: int, orig_w: int, orig_h: int
) -> tuple[int, int]:
    return scale_to_original(x, y, orig_w, orig_h)


def click(x: int, y: int, orig_w: int, orig_h: int, button: str = "left") -> None:
    ox, oy = _ensure_original(x, y, orig_w, orig_h)
    logger.info("click %s at (%d, %d) [orig %d, %d]", button, x, y, ox, oy)
    pyautogui.click(ox, oy, button=button)
    time.sleep(SETTLE_DELAY)


def click_absolute(x: int, y: int, button: str = "left") -> None:
    """Click absolute screen pixels. Use only after structured locators."""
    logger.info("click_absolute %s at (%d, %d)", button, x, y)
    pyautogui.click(x, y, button=button)
    time.sleep(SETTLE_DELAY)


def double_click(x: int, y: int, orig_w: int, orig_h: int) -> None:
    ox, oy = _ensure_original(x, y, orig_w, orig_h)
    logger.info("double_click at (%d, %d) [orig %d, %d]", x, y, ox, oy)
    pyautogui.doubleClick(ox, oy)
    time.sleep(SETTLE_DELAY)


def move_to(x: int, y: int, orig_w: int, orig_h: int) -> None:
    ox, oy = _ensure_original(x, y, orig_w, orig_h)
    logger.info("move_to (%d, %d) [orig %d, %d]", x, y, ox, oy)
    pyautogui.moveTo(ox, oy)
    time.sleep(SETTLE_DELAY)


def type_text(text: str) -> None:
    logger.info("type_text %r", text)
    refocus_last_window()
    time.sleep(TYPE_PRE_DELAY)
    # Non-ASCII text is pasted through the clipboard.
    if any(ord(c) > 127 for c in text):
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=ACTION_DELAY / len(text) if text else 0)
    time.sleep(SETTLE_DELAY)


def key_press(key: str) -> None:
    logger.info("key_press %r", key)
    if "+" in key:
        parts = [k.strip() for k in key.split("+")]
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(key)
    time.sleep(SETTLE_DELAY)


def hotkey(*keys: str) -> None:
    logger.info("hotkey %s", keys)
    pyautogui.hotkey(*keys)
    time.sleep(SETTLE_DELAY)


def scroll(direction: str, amount: int = 3) -> None:
    delta = amount if direction in ("up", "left") else -amount
    logger.info("scroll %s x %d", direction, amount)
    pyautogui.scroll(delta)
    time.sleep(SETTLE_DELAY)


def drag(
    x1: int, y1: int, x2: int, y2: int, orig_w: int, orig_h: int
) -> None:
    ox1, oy1 = _ensure_original(x1, y1, orig_w, orig_h)
    ox2, oy2 = _ensure_original(x2, y2, orig_w, orig_h)
    logger.info(
        "drag (%d, %d) -> (%d, %d) [orig %d, %d -> %d, %d]",
        x1, y1, x2, y2, ox1, oy1, ox2, oy2,
    )
    pyautogui.moveTo(ox1, oy1)
    pyautogui.drag(ox2 - ox1, oy2 - oy1, duration=0.5)
    time.sleep(SETTLE_DELAY)


# ── Window management (win32gui — reliable HWND-level coordinates) ─

def _find_hwnd(title: str) -> int:
    """Find a top-level window HWND by title substring."""

    def _callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            wt = win32gui.GetWindowText(hwnd)
            if title.lower() in wt.lower():
                results.append(hwnd)
        return True

    results = []
    win32gui.EnumWindows(_callback, results)
    if not results:
        raise RuntimeError(f"No visible window found containing {title!r}")

    title_l = title.lower()

    def _rank(hwnd: int) -> tuple[int, int, int, str]:
        wt = win32gui.GetWindowText(hwnd).lower()
        cls = win32gui.GetClassName(hwnd).lower()
        exact = 0 if wt == title_l else 1
        browser_class = 1 if any(token in cls for token in ("chrome", "firefox", "msedge")) else 0
        app_class = 0 if any(token in cls for token in ("mmui", "wechat")) else 1
        return (exact, browser_class, app_class, wt)

    return sorted(results, key=_rank)[0]


def _window_info(hwnd: int) -> dict:
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    title = win32gui.GetWindowText(hwnd)
    return {
        "hwnd": hwnd,
        "title": title,
        "class_name": win32gui.GetClassName(hwnd),
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top,
        "visible": bool(win32gui.IsWindowVisible(hwnd)),
        "minimized": bool(win32gui.IsIconic(hwnd)),
    }


def active_window() -> dict:
    """Return the current foreground window."""
    hwnd = win32gui.GetForegroundWindow()
    return _window_info(hwnd)


def list_windows(title: str | None = None, limit: int = 50) -> list[dict]:
    """List visible top-level windows, optionally filtered by title substring."""

    title_l = title.lower() if title else None
    windows: list[dict] = []

    def _callback(hwnd, _results):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        info = _window_info(hwnd)
        if not info["title"]:
            return True
        if title_l and title_l not in info["title"].lower():
            return True
        if info["width"] <= 0 or info["height"] <= 0:
            return True
        windows.append(info)
        return len(windows) < limit

    win32gui.EnumWindows(_callback, None)
    return windows


def focus_window(title: str) -> dict:
    """Bring window to foreground. Uses win32gui for reliable coordinates.

    Returns {left, top, width, height} in screen pixels.
    """
    global _last_focused_window

    logger.info("focus_window %r", title)
    hwnd = _find_hwnd(title)

    # restore if minimized
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(FOCUS_SETTLE_DELAY)

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    w = right - left
    h = bottom - top

    # validate — retry once if garbage
    if w < 100 or h < 100 or left < -5000:
        logger.warning("focus_window got garbage: %d,%d %dx%d — retrying", left, top, w, h)
        time.sleep(SETTLE_DELAY)
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bottom - top

    if w < 100 or h < 100 or left < -5000:
        raise RuntimeError(
            f"Window {title!r} returned invalid bounds: ({left},{top}) {w}x{h}"
        )

    logger.info("focus_window result: left=%d top=%d w=%d h=%d", left, top, w, h)
    _last_focused_window = {
        "hwnd": hwnd,
        "title": win32gui.GetWindowText(hwnd),
        "class_name": win32gui.GetClassName(hwnd),
        "left": left,
        "top": top,
        "width": w,
        "height": h,
    }
    return dict(_last_focused_window)


def refocus_last_window() -> dict | None:
    """Bring the last focused window back before follow-up actions."""
    if not _last_focused_window:
        return None

    hwnd = int(_last_focused_window["hwnd"])
    if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("Last focused window is no longer available")

    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    active = win32gui.GetForegroundWindow()
    if active != hwnd:
        logger.info(
            "refocus_last_window %r from active %r",
            _last_focused_window.get("title"),
            win32gui.GetWindowText(active),
        )
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(FOCUS_SETTLE_DELAY)

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    _last_focused_window.update(
        {
            "title": win32gui.GetWindowText(hwnd),
            "class_name": win32gui.GetClassName(hwnd),
            "left": left,
            "top": top,
            "width": right - left,
            "height": bottom - top,
        }
    )
    return dict(_last_focused_window)


def _get_active_hwnd_bounds() -> tuple[int, int, int, int]:
    """Get the currently active window bounds via win32gui."""
    hwnd = win32gui.GetForegroundWindow()
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top, right - left, bottom - top


def click_relative(x_pct: float, y_pct: float) -> None:
    """Click inside the last focused window using percentage offsets."""
    focused = refocus_last_window()
    if focused:
        left = int(focused["left"])
        top = int(focused["top"])
        w = int(focused["width"])
        h = int(focused["height"])
    else:
        left, top, w, h = _get_active_hwnd_bounds()
    if w < 50 or h < 50:
        raise RuntimeError(f"Target window too small: {w}x{h}")
    abs_x = left + int(w * x_pct)
    abs_y = top + int(h * y_pct)
    logger.info("click_relative %.2f,%.2f → abs (%d,%d)", x_pct, y_pct, abs_x, abs_y)
    pyautogui.click(abs_x, abs_y)
    time.sleep(SETTLE_DELAY)


def minimize_window(title: str) -> None:
    """Minimize the window with the given title."""
    logger.info("minimize_window %r", title)
    try:
        hwnd = _find_hwnd(title)
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    except RuntimeError:
        pass
    time.sleep(SETTLE_DELAY)
