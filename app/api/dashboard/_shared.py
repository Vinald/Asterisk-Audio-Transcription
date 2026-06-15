from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


def _caller_colors(caller_ids: list) -> dict:
    """Map each unique caller_id to a color index 0-7 for row highlighting."""
    seen: dict = {}
    for cid in caller_ids:
        key = cid or "unknown"
        if key not in seen:
            seen[key] = len(seen) % 8
    return seen


def _v(x):
    """Return empty string for None, otherwise the value as-is (for CSV rows)."""
    return "" if x is None else x
