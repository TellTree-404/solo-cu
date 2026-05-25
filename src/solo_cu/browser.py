"""Playwright-backed browser automation helpers."""

from __future__ import annotations

import asyncio
import threading
import time
from typing import Any

from .config import BROWSER_CHANNEL, BROWSER_HEADLESS

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_playwright: Any = None
_browser: Any = None
_context: Any = None
_page: Any = None


_SNAPSHOT_JS = r"""
() => {
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" &&
      style.display !== "none" &&
      rect.width > 0 &&
      rect.height > 0;
  };
  const cssString = (value) => {
    if (window.CSS && CSS.escape) {
      return CSS.escape(value);
    }
    return String(value).replace(/["\\]/g, "\\$&");
  };
  const selectorFor = (el) => {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }
    if (el.id) {
      return `#${cssString(el.id)}`;
    }
    const attrs = ["data-testid", "data-test", "data-cy", "aria-label", "name", "placeholder", "title"];
    for (const attr of attrs) {
      const value = el.getAttribute(attr);
      if (value) {
        return `${el.tagName.toLowerCase()}[${attr}="${cssString(value)}"]`;
      }
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
        if (same.length > 1) {
          part += `:nth-of-type(${same.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(" > ");
  };
  const textFor = (el) => {
    if (!el) {
      return "";
    }
    if ("value" in el && typeof el.value === "string") {
      return el.value;
    }
    return (el.innerText || el.textContent || "").trim();
  };
  const describe = (el) => {
    if (!el || el.nodeType !== Node.ELEMENT_NODE) {
      return null;
    }
    const rect = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute("type") || "",
      role: el.getAttribute("role") || "",
      name: el.getAttribute("name") || "",
      id: el.id || "",
      aria_label: el.getAttribute("aria-label") || "",
      title: el.getAttribute("title") || "",
      placeholder: el.getAttribute("placeholder") || "",
      text: textFor(el).slice(0, 240),
      disabled: Boolean(el.disabled || el.getAttribute("aria-disabled") === "true"),
      visible: isVisible(el),
      selector: selectorFor(el),
      bounding_box: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
    };
  };
  const inputSelector = [
    "textarea",
    "input:not([type='hidden'])",
    "[contenteditable='true']",
    "[role='textbox']"
  ].join(",");
  const buttonSelector = [
    "button",
    "[role='button']",
    "input[type='button']",
    "input[type='submit']"
  ].join(",");
  return {
    url: location.href,
    title: document.title,
    active_element: describe(document.activeElement),
    inputs: Array.from(document.querySelectorAll(inputSelector)).map(describe).filter(Boolean),
    buttons: Array.from(document.querySelectorAll(buttonSelector)).map(describe).filter(Boolean),
  };
}
"""


_FIND_PROMPT_INPUT_JS = r"""
() => {
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" &&
      style.display !== "none" &&
      rect.width > 0 &&
      rect.height > 0;
  };
  const cssString = (value) => {
    if (window.CSS && CSS.escape) {
      return CSS.escape(value);
    }
    return String(value).replace(/["\\]/g, "\\$&");
  };
  const selectorFor = (el) => {
    if (el.id) {
      return `#${cssString(el.id)}`;
    }
    const attrs = ["data-testid", "data-test", "data-cy", "aria-label", "name", "placeholder"];
    for (const attr of attrs) {
      const value = el.getAttribute(attr);
      if (value) {
        return `${el.tagName.toLowerCase()}[${attr}="${cssString(value)}"]`;
      }
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
        if (same.length > 1) {
          part += `:nth-of-type(${same.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(" > ");
  };
  const textFor = (el) => {
    if ("value" in el && typeof el.value === "string") {
      return el.value;
    }
    return (el.innerText || el.textContent || "").trim();
  };
  const badWords = ["search", "\u641c\u7d22"];
  const goodWords = ["prompt", "composer", "message", "chat", "\u6d88\u606f", "\u8f93\u5165"];
  const elements = Array.from(document.querySelectorAll(
    "textarea,input:not([type='hidden']),[contenteditable='true'],[role='textbox']"
  ));
  const candidates = elements
    .filter((el) => isVisible(el))
    .filter((el) => !el.disabled && el.getAttribute("aria-disabled") !== "true")
    .map((el) => {
      const rect = el.getBoundingClientRect();
      const haystack = [
        el.id,
        el.getAttribute("data-testid"),
        el.getAttribute("aria-label"),
        el.getAttribute("placeholder"),
        el.getAttribute("name"),
        el.getAttribute("role"),
      ].filter(Boolean).join(" ").toLowerCase();
      let score = rect.y + rect.width / 10;
      if (el === document.activeElement) {
        score += 1000;
      }
      if (goodWords.some((word) => haystack.includes(word))) {
        score += 500;
      }
      if (badWords.some((word) => haystack.includes(word))) {
        score -= 1200;
      }
      if (rect.width < 160) {
        score -= 300;
      }
      return {
        selector: selectorFor(el),
        score,
        text: textFor(el).slice(0, 200),
        bounding_box: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
      };
    })
    .sort((a, b) => b.score - a.score);
  return {chosen: candidates[0] || null, candidates};
}
"""


_FIND_SUBMIT_BUTTON_JS = r"""
(inputSelector) => {
  const input = inputSelector ? document.querySelector(inputSelector) : document.activeElement;
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.visibility !== "hidden" &&
      style.display !== "none" &&
      rect.width > 0 &&
      rect.height > 0;
  };
  const cssString = (value) => {
    if (window.CSS && CSS.escape) {
      return CSS.escape(value);
    }
    return String(value).replace(/["\\]/g, "\\$&");
  };
  const selectorFor = (el) => {
    if (el.id) {
      return `#${cssString(el.id)}`;
    }
    const attrs = ["data-testid", "data-test", "data-cy", "aria-label", "name", "title"];
    for (const attr of attrs) {
      const value = el.getAttribute(attr);
      if (value) {
        return `${el.tagName.toLowerCase()}[${attr}="${cssString(value)}"]`;
      }
    }
    const parts = [];
    let node = el;
    while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
        if (same.length > 1) {
          part += `:nth-of-type(${same.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(" > ");
  };
  const textFor = (el) => ("value" in el && typeof el.value === "string")
    ? el.value
    : (el.innerText || el.textContent || "").trim();
  const inputRect = input && input.getBoundingClientRect ? input.getBoundingClientRect() : null;
  const submitWords = ["send", "submit", "prompt", "\u53d1\u9001", "\u63d0\u4ea4"];
  const stopWords = ["stop", "cancel", "\u505c\u6b62", "\u53d6\u6d88"];
  const elements = Array.from(document.querySelectorAll(
    "button,[role='button'],input[type='button'],input[type='submit']"
  ));
  const candidates = elements
    .filter((el) => isVisible(el))
    .map((el) => {
      const rect = el.getBoundingClientRect();
      const haystack = [
        el.id,
        el.getAttribute("data-testid"),
        el.getAttribute("aria-label"),
        el.getAttribute("title"),
        el.getAttribute("name"),
        textFor(el),
      ].filter(Boolean).join(" ").toLowerCase();
      const disabled = Boolean(el.disabled || el.getAttribute("aria-disabled") === "true");
      let score = 0;
      if (submitWords.some((word) => haystack.includes(word))) {
        score += 1000;
      }
      if (stopWords.some((word) => haystack.includes(word))) {
        score -= 1000;
      }
      if (inputRect) {
        const nearVertically = Math.abs((rect.y + rect.height / 2) - (inputRect.y + inputRect.height / 2));
        const nearHorizontally = Math.abs((rect.x + rect.width / 2) - (inputRect.x + inputRect.width));
        score += Math.max(0, 500 - nearVertically);
        score += Math.max(0, 300 - nearHorizontally / 2);
        if (rect.x >= inputRect.x && rect.y >= inputRect.y - 20) {
          score += 150;
        }
      }
      if (disabled) {
        score -= 2000;
      }
      return {
        selector: selectorFor(el),
        score,
        disabled,
        text: textFor(el).slice(0, 120),
        aria_label: el.getAttribute("aria-label") || "",
        title: el.getAttribute("title") || "",
        bounding_box: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
      };
    })
    .sort((a, b) => b.score - a.score);
  return {chosen: candidates.find((candidate) => !candidate.disabled && candidate.score > 0) || null, candidates};
}
"""


_VERIFY_SUBMIT_JS = r"""
({inputSelector, submittedText}) => {
  const input = inputSelector ? document.querySelector(inputSelector) : document.activeElement;
  const editableText = input
    ? (("value" in input && typeof input.value === "string")
        ? input.value
        : (input.innerText || input.textContent || ""))
    : "";
  const inputCleared = editableText.trim().length === 0;
  const containsSubmittedOutsideInput = Array.from(document.querySelectorAll(
    "main,[role='main'],article,[data-message-author-role='user'],[data-testid*='conversation'],[class*='conversation']"
  )).some((el) => {
    if (input && el.contains(input)) {
      return false;
    }
    return (el.innerText || el.textContent || "").includes(submittedText);
  });
  const busySelector = [
    "button[data-testid='stop-button']",
    "button[aria-label*='Stop']",
    "button[aria-label*='\u505c\u6b62']",
    "[data-testid*='streaming']",
    "[aria-busy='true']"
  ].join(",");
  const assistantBusy = Boolean(document.querySelector(busySelector));
  return {
    input_text: editableText.slice(0, 500),
    input_cleared: inputCleared,
    message_visible_outside_input: containsSubmittedOutsideInput,
    assistant_busy: assistantBusy,
    sent: inputCleared || containsSubmittedOutsideInput || assistantBusy,
  };
}
"""


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop, _thread
    if _loop and _loop.is_running():
        return _loop

    ready = threading.Event()
    _loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(_loop)
        ready.set()
        _loop.run_forever()

    _thread = threading.Thread(target=_run, name="solo-cu-playwright", daemon=True)
    _thread.start()
    ready.wait(timeout=5)
    return _loop


def _run_async(coro: Any) -> Any:
    loop = _ensure_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop).result()


async def _ensure_page() -> Any:
    global _playwright, _browser, _context, _page
    if _page is not None:
        return _page
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed. Install project dependencies first."
        ) from exc

    _playwright = await async_playwright().start()
    launch_errors = []
    channels = [BROWSER_CHANNEL] if BROWSER_CHANNEL else [None, "msedge", "chrome"]
    for channel in channels:
        try:
            kwargs = {"headless": BROWSER_HEADLESS}
            if channel:
                kwargs["channel"] = channel
            _browser = await _playwright.chromium.launch(**kwargs)
            break
        except Exception as exc:
            launch_errors.append(f"{channel or 'bundled chromium'}: {exc}")
    if _browser is None:
        raise RuntimeError(
            "Unable to launch Playwright browser. Install Chromium with "
            "`python -m playwright install chromium` or install Microsoft Edge/Chrome. "
            + " | ".join(launch_errors)
        )
    _context = await _browser.new_context()
    _page = await _context.new_page()
    return _page


def _locator(page: Any, selector: dict) -> Any:
    strategy = selector.get("strategy", "dom")
    if strategy == "role":
        role = selector["role"]
        name = selector.get("name")
        return page.get_by_role(role, name=name) if name else page.get_by_role(role)
    if strategy == "text":
        return page.get_by_text(selector["text"])
    if strategy == "label":
        return page.get_by_label(selector["label"])
    if strategy == "placeholder":
        return page.get_by_placeholder(selector["placeholder"])
    if strategy == "css":
        return page.locator(selector["css"])
    if strategy == "dom":
        if "role" in selector:
            role = selector["role"]
            name = selector.get("name")
            return page.get_by_role(role, name=name) if name else page.get_by_role(role)
        if "text" in selector:
            return page.get_by_text(selector["text"])
        if "css" in selector:
            return page.locator(selector["css"])
    raise ValueError(f"Unsupported browser selector: {selector!r}")


async def _read_editable_text(locator: Any) -> str:
    return await locator.evaluate(
        """(el) => {
            if ("value" in el && typeof el.value === "string") {
                return el.value;
            }
            return el.innerText || el.textContent || "";
        }"""
    )


async def _element_css_selector(locator: Any) -> str | None:
    return await locator.evaluate(
        r"""(el) => {
            if (!el || el.nodeType !== Node.ELEMENT_NODE) {
                return null;
            }
            const cssString = (value) => {
                if (window.CSS && CSS.escape) {
                    return CSS.escape(value);
                }
                return String(value).replace(/["\\]/g, "\\$&");
            };
            if (el.id) {
                return `#${cssString(el.id)}`;
            }
            const attrs = ["data-testid", "data-test", "data-cy", "aria-label", "name", "placeholder", "title"];
            for (const attr of attrs) {
                const value = el.getAttribute(attr);
                if (value) {
                    return `${el.tagName.toLowerCase()}[${attr}="${cssString(value)}"]`;
                }
            }
            const parts = [];
            let node = el;
            while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 5) {
                let part = node.tagName.toLowerCase();
                const parent = node.parentElement;
                if (parent) {
                    const same = Array.from(parent.children).filter((child) => child.tagName === node.tagName);
                    if (same.length > 1) {
                        part += `:nth-of-type(${same.indexOf(node) + 1})`;
                    }
                }
                parts.unshift(part);
                node = parent;
            }
            return parts.join(" > ");
        }"""
    )


async def _find_prompt_input(page: Any) -> dict:
    return await page.evaluate(_FIND_PROMPT_INPUT_JS)


async def _find_submit_button(page: Any, input_selector: str) -> dict:
    return await page.evaluate(_FIND_SUBMIT_BUTTON_JS, input_selector)


async def _verify_submit(page: Any, input_selector: str, submitted_text: str) -> dict:
    return await page.evaluate(
        _VERIFY_SUBMIT_JS,
        {"inputSelector": input_selector, "submittedText": submitted_text},
    )


async def _open_url_async(url: str, wait_until: str = "domcontentloaded") -> dict:
    page = await _ensure_page()
    await page.goto(url, wait_until=wait_until)
    return {"ok": True, "url": page.url, "title": await page.title()}


def open_url(url: str, wait_until: str = "domcontentloaded") -> dict:
    return _run_async(_open_url_async(url, wait_until))


async def _locate_async(selector: dict) -> dict:
    try:
        page = await _ensure_page()
        loc = _locator(page, selector)
        count = await loc.count()
        first = loc.first if count else None
        box = await first.bounding_box() if first else None
        return {
            "ok": count > 0,
            "selector": selector,
            "count": count,
            "first": {"bounding_box": box} if box else None,
            "url": page.url,
            "title": await page.title(),
            "error": "" if count else "No DOM locator matched the selector.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "selector": selector,
            "error": "DOM locator failed.",
            "detail": str(exc),
        }


def locate(selector: dict) -> dict:
    return _run_async(_locate_async(selector))


async def _snapshot_async() -> dict:
    try:
        page = await _ensure_page()
        snapshot = await page.evaluate(_SNAPSHOT_JS)
        snapshot["ok"] = True
        return snapshot
    except Exception as exc:
        return {
            "ok": False,
            "error": "Browser snapshot failed.",
            "detail": str(exc),
        }


def snapshot() -> dict:
    return _run_async(_snapshot_async())


async def _act_async(action: dict) -> dict:
    """Run a DOM action. Supported types: click, fill, type, press, read_text."""
    try:
        page = await _ensure_page()
        action_type = action.get("type")
        selector = action.get("selector")
        loc = _locator(page, selector).first if selector else None

        if action_type == "click":
            await loc.click()
            result = None
        elif action_type == "fill":
            await loc.fill(action.get("text", ""))
            result = None
        elif action_type == "type":
            await loc.type(action.get("text", ""))
            result = None
        elif action_type == "press":
            target = loc if loc is not None else page
            await target.press(action["key"])
            result = None
        elif action_type == "read_text":
            result = await loc.inner_text()
        else:
            raise ValueError(f"Unsupported browser action type: {action_type!r}")

        return {
            "ok": True,
            "action": action,
            "result": result,
            "url": page.url,
            "title": await page.title(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "action": action,
            "error": "Browser action failed.",
            "detail": str(exc),
        }


def act(action: dict) -> dict:
    return _run_async(_act_async(action))


async def _submit_prompt_async(
    text: str,
    input_selector: dict | None = None,
    submit_selector: dict | None = None,
    timeout_ms: int = 15000,
) -> dict:
    """Fill a browser prompt, submit it, and verify that it was sent."""
    started = time.monotonic()
    try:
        page = await _ensure_page()
        if not text:
            return {"ok": False, "sent": False, "error": "Text must not be empty."}

        input_diagnostics = None
        if input_selector:
            raw_input_loc = _locator(page, input_selector)
            input_loc = raw_input_loc.first
            count = await raw_input_loc.count()
            if count < 1:
                return {
                    "ok": False,
                    "sent": False,
                    "error": "Input selector did not match any element.",
                    "input_selector": input_selector,
                }
            input_selector_text = await _element_css_selector(input_loc)
        else:
            input_diagnostics = await _find_prompt_input(page)
            chosen_input = input_diagnostics.get("chosen")
            if not chosen_input or not chosen_input.get("selector"):
                return {
                    "ok": False,
                    "sent": False,
                    "error": "No visible editable prompt input was found.",
                    "diagnostics": input_diagnostics,
                    "url": page.url,
                    "title": await page.title(),
                }
            input_selector_text = chosen_input["selector"]
            input_loc = page.locator(input_selector_text).first

        if not input_selector_text:
            return {
                "ok": False,
                "sent": False,
                "error": "Submit verification requires a CSS input selector.",
                "input_selector": input_selector,
            }

        await input_loc.scroll_into_view_if_needed(timeout=timeout_ms)
        await input_loc.click(timeout=timeout_ms)
        before_text = await _read_editable_text(input_loc)
        try:
            await input_loc.fill(text, timeout=timeout_ms)
        except Exception:
            await page.keyboard.press("Control+A")
            await page.keyboard.insert_text(text)

        filled_text = await _read_editable_text(input_loc)
        if text not in filled_text:
            return {
                "ok": False,
                "sent": False,
                "error": "Prompt text was not present after filling the input.",
                "input_selector": input_selector_text,
                "before_text": before_text[:500],
                "after_text": filled_text[:500],
                "url": page.url,
                "title": await page.title(),
            }

        submit_diagnostics = None
        if submit_selector:
            raw_submit_loc = _locator(page, submit_selector)
            submit_loc = raw_submit_loc.first
            submit_count = await raw_submit_loc.count()
            if submit_count < 1:
                return {
                    "ok": False,
                    "sent": False,
                    "error": "Submit selector did not match any element.",
                    "submit_selector": submit_selector,
                }
            submit_selector_text = await _element_css_selector(submit_loc)
        else:
            submit_diagnostics = await _find_submit_button(page, input_selector_text)
            chosen_submit = submit_diagnostics.get("chosen")
            if not chosen_submit or not chosen_submit.get("selector"):
                return {
                    "ok": False,
                    "sent": False,
                    "error": "No enabled submit button was found near the prompt input.",
                    "input_selector": input_selector_text,
                    "diagnostics": submit_diagnostics,
                    "url": page.url,
                    "title": await page.title(),
                }
            submit_selector_text = chosen_submit["selector"]
            submit_loc = page.locator(submit_selector_text).first

        await submit_loc.scroll_into_view_if_needed(timeout=timeout_ms)
        await submit_loc.click(timeout=timeout_ms)

        deadline = started + timeout_ms / 1000
        last_check: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last_check = await _verify_submit(page, input_selector_text, text)
            if last_check.get("sent"):
                return {
                    "ok": True,
                    "sent": True,
                    "input_selector": input_selector_text,
                    "submit_selector": submit_selector_text,
                    "checks": last_check,
                    "input_diagnostics": input_diagnostics,
                    "submit_diagnostics": submit_diagnostics,
                    "url": page.url,
                    "title": await page.title(),
                }
            await page.wait_for_timeout(250)

        return {
            "ok": False,
            "sent": False,
            "error": "Submit could not be verified before timeout.",
            "input_selector": input_selector_text,
            "submit_selector": submit_selector_text,
            "checks": last_check,
            "input_diagnostics": input_diagnostics,
            "submit_diagnostics": submit_diagnostics,
            "url": page.url,
            "title": await page.title(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "sent": False,
            "error": "Browser prompt submit failed.",
            "detail": str(exc),
        }


def submit_prompt(
    text: str,
    input_selector: dict | None = None,
    submit_selector: dict | None = None,
    timeout_ms: int = 15000,
) -> dict:
    return _run_async(_submit_prompt_async(text, input_selector, submit_selector, timeout_ms))


async def _close_async() -> dict:
    """Close the Playwright browser session if one is open."""
    global _playwright, _browser, _context, _page
    try:
        if _page is not None:
            await _page.close()
        if _context is not None:
            await _context.close()
        if _browser is not None:
            await _browser.close()
        if _playwright is not None:
            await _playwright.stop()
        return {"ok": True, "action": "browser_close"}
    finally:
        _page = None
        _context = None
        _browser = None
        _playwright = None


def close() -> dict:
    return _run_async(_close_async())
