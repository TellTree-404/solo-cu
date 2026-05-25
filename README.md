# solo-cu

> Computer Use and Browser Use MCP Server for Windows

**Status:** v0.1.0 experimental. This project is usable as an early MCP server,
but it is not a fully reliable general-purpose Computer Use framework yet.

Let AI agents (Codex Desktop/CLI, OpenCode, Claude Code, Cursor, Hermes Agent)
**observe and control** Windows apps through MCP. It prefers structured
automation (UI Automation and Playwright DOM locators) and keeps screenshots and
mouse coordinates as fallbacks.

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Optional: set a vision API key for screen_describe fallback
set VISION_API_KEY=your-vision-api-key   # Windows CMD
# or
$env:VISION_API_KEY="your-vision-api-key"  # PowerShell

# 3. Run MCP server
python -m solo_cu.mcp_server
```

## Connect to Your AI Tool

### OpenCode

Copy `config.example.json` to `.opencode/mcp.json` and fill in your API key.

### Claude Code

```bash
claude mcp add solo-cu -- python -m solo_cu.mcp_server
```

### Codex Desktop / CLI

```bash
codex mcp add solo-cu -- python -m solo_cu.mcp_server
```

### Cursor / Hermes / Other

Configure as a stdio MCP server — see `config.example.json` for the template.

## Tools (26 total)

| Tool | Description |
|------|-------------|
| `screen_shot` | Capture desktop as base64 PNG |
| `screen_describe` | Vision fallback describes what's on screen |
| `screen_describe_window` | Focus and describe one window |
| `computer_observe` | Read foreground and visible windows |
| `computer_uia_tree` | Read a Windows UI Automation tree |
| `computer_locate` | Locate native controls with structured selectors |
| `computer_act` | Guarded native action using selectors or fallback coordinates |
| `computer_click` | Low-level click at scaled (x, y) |
| `computer_click_absolute` | Low-level click at absolute screen pixels |
| `computer_double_click` | Low-level double-click |
| `computer_move` | Low-level cursor move |
| `computer_type` | Type text, using clipboard paste for non-ASCII |
| `computer_key` | Press key or key combination |
| `computer_hotkey` | Press key combination |
| `computer_scroll` | Scroll mouse wheel |
| `computer_drag` | Low-level drag |
| `computer_focus_window` | Bring a window to foreground by title |
| `computer_click_relative` | Low-level percentage click in active window |
| `computer_minimize_window` | Minimize a window by title |
| `computer_screenshot` | Take fresh screenshot |
| `browser_open` | Open a visible Chromium page via Playwright |
| `browser_locate` | Locate DOM elements with Playwright |
| `browser_snapshot` | Read page URL/title, focused element, inputs, and buttons |
| `browser_act` | Click/fill/type/press/read via DOM locators |
| `browser_submit_prompt` | Fill, submit, and verify a web chat prompt |
| `browser_close` | Close the active Playwright browser session |

## How It Works

```
AI Agent (OpenCode/Claude/etc.)
    │ MCP protocol
    ▼
solo-cu MCP Server
    ├── browser_* → Playwright DOM automation
    ├── computer_uia_tree / computer_locate → Windows UI Automation
    ├── screen_shot / screen_describe → screenshot and vision fallback
    └── low-level computer_* → pyautogui mouse/keyboard fallback
```

All coordinates use a 1024x768 scaled space (following Anthropic's best practice) and are automatically mapped to your actual screen resolution.

## Configuration

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `VISION_API_KEY` | empty | OpenAI-compatible vision API key |
| `VISION_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Vision API endpoint |
| `VISION_MODEL` | `qwen3-vl-flash` | Vision model ID |
| `SOLO_CU_WIDTH` | `1024` | Target screenshot width |
| `SOLO_CU_HEIGHT` | `768` | Target screenshot height |
| `SOLO_CU_FAILSAFE` | `true` | Enable pyautogui corner abort |
| `SOLO_CU_ACTION_DELAY` | `0.3` | Delay spread across ASCII typing |
| `SOLO_CU_SETTLE_DELAY` | `0.8` | Delay after mouse/keyboard actions |
| `SOLO_CU_FOCUS_SETTLE_DELAY` | `0.6` | Delay after bringing a window forward |
| `SOLO_CU_TYPE_PRE_DELAY` | `0.15` | Delay before typing or clipboard paste |
| `SOLO_CU_BROWSER_CHANNEL` | empty | Optional Playwright channel, e.g. `msedge` |
| `SOLO_CU_BROWSER_HEADLESS` | `false` | Run Playwright browser without a visible window |

Legacy `MIMO_API_KEY`, `MIMO_BASE_URL`, and `MIMO_MODEL` are still accepted as
fallbacks, but new configs should use `VISION_*`.

## Safety

- `pyautogui.FAILSAFE = True` — move mouse to any corner to abort
- All coordinates validated and clamped to screen bounds
- Prefer UIA/DOM locators before mouse coordinates
- Browser automation should use Playwright DOM locators first. For chat-style
  pages, prefer `browser_submit_prompt` because it verifies that the prompt was
  submitted instead of assuming a click worked.
- Native Windows apps should use UI Automation first
- Screenshot, vision, and raw mouse coordinates are fallbacks, not the primary path
- `screen_describe_window` returns window-relative pixels; convert them to
  absolute screen pixels and use `computer_click_absolute`
- Recommend running in a VM for untrusted tasks
- Never commit API keys to git

## Privacy

Do not commit `.env`, screenshots, chat logs, contact lists, browser profiles, or
local Codex configuration backups. Desktop automation screenshots can contain
private names, messages, and API keys. Keep manual validation artifacts outside
Git or under ignored folders such as `manual_tests/` and `backup/`.

## Known Limits

- Some desktop apps, including Qt-based messaging clients, expose only shallow
  UI Automation trees. Those apps may still need vision-assisted confirmation.
- Vision model coordinates are not trusted as the only source of truth.
- Focus can move between MCP calls in desktop automation. Prefer guarded actions
  and app-specific atomic workflows for risky tasks.
- Most MCP clients do not hot-reload tool definitions. Restart the client or MCP
  server after upgrading solo-cu if new tools do not appear.
- Messaging app automation is a validation scenario only. It is not guaranteed
  across client versions and should not be used for untrusted or irreversible
  actions without human confirmation.

## License

MIT
