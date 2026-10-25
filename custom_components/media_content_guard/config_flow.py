"""Config and options flow for Media Content Guard."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    AVAILABLE_FIELDS,
    CONF_FIELDS,
    CONF_KEYWORDS,
    CONF_NAME,
    CONF_PLAYERS,
    DEFAULT_FIELDS,
    DOMAIN,
)
from .matching import keywords_to_text, parse_keywords


def _name_in_use(hass: HomeAssistant, name: str, exclude_entry_id: str | None = None) -> bool:
    """Return True if another rule already uses ``name`` (case-insensitive)."""
    needle = name.strip().casefold()
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == exclude_entry_id:
            continue
        merged = {**entry.data, **entry.options}
        names = {str(merged.get(CONF_NAME, "")).strip().casefold(), entry.title.casefold()}
        if needle in names:
            return True
    return False


def _rule_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): selector.TextSelector(),
            vol.Required(
                CONF_PLAYERS, default=defaults.get(CONF_PLAYERS, [])
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player", multiple=True)
            ),
            vol.Required(
                CONF_KEYWORDS,
                default=keywords_to_text(defaults.get(CONF_KEYWORDS, [])),
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
            vol.Required(
                CONF_FIELDS, default=defaults.get(CONF_FIELDS, DEFAULT_FIELDS)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=AVAILABLE_FIELDS,
                    multiple=True,
                    translation_key="fields",
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


def _validate(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Clean the submitted form and return ``(data, errors)``."""
    data = {
        CONF_NAME: str(user_input.get(CONF_NAME, "")).strip(),
        CONF_PLAYERS: list(user_input.get(CONF_PLAYERS) or []),
        CONF_KEYWORDS: parse_keywords(user_input.get(CONF_KEYWORDS, "")),
        CONF_FIELDS: [f for f in AVAILABLE_FIELDS if f in (user_input.get(CONF_FIELDS) or [])],
    }
    errors: dict[str, str] = {}
    if not data[CONF_NAME]:
        errors[CONF_NAME] = "name_required"
    if not data[CONF_PLAYERS]:
        errors[CONF_PLAYERS] = "no_players"
    if not data[CONF_KEYWORDS]:
        errors[CONF_KEYWORDS] = "no_keywords"
    if not data[CONF_FIELDS]:
        errors[CONF_FIELDS] = "no_fields"
    return data, errors


class MediaContentGuardConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a new rule (players + blocklist)."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {}
        if user_input is not None:
            data, errors = _validate(user_input)
            defaults = data
            if not errors:
                if _name_in_use(self.hass, data[CONF_NAME]):
                    return self.async_abort(reason="already_configured")
                unique_id = f"{DOMAIN}_{data[CONF_NAME].casefold()}"
                if self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, unique_id):
                    # The unique_id is kept on rename, so a renamed rule can
                    # still hold the id derived from this name.
                    unique_id = f"{unique_id}_{uuid4().hex[:8]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_NAME], data=data)
        return self.async_show_form(
            step_id="user", data_schema=_rule_schema(defaults), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> MediaContentGuardOptionsFlow:
        return MediaContentGuardOptionsFlow()


class MediaContentGuardOptionsFlow(OptionsFlow):
    """Edit name, players, blocklist and searched fields of a rule."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {**entry.data, **entry.options}
        if user_input is not None:
            data, errors = _validate(user_input)
            defaults = data
            if not errors and _name_in_use(
                self.hass, data[CONF_NAME], exclude_entry_id=entry.entry_id
            ):
                errors[CONF_NAME] = "name_in_use"
            if not errors:
                # Title and options in one update -> exactly one reload. The
                # unique_id stays, so entity IDs are kept on rename.
                self.hass.config_entries.async_update_entry(
                    entry, title=data[CONF_NAME], options=data
                )
                return self.async_create_entry(data=data)
        return self.async_show_form(
            step_id="init", data_schema=_rule_schema(defaults), errors=errors
        )
