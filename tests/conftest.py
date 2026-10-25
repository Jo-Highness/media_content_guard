"""Common fixtures for Media Content Guard tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant, ServiceCall
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.media_content_guard.const import (
    CONF_FIELDS,
    CONF_KEYWORDS,
    CONF_NAME,
    CONF_PLAYERS,
    DEFAULT_FIELDS,
    DOMAIN,
)

PLAYER = "media_player.sonos_move"
OTHER_PLAYER = "media_player.kitchen"
KEYWORDS = ["Lego", "???", "TKKG", "Bibi"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture(autouse=True)
def fast_retry():
    """Do not wait 2 s between stop attempts in tests."""
    with patch("custom_components.media_content_guard.const.STOP_RETRY_DELAY", 0):
        yield


def build_entry_data(
    *,
    name: str = "Living room",
    players: list[str] | None = None,
    keywords: list[str] | None = None,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Return config-entry data for a rule."""
    return {
        CONF_NAME: name,
        CONF_PLAYERS: players if players is not None else [PLAYER],
        CONF_KEYWORDS: keywords if keywords is not None else list(KEYWORDS),
        CONF_FIELDS: fields if fields is not None else list(DEFAULT_FIELDS),
    }


async def setup_rule(hass: HomeAssistant, **kwargs: Any) -> MockConfigEntry:
    """Add and set up a config entry for one rule."""
    data = build_entry_data(**kwargs)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=data[CONF_NAME],
        data=data,
        unique_id=f"{DOMAIN}_{data[CONF_NAME].casefold()}",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


class FakeSpeaker:
    """Registers media_player.media_stop/media_pause and records calls.

    ``obey`` controls whether the "speaker" actually stops (state -> paused).
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.calls: list[tuple[str, str]] = []
        self.obey = True
        for service in ("media_stop", "media_pause"):
            hass.services.async_register("media_player", service, self._make_handler(service))

    def _make_handler(self, service: str):
        async def _handler(call: ServiceCall) -> None:
            entity_ids = call.data["entity_id"]
            if isinstance(entity_ids, str):
                entity_ids = [entity_ids]
            for entity_id in entity_ids:
                self.calls.append((service, entity_id))
                if self.obey:
                    state = self.hass.states.get(entity_id)
                    self.hass.states.async_set(entity_id, "paused", state.attributes)

        return _handler

    def stops(self, entity_id: str | None = None) -> int:
        return len([c for c in self.calls if entity_id in (None, c[1])])


@pytest.fixture
def speaker(hass: HomeAssistant) -> FakeSpeaker:
    """A fake media player backend for stop/pause calls."""
    return FakeSpeaker(hass)


def play(hass: HomeAssistant, entity_id: str = PLAYER, state: str = "playing", **attrs: Any):
    """Set a media player state with media attributes."""
    hass.states.async_set(entity_id, state, attrs)
