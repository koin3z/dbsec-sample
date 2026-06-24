"""Conservative SELECT-only validation for the demo query panel."""

from __future__ import annotations

import re


class UnsafeSqlError(ValueError):
    """Raised when a SQL string is outside the demo's SELECT-only boundary."""


_START_RE = re.compile(r"^\s*(select|with)\b", re.IGNORECASE | re.DOTALL)
_UNSAFE_KEYWORDS_RE = re.compile(
    r"\b("
    r"insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|"
    r"begin|declare|execute|exec|call|commit|rollback"
    r")\b",
    re.IGNORECASE,
)


def normalize_select_sql(sql: str) -> str:
    """Return a cleaned single SELECT/WITH statement or raise UnsafeSqlError."""
    text = sql.strip()
    if not text:
        raise UnsafeSqlError("SQL is empty.")

    if "--" in text or "/*" in text or "*/" in text:
        raise UnsafeSqlError("SQL comments are not allowed in the demo query panel.")

    if text.endswith(";"):
        text = text[:-1].rstrip()

    if ";" in text:
        raise UnsafeSqlError("Multiple SQL statements are not allowed.")

    if not _START_RE.match(text):
        raise UnsafeSqlError("Only SELECT or WITH queries are allowed.")

    match = _UNSAFE_KEYWORDS_RE.search(text)
    if match:
        raise UnsafeSqlError(f"Keyword {match.group(1).upper()} is not allowed.")

    return text
