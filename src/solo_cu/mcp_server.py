"""MCP Server entry point for solo-cu.

Registers Computer Use and Browser Use tools over the MCP protocol.
Compatible with OpenCode, Claude Code, Codex CLI, Cursor, Hermes Agent,
Codex Desktop, and any other MCP-compatible AI tool.

Usage:
    solo-cu              # run via pyproject.toml console-script
    python -m solo_cu.mcp_server
"""

import logging
import sys

from . import config
from . import tools as _tools

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# ── MCP boilerplate (sdk-agnostic) ──────────────────────────────────────
# We try the modern FastMCP API first, then fall back to the low-level Server.

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationCapabilities
    from mcp.server.stdio import stdio_server
except ImportError:
    Server = None


def _build_fastmcp():
    """Register tools via FastMCP (recommended)."""
    mcp = FastMCP("solo-cu")

    # ── Visibility ──────────────────────────────────────────────
    @mcp.tool()
    def screen_shot() -> dict:
        """Screenshot: Capture the current Windows desktop. Returns a base64
        PNG image and screen dimensions. Call this first to see what is on screen."""
        return _tools.screen_shot()

    @mcp.tool()
    def screen_describe() -> str:
        """Screen Describe: Ask the configured vision model to describe what is
        currently visible on the Windows desktop. Returns a text description
        with coordinates of interactive UI elements. Use when the calling AI
        cannot natively analyze images."""
        return _tools.screen_describe()

    @mcp.tool()
    def computer_observe(title: str | None = None) -> dict:
        """Observe: Return foreground window details and visible windows.
        This is read-only and should be called before risky mouse actions."""
        return _tools.computer_observe(title)

    @mcp.tool()
    def computer_uia_tree(
        title: str | None = None,
        max_depth: int = 3,
        max_nodes: int = 80,
    ) -> dict:
        """UIA Tree: Return a shallow Windows UI Automation control tree.
        Prefer this over visual coordinates when native controls are exposed."""
        return _tools.computer_uia_tree(title, max_depth, max_nodes)

    @mcp.tool()
    def computer_locate(selector: dict, title: str | None = None) -> dict:
        """Locate: Find a Windows UI element with a structured selector.
        Example selector: {'strategy':'uia','name':'OK','control_type':'Button'}."""
        return _tools.computer_locate(selector, title)

    # ── Actions ─────────────────────────────────────────────────
    @mcp.tool()
    def computer_click(x: int, y: int, button: str = "left") -> dict:
        """Click: Left/right/middle click at screen coordinates.
        Coordinates use the 1024x768 scaled space. Returns a new screenshot."""
        return _tools.computer_click(x, y, button)

    @mcp.tool()
    def computer_click_absolute(x: int, y: int, button: str = "left") -> dict:
        """Click Absolute: Click at absolute screen pixel coordinates.
        Use for coordinates from screen_describe_window after adding window left/top."""
        return _tools.computer_click_absolute(x, y, button)

    @mcp.tool()
    def computer_double_click(x: int, y: int) -> dict:
        """Double Click: Double-click at screen coordinates (1024x768 space).
        Returns a new screenshot."""
        return _tools.computer_double_click(x, y)

    @mcp.tool()
    def computer_move(x: int, y: int) -> dict:
        """Mouse Move: Move cursor to coordinates (1024x768 space).
        Returns a new screenshot."""
        return _tools.computer_move(x, y)

    @mcp.tool()
    def computer_type(text: str) -> dict:
        """Type: Simulate keyboard typing of the given text.
        Returns a new screenshot."""
        return _tools.computer_type(text)

    @mcp.tool()
    def computer_key(key: str) -> dict:
        """Key Press: Press a keyboard key (enter, escape, tab, ctrl+c, etc.).
        Returns a new screenshot."""
        return _tools.computer_key(key)

    @mcp.tool()
    def computer_scroll(direction: str, amount: int = 3) -> dict:
        """Scroll: Scroll mouse wheel. direction='up'/'down'/'left'/'right'.
        Returns a new screenshot."""
        return _tools.computer_scroll(direction, amount)

    @mcp.tool()
    def computer_drag(x1: int, y1: int, x2: int, y2: int) -> dict:
        """Drag: Drag from (x1,y1) to (x2,y2) in 1024x768 space.
        Returns a new screenshot."""
        return _tools.computer_drag(x1, y1, x2, y2)

    @mcp.tool()
    def computer_screenshot() -> dict:
        """Take a fresh screenshot. Same as screen_shot, use after actions
        to confirm the result."""
        return _tools.computer_screenshot()

    @mcp.tool()
    def computer_hotkey(keys: str) -> dict:
        """Key Combination: Press a key combination like 'ctrl+c', 'alt+tab', 'win+d'.
        Pass keys with '+' separator: e.g. 'ctrl+c', 'win+e', 'alt+tab'."""
        parts = [k.strip() for k in keys.split("+")]
        return _tools.computer_hotkey(*parts)

    @mcp.tool()
    def computer_focus_window(title: str) -> dict:
        """Focus Window: Bring a window to the foreground by its title.
        Returns {left, top, width, height} of the window in screen pixels.
        Use with computer_click_relative for in-window operations."""
        return _tools.computer_focus_window(title)

    @mcp.tool()
    def computer_click_relative(x_pct: float, y_pct: float) -> dict:
        """Click Relative: Click at percentage position inside the last focused window.
        (0.35, 0.88) = 35% from left, 88% from top. Call focus_window first."""
        return _tools.computer_click_relative(x_pct, y_pct)

    @mcp.tool()
    def computer_act(action: dict) -> dict:
        """Act: Run a guarded native action.
        Prefer {'type':'click','selector':{...}} over raw coordinates."""
        return _tools.computer_act(action)

    @mcp.tool()
    def computer_minimize_window(title: str) -> dict:
        """Minimize Window: Minimize the window with the given title."""
        return _tools.computer_minimize_window(title)

    @mcp.tool()
    def screen_describe_window(title: str) -> str:
        """Describe Window: Focus a window, capture its content, send to vision.
        Returns description with coordinates relative to window interior.
        Use with computer_focus_window to convert to screen clicks."""
        return _tools.screen_describe_window(title)

    @mcp.tool()
    def browser_open(url: str) -> dict:
        """Browser Open: Open a visible Chromium page via Playwright."""
        return _tools.browser_open(url)

    @mcp.tool()
    def browser_locate(selector: dict) -> dict:
        """Browser Locate: Find a DOM element via Playwright locators.
        Example: {'strategy':'role','role':'button','name':'Submit'}."""
        return _tools.browser_locate(selector)

    @mcp.tool()
    def browser_snapshot() -> dict:
        """Browser Snapshot: Read current page URL/title, focused element,
        visible inputs, buttons, disabled state, and usable CSS selectors.
        Use this before web actions when selector choice is uncertain."""
        return _tools.browser_snapshot()

    @mcp.tool()
    def browser_act(action: dict) -> dict:
        """Browser Act: Click, fill, type, press, or read text via DOM locators."""
        return _tools.browser_act(action)

    @mcp.tool()
    def browser_submit_prompt(
        text: str,
        input_selector: dict | None = None,
        submit_selector: dict | None = None,
        timeout_ms: int = 15000,
    ) -> dict:
        """Browser Submit Prompt: Fill a web prompt, submit it, and verify
        success via DOM state. Prefer this over coordinates for chat pages."""
        return _tools.browser_submit_prompt(
            text,
            input_selector,
            submit_selector,
            timeout_ms,
        )

    @mcp.tool()
    def browser_close() -> dict:
        """Browser Close: Close the active Playwright browser session."""
        return _tools.browser_close()

    return mcp


def _build_fallback_server():
    """Register tools via low-level MCP Server API."""
    if Server is None:
        raise ImportError(
            "mcp package is required. Install with: pip install 'mcp[cli]'"
        )

    server = Server("solo-cu")

    TOOLS = [
        ("screen_shot", _tools.screen_shot),
        ("screen_describe", _tools.screen_describe),
        ("computer_click", _tools.computer_click),
        ("computer_double_click", _tools.computer_double_click),
        ("computer_move", _tools.computer_move),
        ("computer_type", _tools.computer_type),
        ("computer_key", _tools.computer_key),
        ("computer_scroll", _tools.computer_scroll),
        ("computer_drag", _tools.computer_drag),
        ("computer_screenshot", _tools.computer_screenshot),
    ]

    # We can't easily use the low-level API with synchronous tools,
    # so if FastMCP fails, we recommend using FastMCP.
    # This fallback is reserved for future async tool support.
    raise NotImplementedError(
        "FastMCP is required. Install with: pip install 'mcp[cli]'"
    )


def main():
    """Entry point: start the MCP server on stdio."""
    if FastMCP is not None:
        logger.info("solo-cu MCP server starting (FastMCP)")
        try:
            mcp = _build_fastmcp()
            mcp.run(transport="stdio")
        except KeyboardInterrupt:
            logger.info("solo-cu MCP server stopped")
    else:
        logger.error(
            "FastMCP not available. "
            "Install mcp: pip install 'mcp[cli]'"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
