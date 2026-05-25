"""Agent workflow rules — best practices for efficient computer use.

These rules are learned from real-world testing and optimization.
Import and inject them into agent tool descriptions where appropriate.
"""

AGENT_RULES = """
## Computer Use Efficiency Rules

### 1. Prefer bash over GUI for starting applications
Use `bash: Start-Process` to launch apps directly. Only use screen-based
clicks when the app cannot be started via command line.

### 2. Window focus before click
Always call `computer_focus_window(title)` before any click/type operation.
This brings the target window to the foreground and returns its exact bounds.

### 3. Use relative clicks inside windows
After `computer_focus_window`, use `computer_click_relative(x_pct, y_pct)`
instead of absolute coordinates. Percentages are resolution-independent and
don't break when windows move.

### 4. Chain operations in a single bash command when possible
Multiple steps (activate → click → type → send) should be run in ONE bash
command to avoid focus loss between tool calls. Only use individual MCP tools
when you need mid-step verification via screenshots.

### 5. Minimize screen_describe calls
`screen_describe` costs API tokens. Use it only when you need to LOCATE
unknown UI elements. Skip it when:
- The app layout is predictable (e.g., WeChat input is always at bottom)
- You already have window bounds from `computer_focus_window`
- You can click_relative with reasonable percentage estimates

### 6. Chinese text goes through clipboard
The `computer_type` tool automatically uses ctrl+v (pyperclip) for
non-ASCII text. No manual clipboard handling needed.

### 7. Atomic send: click send button, not keyboard enter
Keyboard focus is fragile. Clicking the send/confirm button with
`computer_click_relative` is more reliable than pressing Enter.

### 8. Minimize after use
Call `computer_minimize_window(title)` after finishing a task to restore
a clean desktop state.
"""
