"""Playwright-backed browser automation helpers."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from .config import BROWSER_CHANNEL, BROWSER_HEADLESS

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_playwright: Any = None
_browser: Any = None
_context: Any = None
_page: Any = None


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
