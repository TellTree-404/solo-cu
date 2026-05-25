"""Windows UI Automation helpers.

UIA gives agents a structured view of native Windows apps. It should be tried
before screenshot-based coordinates whenever the target app exposes controls.
"""

from __future__ import annotations

from typing import Any

from . import computer


def _rect_to_dict(rect: Any) -> dict:
    try:
        left = int(rect.left)
        top = int(rect.top)
        right = int(rect.right)
        bottom = int(rect.bottom)
    except Exception:
        return {"left": 0, "top": 0, "width": 0, "height": 0}
    return {
        "left": left,
        "top": top,
        "width": max(0, right - left),
        "height": max(0, bottom - top),
    }


def _control_to_dict(control: Any, depth: int) -> dict:
    info = getattr(control, "element_info", None)
    rect = _rect_to_dict(getattr(info, "rectangle", None))
    return {
        "name": getattr(info, "name", "") or "",
        "control_type": getattr(info, "control_type", "") or "",
        "automation_id": getattr(info, "automation_id", "") or "",
        "class_name": getattr(info, "class_name", "") or "",
        "handle": getattr(info, "handle", None),
        "depth": depth,
        "bounds": rect,
    }


def inspect_window(title: str | None = None, max_depth: int = 3, max_nodes: int = 80) -> dict:
    """Return a shallow UIA control tree for a window or foreground app."""
    try:
        from pywinauto import Desktop
    except ImportError as exc:
        return {
            "ok": False,
            "error": "pywinauto is not installed. Install project dependencies first.",
            "detail": str(exc),
        }

    try:
        if title:
            bounds = computer.focus_window(title)
            root = Desktop(backend="uia").window(handle=bounds["hwnd"])
        else:
            active = computer.active_window()
            root = Desktop(backend="uia").window(handle=active["hwnd"])
    except Exception as exc:
        return {"ok": False, "error": "Unable to attach to target window.", "detail": str(exc)}

    nodes: list[dict] = []

    def walk(control: Any, depth: int) -> None:
        if len(nodes) >= max_nodes or depth > max_depth:
            return
        nodes.append(_control_to_dict(control, depth))
        if depth == max_depth:
            return
        try:
            children = control.children()
        except Exception:
            return
        for child in children:
            walk(child, depth + 1)
            if len(nodes) >= max_nodes:
                return

    try:
        walk(root, 0)
        return {
            "ok": True,
            "target": title or "foreground",
            "max_depth": max_depth,
            "node_count": len(nodes),
            "nodes": nodes,
        }
    except Exception as exc:
        return {"ok": False, "error": "Unable to read UIA tree.", "detail": str(exc)}


def locate(selector: dict, title: str | None = None, max_depth: int = 5, max_nodes: int = 300) -> dict:
    """Locate controls by UIA fields and return matching candidates."""
    tree = inspect_window(title=title, max_depth=max_depth, max_nodes=max_nodes)
    if not tree.get("ok"):
        return tree

    name = str(selector.get("name", "")).lower()
    control_type = str(selector.get("control_type", "")).lower()
    automation_id = str(selector.get("automation_id", "")).lower()

    matches = []
    for node in tree["nodes"]:
        if name and name not in node["name"].lower():
            continue
        if control_type and control_type != node["control_type"].lower():
            continue
        if automation_id and automation_id != node["automation_id"].lower():
            continue
        bounds = node["bounds"]
        matches.append(
            {
                **node,
                "center": {
                    "x": bounds["left"] + bounds["width"] // 2,
                    "y": bounds["top"] + bounds["height"] // 2,
                },
                "source": "uia",
                "confidence": 0.95,
            }
        )

    return {
        "ok": bool(matches),
        "selector": selector,
        "target": title or "foreground",
        "count": len(matches),
        "matches": matches,
        "error": "" if matches else "No UIA controls matched the selector.",
    }
