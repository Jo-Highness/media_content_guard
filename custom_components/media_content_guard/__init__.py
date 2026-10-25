"""The Media Content Guard integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_KEYWORD,
    ATTR_RULE,
    CONF_KEYWORDS,
    DOMAIN,
    SERVICE_ADD_KEYWORD,
    SERVICE_REMOVE_KEYWORD,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .guard import ContentGuard, missing_players_issue_id
from .matching import normalize, parse_keywords

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type MediaContentGuardConfigEntry = ConfigEntry[ContentGuard]

# Every service addresses one rule, either by name (``rule``) or by its
# config entry (``config_entry_id``, stable across renames).
KEYWORD_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional(ATTR_RULE): cv.string,
            vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
            vol.Required(ATTR_KEYWORD): vol.All(cv.ensure_list, [cv.string]),
        }
    ),
    cv.has_at_least_one_key(ATTR_RULE, ATTR_CONFIG_ENTRY_ID),
)


def _find_entry(hass: HomeAssistant, call: ServiceCall) -> MediaContentGuardConfigEntry:
    """Resolve the service call target to its config entry."""
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_found",
                translation_placeholders={"entry_id": entry_id},
            )
        if entry.state is not ConfigEntryState.LOADED:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_loaded",
                translation_placeholders={"name": entry.title},
            )
        return entry

    rule: str = call.data[ATTR_RULE]
    needle = rule.strip().casefold()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is not ConfigEntryState.LOADED:
            continue
        guard: ContentGuard = entry.runtime_data
        if needle in (guard.name.casefold(), guard.slug, entry.title.casefold()):
            return entry
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="rule_not_found",
        translation_placeholders={"rule": rule},
    )


def _store_keywords(
    hass: HomeAssistant, entry: MediaContentGuardConfigEntry, keywords: list[str]
) -> None:
    """Persist a new keyword list; the update listener reloads the entry."""
    options = {**entry.data, **entry.options, CONF_KEYWORDS: keywords}
    hass.config_entries.async_update_entry(entry, options=options)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's services (once, independent of entries)."""

    async def _handle_add(call: ServiceCall) -> None:
        entry = _find_entry(hass, call)
        current = entry.runtime_data.keywords
        merged = parse_keywords([*current, *call.data[ATTR_KEYWORD]])
        if merged != current:
            _store_keywords(hass, entry, merged)

    async def _handle_remove(call: ServiceCall) -> None:
        entry = _find_entry(hass, call)
        current = entry.runtime_data.keywords
        drop = {normalize(keyword) for keyword in call.data[ATTR_KEYWORD]}
        remaining = [keyword for keyword in current if normalize(keyword) not in drop]
        if remaining == current:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="keyword_not_found",
                translation_placeholders={
                    "keyword": ", ".join(call.data[ATTR_KEYWORD]),
                    "name": entry.title,
                },
            )
        _store_keywords(hass, entry, remaining)

    hass.services.async_register(DOMAIN, SERVICE_ADD_KEYWORD, _handle_add, schema=KEYWORD_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_KEYWORD, _handle_remove, schema=KEYWORD_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MediaContentGuardConfigEntry) -> bool:
    """Set up one Media Content Guard rule from a config entry."""
    guard = ContentGuard(hass, entry)
    await guard.async_setup()
    entry.runtime_data = guard

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    @callback
    def _started(_hass: HomeAssistant) -> None:
        guard.async_check_missing_players()
        # Content may already be playing (HA restart, reload after editing the
        # list) - that produces no state change, so look once right away.
        guard.async_check_all()

    entry.async_on_unload(async_at_started(hass, _started))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MediaContentGuardConfigEntry) -> bool:
    """Unload a config entry.

    The guard stops its loops and saves its state itself via
    ``entry.async_on_unload``.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MediaContentGuardConfigEntry) -> None:
    """Remove stored data and the repair issue of a deleted rule."""
    ir.async_delete_issue(hass, DOMAIN, missing_players_issue_id(entry.entry_id))
    await Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}").async_remove()


async def _async_update_listener(hass: HomeAssistant, entry: MediaContentGuardConfigEntry) -> None:
    """Reload the entry when its options (or title) change."""
    await hass.config_entries.async_reload(entry.entry_id)
