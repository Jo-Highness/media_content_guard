"""Base entity for Media Content Guard."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .guard import ContentGuard


class MediaContentGuardEntity(Entity):
    """Base class wiring entities to a rule's :class:`ContentGuard`."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, guard: ContentGuard, key: str, platform: str) -> None:
        self.guard = guard
        self._attr_unique_id = f"{guard.entry.entry_id}_{key}"
        # Suggested entity_id only - used when the entity is first registered;
        # afterwards the registry wins, so renaming the rule keeps the IDs.
        # Language-independent pattern: <platform>.content_guard_<slug>_<key>.
        self.entity_id = f"{platform}.content_guard_{guard.slug}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, guard.entry.entry_id)},
            name=guard.name,
            manufacturer="Media Content Guard",
            model="Keyword blocklist for media players",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.guard.async_add_listener(self.async_write_ha_state))
