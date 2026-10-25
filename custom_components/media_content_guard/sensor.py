"""Sensor platform for Media Content Guard."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MediaContentGuardConfigEntry
from .const import ATTR_BLOCKED_AT
from .entity import MediaContentGuardEntity
from .guard import ContentGuard

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MediaContentGuardConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of a rule."""
    guard = entry.runtime_data
    async_add_entities([LastBlockedSensor(guard), BlockedCountSensor(guard)])


class LastBlockedSensor(MediaContentGuardEntity, SensorEntity):
    """When content was last stopped - with player, keyword and title."""

    _attr_translation_key = "last_blocked"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, guard: ContentGuard) -> None:
        super().__init__(guard, "last_blocked", Platform.SENSOR)

    @property
    def native_value(self) -> datetime | None:
        last = self.guard.last_block
        if not last or not last.get(ATTR_BLOCKED_AT):
            return None
        return dt_util.parse_datetime(last[ATTR_BLOCKED_AT])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        last = dict(self.guard.last_block or {})
        last.pop(ATTR_BLOCKED_AT, None)
        return last


class BlockedCountSensor(MediaContentGuardEntity, SensorEntity):
    """How often content has been stopped by this rule (ever increasing)."""

    _attr_translation_key = "blocked_count"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, guard: ContentGuard) -> None:
        super().__init__(guard, "blocked_count", Platform.SENSOR)

    @property
    def native_value(self) -> int:
        return self.guard.block_count
