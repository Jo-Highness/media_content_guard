"""Describe Media Content Guard events in the logbook."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.logbook import (
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    ATTR_MATCHED_KEYWORD,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_TITLE,
    ATTR_RULE_NAME,
    DOMAIN,
    EVENT_BLOCKED,
)

# The logbook API takes plain text, not translation keys - so the few
# messages are kept here, keyed by the Home Assistant UI language.
_MESSAGES: dict[str, tuple[str, str]] = {
    # (with title, without title)
    "de": (
        "hat „{title}“ gestoppt (Stichwort: {keyword})",
        "hat die Wiedergabe gestoppt (Stichwort: {keyword})",
    ),
    "en": ("stopped “{title}” (keyword: {keyword})", "stopped playback (keyword: {keyword})"),
    "es": (
        "detuvo «{title}» (palabra clave: {keyword})",
        "detuvo la reproducción (palabra clave: {keyword})",
    ),
    "fr": (
        "a arrêté « {title} » (mot-clé : {keyword})",
        "a arrêté la lecture (mot-clé : {keyword})",
    ),
}


def _message(language: str | None, title: str, keyword: str) -> str:
    lang = (language or "en").replace("_", "-").split("-")[0].casefold()
    with_title, without_title = _MESSAGES.get(lang, _MESSAGES["en"])
    if title:
        return with_title.format(title=title, keyword=keyword)
    return without_title.format(keyword=keyword)


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict[str, Any]]], None],
) -> None:
    """Describe the ``media_content_guard_blocked`` event."""

    @callback
    def _describe(event: Event) -> dict[str, Any]:
        data = event.data
        title = " – ".join(
            str(part) for part in (data.get(ATTR_MEDIA_ARTIST), data.get(ATTR_MEDIA_TITLE)) if part
        )
        return {
            LOGBOOK_ENTRY_NAME: data.get(ATTR_RULE_NAME, "Media Content Guard"),
            LOGBOOK_ENTRY_MESSAGE: _message(
                hass.config.language, title, str(data.get(ATTR_MATCHED_KEYWORD, ""))
            ),
            LOGBOOK_ENTRY_ENTITY_ID: data.get(ATTR_ENTITY_ID),
        }

    async_describe_event(DOMAIN, EVENT_BLOCKED, _describe)
