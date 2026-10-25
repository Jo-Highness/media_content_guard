"""Diagnostics support for Media Content Guard."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MediaContentGuardConfigEntry
from .const import CONF_KEYWORDS, CONF_NAME, CONF_PLAYERS

# Rule names, entity ids (often rooms or children's names), the keyword list
# and played titles are personal - only counts and states are included.
TO_REDACT = {CONF_NAME, CONF_PLAYERS, CONF_KEYWORDS, "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MediaContentGuardConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    guard = entry.runtime_data
    players = []
    for index, entity_id in enumerate(guard.players):
        state = hass.states.get(entity_id)
        players.append(
            {
                "index": index,
                "exists": state is not None,
                "state": state.state if state else None,
                "supported_features": state.attributes.get("supported_features") if state else None,
                "searched_fields_present": sorted(
                    field for field in guard.fields if state and state.attributes.get(field)
                ),
                "enforcing": entity_id in guard._tasks,
            }
        )
    return {
        "entry": async_redact_data(
            {
                "version": entry.version,
                "title": entry.title,
                "unique_id": entry.unique_id,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "enabled": guard.enabled,
        "keyword_count": len(guard.keywords),
        "fields": guard.fields,
        "players": players,
        "block_count": guard.block_count,
        "last_block_at": (guard.last_block or {}).get("blocked_at"),
    }
