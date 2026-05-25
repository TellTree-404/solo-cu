"""Agent workflow rules — best practices for efficient computer use.

These rules are learned from real-world testing and optimization.
Import and inject them into agent tool descriptions where appropriate.
"""

AGENT_RULES = """
## Computer Use and Browser Use Efficiency Rules

### 1. Prefer structured automation over coordinates
For web pages, use `browser_open`, `browser_locate`, and `browser_act` with
DOM locators first. For native Windows apps, call `computer_observe`,
`computer_uia_tree`, or `computer_locate` before using mouse coordinates.

### 2. Use screenshots and vision as fallbacks
Use `screen_describe` or `screen_describe_window` only when UIA/DOM cannot
identify the target. Treat vision coordinates as suggestions that need
confirmation, not as the sole authority for risky clicks.

### 3. Focus and verify the target window
Call `computer_focus_window(title)` before native app actions, then confirm
the active window with `computer_observe` when focus drift would be risky.
Avoid clicking if the foreground window is not the intended app.

### 4. Prefer guarded actions
Use `computer_act` with a UIA selector when possible. Use raw
`computer_click`, `computer_click_relative`, `computer_click_absolute`, or
`computer_drag` only as low-level fallbacks after the target has been verified.
If `screen_describe_window` returns window-relative coordinates, add the window
left/top and call `computer_click_absolute`.

### 5. Keep multi-step desktop actions atomic
Focus can change between MCP calls. For fragile app workflows, combine
focus, locate, type, send, and post-check in one guarded action or app-specific
adapter instead of many independent clicks.

### 6. Non-ASCII text goes through clipboard
The `computer_type` tool automatically pastes non-ASCII text through the
clipboard. Confirm the input field is focused before typing.

### 7. Never continue through uncertainty
If a dialog, login screen, permission prompt, or unexpected foreground window
appears, stop and report it. Do not guess through popups.

### 8. Minimize or close transient windows after use
Call `computer_minimize_window(title)` or `browser_close` after finishing a
task when leaving the desktop clean matters.
"""
