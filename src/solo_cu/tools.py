"""MCP tool definitions exposed by the solo-cu server.

Each tool returns a screenshot (base64 PNG) after execution so the AI
agent always has a fresh view of the screen.
"""

import logging

from . import browser
from . import computer
from . import screen as scr
from . import uia
from . import vision

logger = logging.getLogger(__name__)

_screen_cache: scr.Screenshot | None = None


def _current_screen() -> scr.Screenshot:
    global _screen_cache
    _screen_cache = scr.take_screenshot()
    return _screen_cache


def screen_shot() -> dict:
    """Take a screenshot of the current screen.

    Returns the raw screenshot as base64 PNG. The AI agent can analyze
    this image directly if it has vision capabilities.
    """
    ss = _current_screen()
    return {
        "base64_image": ss.base64,
        "original_width": ss.original_width,
        "original_height": ss.original_height,
        "scaled_width": ss.scaled_width,
        "scaled_height": ss.scaled_height,
    }


def screen_describe() -> str:
    """Use the configured vision model to describe what is currently visible.

    Returns a text description with coordinates of interactive elements.
    Useful when the AI agent does NOT have native vision capabilities.
    """
    ss = _current_screen()
    try:
        desc = vision.describe_screen(ss.base64)
        return desc
    except ValueError as e:
        return str(e)


def _action_result(action_desc: str) -> dict:
    ss = _current_screen()
    return {
        "action": action_desc,
        "base64_image": ss.base64,
        "width": ss.original_width,
        "height": ss.original_height,
    }


def computer_click(x: int, y: int, button: str = "left") -> dict:
    """Click at position (x,y) in the scaled coordinate space (1024x768)."""
    ss = _screen_cache or _current_screen()
    computer.click(x, y, ss.original_width, ss.original_height, button)
    return _action_result(f"click({x}, {y}, {button})")


def computer_click_absolute(x: int, y: int, button: str = "left") -> dict:
    """Click at absolute screen pixel coordinates."""
    computer.click_absolute(x, y, button)
    return _action_result(f"click_absolute({x}, {y}, {button})")


def computer_double_click(x: int, y: int) -> dict:
    """Double-click at position (x,y) in the scaled coordinate space (1024x768)."""
    ss = _screen_cache or _current_screen()
    computer.double_click(x, y, ss.original_width, ss.original_height)
    return _action_result(f"double_click({x}, {y})")


def computer_move(x: int, y: int) -> dict:
    """Move the mouse cursor to (x,y) in the scaled coordinate space (1024x768)."""
    ss = _screen_cache or _current_screen()
    computer.move_to(x, y, ss.original_width, ss.original_height)
    return _action_result(f"move({x}, {y})")


def computer_type(text: str) -> dict:
    """Type the given text using the keyboard."""
    computer.type_text(text)
    return _action_result(f"type({text!r})")


def computer_key(key: str) -> dict:
    """Press a keyboard key (e.g. 'enter', 'escape', 'ctrl+c', 'alt+tab')."""
    computer.key_press(key)
    return _action_result(f"key({key})")


def computer_scroll(direction: str, amount: int = 3) -> dict:
    """Scroll the mouse wheel.

    Args:
        direction: 'up', 'down', 'left', or 'right'
        amount: Number of scroll clicks (default 3)
    """
    computer.scroll(direction, amount)
    return _action_result(f"scroll({direction}, {amount})")


def computer_drag(x1: int, y1: int, x2: int, y2: int) -> dict:
    """Drag from (x1,y1) to (x2,y2) in the scaled coordinate space (1024x768)."""
    ss = _screen_cache or _current_screen()
    computer.drag(x1, y1, x2, y2, ss.original_width, ss.original_height)
    return _action_result(f"drag({x1},{y1} -> {x2},{y2})")


def computer_screenshot() -> dict:
    """Take a fresh screenshot of the current screen (same as screen_shot)."""
    return screen_shot()


def computer_hotkey(*keys: str) -> dict:
    """Press a key combination like win+d, ctrl+c, alt+tab.
    Pass each key as a separate argument. Example: computer_hotkey('win', 'd')"""
    computer.hotkey(*keys)
    return _action_result(f"hotkey({keys})")


def computer_focus_window(title: str) -> dict:
    """Bring window with given title to foreground.

    Returns the window's {left, top, width, height} in actual screen pixels.
    Use before computer_click_relative to operate inside a specific window.
    """
    try:
        bounds = computer.focus_window(title)
        return {
            "ok": True,
            "action": f"focus_window({title!r})",
            **bounds,
        }
    except Exception as e:
        return {
            "ok": False,
            "action": f"focus_window({title!r})",
            "error": str(e),
        }


def computer_click_relative(x_pct: float, y_pct: float) -> dict:
    """Click inside the last focused window using percentage offsets.

    Args:
        x_pct: 0.0–1.0, horizontal position relative to window width.
        y_pct: 0.0–1.0, vertical position relative to window height.

    Must call computer_focus_window first to cache and activate the target window.
    """
    computer.click_relative(x_pct, y_pct)
    return _action_result(f"click_relative({x_pct:.2f}, {y_pct:.2f})")


def computer_minimize_window(title: str) -> dict:
    """Minimize the window with the given title."""
    computer.minimize_window(title)
    return _action_result(f"minimize_window({title!r})")


def screen_describe_window(title: str) -> str:
    """Focus a window, capture its content, and ask the vision model to describe it.

    Returns a description with coordinates relative to the window interior.
    Use computer_click_absolute with window_left + coord_x and window_top + coord_y.
    """
    bounds = computer.focus_window(title)
    ss = _current_screen()
    cropped = scr.crop_screenshot(
        ss, bounds["left"], bounds["top"], bounds["width"], bounds["height"]
    )
    try:
        desc = vision.describe_screen(cropped.base64)
    except ValueError as e:
        return str(e)

    return (
        f"Window: left={bounds['left']} top={bounds['top']} "
        f"{cropped.original_width}x{cropped.original_height}\n"
        f"All coordinates below are in original window pixels. "
        f"To click: use computer_click_absolute("
        f"x=left+coord_x, y=top+coord_y). "
        f"Do not pass these absolute coordinates to computer_click, which uses "
        f"the 1024x768 scaled screen space.\n\n"
        f"{desc}"
    )


def computer_observe(title: str | None = None) -> dict:
    """Inspect foreground state and visible windows without clicking."""
    try:
        active = computer.active_window()
        windows = computer.list_windows(title=title)
        return {
            "ok": True,
            "active_window": active,
            "visible_windows": windows,
            "filtered_by": title,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def computer_uia_tree(title: str | None = None, max_depth: int = 3, max_nodes: int = 80) -> dict:
    """Read a UI Automation tree for a target window or the foreground window."""
    return uia.inspect_window(title=title, max_depth=max_depth, max_nodes=max_nodes)


def computer_locate(selector: dict, title: str | None = None) -> dict:
    """Locate a native Windows control. UIA is the primary supported strategy."""
    strategy = selector.get("strategy", "uia")
    if strategy != "uia":
        return {
            "ok": False,
            "selector": selector,
            "error": f"Unsupported computer locator strategy: {strategy!r}",
        }
    return uia.locate(selector, title=title)


def computer_act(action: dict) -> dict:
    """Run a guarded low-level action.

    Supported actions:
    - {"type": "click", "x": 100, "y": 100}
    - {"type": "click", "selector": {"strategy": "uia", ...}, "title": "..."}
    - {"type": "type", "text": "..."}
    - {"type": "key", "key": "enter"}
    """
    try:
        action_type = action.get("type")
        if action_type == "click" and "selector" in action:
            located = computer_locate(action["selector"], title=action.get("title"))
            if not located.get("ok") or not located.get("matches"):
                return {
                    "ok": False,
                    "action": action,
                    "error": located.get("error", "No locator match."),
                    "locate": located,
                }
            match = located["matches"][0]
            x = match["center"]["x"]
            y = match["center"]["y"]
            computer.click_absolute(x, y, action.get("button", "left"))
            return _action_result(f"act.click_uia({action['selector']!r})")
        if action_type == "click":
            ss = _screen_cache or _current_screen()
            computer.click(
                int(action["x"]),
                int(action["y"]),
                ss.original_width,
                ss.original_height,
                action.get("button", "left"),
            )
            return _action_result(f"act.click({action['x']}, {action['y']})")
        if action_type == "type":
            computer.type_text(action.get("text", ""))
            return _action_result("act.type")
        if action_type == "key":
            computer.key_press(action["key"])
            return _action_result(f"act.key({action['key']})")
        return {"ok": False, "action": action, "error": f"Unsupported action: {action_type!r}"}
    except Exception as e:
        return {"ok": False, "action": action, "error": str(e)}


def browser_open(url: str) -> dict:
    """Open a visible Playwright Chromium page."""
    return browser.open_url(url)


def browser_locate(selector: dict) -> dict:
    """Locate a browser DOM element with Playwright."""
    return browser.locate(selector)


def browser_act(action: dict) -> dict:
    """Run a browser DOM action with Playwright."""
    return browser.act(action)


def browser_close() -> dict:
    """Close the active Playwright browser session."""
    return browser.close()
