"""Pure keyword matching - no Home Assistant imports, fully unit-testable."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
import unicodedata


@dataclass(frozen=True, slots=True)
class Match:
    """A keyword that was found in one of the searched attributes."""

    keyword: str
    field: str


def normalize(value: Any) -> str:
    """Normalise a value for case-insensitive comparison.

    NFKC folds look-alike characters (full-width letters, ligatures), casefold
    is a stronger ``lower()`` (``ß`` == ``ss``), and surrounding whitespace is
    dropped - the original automation trimmed every attribute as well.
    """
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).casefold().strip()


def parse_keywords(raw: str | Iterable[str] | None) -> list[str]:
    """Turn user input into a clean keyword list.

    Accepts the multi-line text of the config form (one keyword per line) or
    an already split list. Blank lines are dropped, surrounding whitespace is
    removed and duplicates (case-insensitive) are kept only once, in the order
    they were entered.
    """
    if raw is None:
        return []
    lines = raw.splitlines() if isinstance(raw, str) else [str(item) for item in raw]
    result: list[str] = []
    seen: set[str] = set()
    for line in lines:
        keyword = line.strip()
        key = normalize(keyword)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(keyword)
    return result


def keywords_to_text(keywords: Iterable[str]) -> str:
    """Render a keyword list for the multi-line form field."""
    return "\n".join(keywords)


def find_match(
    attributes: Mapping[str, Any], keywords: Iterable[str], fields: Iterable[str]
) -> Match | None:
    """Return the first keyword contained in one of ``fields``, else ``None``.

    Keywords are compared as case-insensitive substrings, so ``tkkg`` matches
    the album "TKKG Folge 200" and ``???`` matches "Die drei ???". Keywords are
    checked in list order; the first hit wins.
    """
    values = [(field, normalize(attributes.get(field))) for field in fields]
    values = [(field, value) for field, value in values if value]
    if not values:
        return None
    for keyword in keywords:
        needle = normalize(keyword)
        if not needle:
            continue
        for field, value in values:
            if needle in value:
                return Match(keyword=keyword, field=field)
    return None
