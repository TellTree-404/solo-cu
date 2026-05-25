# Changelog

## 0.1.0 - 2026-05-25

Initial experimental release.

### Added

- MCP server for Windows Computer Use and Browser Use.
- Screenshot capture, screen description, mouse, keyboard, hotkey, scroll, drag,
  window focus, and window minimize tools.
- Windows observation helpers for foreground windows, visible windows, and UI
  Automation trees.
- UIA-based native control locator and guarded native action helper.
- Playwright-based browser tools for opening pages, locating DOM elements,
  acting on DOM locators, and closing browser sessions.
- Absolute pixel click tool for window-relative vision coordinates.
- Configurable OpenAI-compatible vision backend via `VISION_*` variables.
- Safer defaults for pyautogui failsafe and browser launch fallback.

### Verified

- MCP tool discovery returns 26 tools.
- Basic screenshot and window observation work on Windows.
- UIA tree inspection and non-ASCII text input work in Notepad.
- Browser DOM automation works through Playwright.
- A constrained messaging-app validation was performed against a self-owned file
  transfer conversation only.

### Known limitations

- Some Windows apps expose only shallow UIA trees.
- Vision coordinates are a fallback and should not be used as the sole authority.
- Raw mouse coordinates remain sensitive to focus changes and window movement.
- Browser bundled Chromium may require a separate Playwright runtime download;
  installed system Edge or Chrome can be used as fallback.

### Fixed after initial publication

- Corrected `screen_describe_window` click guidance to use absolute pixel clicks.
- Made relative clicks and text entry refocus the last focused window.
- Added configurable action delays and process DPI awareness.
- Registered browser tools synchronously for broader MCP client compatibility.
- Added DOM browser snapshots and verified prompt submission for web chat pages.
