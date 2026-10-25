"""Tests for setup, diagnostics and the logbook description."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Event, HomeAssistant

from custom_components.media_content_guard.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.media_content_guard.logbook import _message, async_describe_events

from .conftest import PLAYER, play, setup_rule


async def test_setup_and_unload(hass: HomeAssistant):
    entry = await setup_rule(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("switch.content_guard_living_room_active").state == "on"
    assert hass.states.get("sensor.content_guard_living_room_last_blocked").state == "unknown"
    assert hass.states.get("sensor.content_guard_living_room_blocked_count").state == "0"
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_counter_and_last_block_survive_reload(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    entry = await setup_rule(hass)
    play(hass, media_title="Lego")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.content_guard_living_room_blocked_count").state == "1"
    last = hass.states.get("sensor.content_guard_living_room_last_blocked")
    assert last.attributes["matched_keyword"] == "Lego"


async def test_diagnostics_redacts_personal_data(hass: HomeAssistant):
    play(hass, state="idle")
    entry = await setup_rule(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diag)
    assert "Living room" not in text
    assert PLAYER not in text
    assert "TKKG" not in text
    assert diag["keyword_count"] == 4
    assert diag["players"][0]["exists"] is True


async def test_logbook_messages():
    assert (
        _message("de", "TKKG – Folge 1", "TKKG")
        == "hat „TKKG – Folge 1“ gestoppt (Stichwort: TKKG)"
    )
    assert _message("en-GB", "", "Lego") == "stopped playback (keyword: Lego)"
    assert _message("xx", "Song", "k") == "stopped “Song” (keyword: k)"


async def test_logbook_describes_event(hass: HomeAssistant):
    described = {}
    async_describe_events(hass, lambda domain, event, fn: described.update({event: fn}))
    describe = described["media_content_guard_blocked"]
    hass.config.language = "de"
    entry = describe(
        Event(
            "media_content_guard_blocked",
            {
                "rule_name": "Wohnzimmer",
                "entity_id": PLAYER,
                "matched_keyword": "TKKG",
                "media_artist": "TKKG",
                "media_title": "Folge 1",
            },
        )
    )
    assert entry == {
        "name": "Wohnzimmer",
        "message": "hat „TKKG – Folge 1“ gestoppt (Stichwort: TKKG)",
        "entity_id": PLAYER,
    }
