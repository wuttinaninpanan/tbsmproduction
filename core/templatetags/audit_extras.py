from __future__ import annotations

import json
from typing import Any

from django import template

register = template.Library()


@register.filter
def pretty_json(value: Any) -> str:
    """Render a Python object (typically JSONField) as pretty JSON for templates."""

    if value in (None, ""):
        return ""

    try:
        if isinstance(value, (dict, list)) and not value:
            return ""

        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
    except Exception:
        return str(value)
