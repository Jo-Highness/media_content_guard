"""Switch platform for Media Content Guard."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MediaContentGuardConfigEntry
from .const import ATTR_KEYWORD_COUNT, ATTR_PLAYERS
from .entity import MediaContentGuardEntity
from .guard import ContentGuard

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MediaContentGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the on/off switch of a rule."""
    async_add_entities([GuardActiveSwitch(entry.runtime_data)])


class GuardActiveSwitch(MediaContentGuardEntity, SwitchEntity):
    """Turns the blocklist of a rule on or off (state survives restarts)."""

    _attr_translation_key = "active"

    def __init__(self, guard: ContentGuard) -> None:
        super().__init__(guard, "active", Platform.SWITCH)

    @property
    def is_on(self) -> bool:
        return self.guard.enabled

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            ATTR_PLAYERS: list(self.guard.players),
            ATTR_KEYWORD_COUNT: len(self.guard.keywords),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.guard.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.guard.async_set_enabled(False)
