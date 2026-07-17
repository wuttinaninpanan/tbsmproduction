"""Sanitize staff-authored WYSIWYG HTML (the Manual ``detail`` field).

The manual editor lets staff produce rich HTML that is later rendered with
``|safe``. Even though authors are trusted staff, an XSS planted there executes
for *every* reader, so we scrub the markup through nh3 (Rust/ammonia) — keeping
the formatting and embedded images the editor produces, while dropping
``<script>``, event-handler attributes and ``javascript:``/``data:`` links.
"""
from __future__ import annotations

import nh3

# Tags the WYSIWYG editor legitimately emits (text formatting, lists, tables,
# images, headings). Anything not listed (script/iframe/object/embed/form/...)
# is stripped by nh3.
_ALLOWED_TAGS: set[str] = {
    "a", "abbr", "b", "blockquote", "br", "caption", "code", "col", "colgroup",
    "div", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "img", "li", "mark", "ol", "p", "pre", "s", "small", "span",
    "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead",
    "tr", "u", "ul",
}

_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "*": {"class", "style", "align", "title"},
    "a": {"href", "target"},  # "rel" is managed by link_rel below
    "img": {"src", "alt", "width", "height"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
    "col": {"span"},
    "colgroup": {"span"},
}

# ``data:`` is allowed so the editor's embedded (base64) images survive; it is
# blocked on <a href> below so a data:text/html link can't be planted.
_ALLOWED_URL_SCHEMES: set[str] = {"http", "https", "mailto", "data"}


def _attribute_filter(tag: str, attr: str, value: str) -> str | None:
    low = value.strip().lower()
    # Never let a navigable link carry a data:/javascript: payload.
    if attr == "href" and low.startswith(("data:", "javascript:", "vbscript:")):
        return None
    if attr == "src" and low.startswith(("javascript:", "vbscript:")):
        return None
    return value


def sanitize_manual_html(html: str | None) -> str:
    """Return a safe-to-render version of ``html`` (empty string for falsy input)."""
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        attribute_filter=_attribute_filter,
        link_rel="noopener noreferrer",
    )
