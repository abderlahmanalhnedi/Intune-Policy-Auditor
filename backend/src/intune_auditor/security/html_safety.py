"""Small explicit HTML escaping boundary used by report renderers."""

from html import escape


def safe_html(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)
