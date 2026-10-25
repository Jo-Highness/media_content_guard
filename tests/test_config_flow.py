"""Tests for the Media Content Guard config and options flow."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.media_content_guard.const import (
    CONF_FIELDS,
    CONF_KEYWORDS,
    CONF_NAME,
    CONF_PLAYERS,
    DEFAULT_FIELDS,
    DOMAIN,
)

from .conftest import OTHER_PLAYER, PLAYER, build_entry_data, play, setup_rule


def _form(name="Living room", players=None, keywords="Lego\nTKKG", fields=None):
    return {
        CONF_NAME: name,
        CONF_PLAYERS: players if players is not None else [PLAYER],
        CONF_KEYWORDS: keywords,
        CONF_FIELDS: fields if fields is not None else list(DEFAULT_FIELDS),
    }


async def _start(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    return result


async def test_full_config_flow(hass: HomeAssistant):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        _form(
            name="  Living room ",
            players=[PLAYER, OTHER_PLAYER],
            keywords="Lego\n\n  TKKG \nlego\n???",
        ),
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living room"
    assert result["data"] == {
        CONF_NAME: "Living room",
        CONF_PLAYERS: [PLAYER, OTHER_PLAYER],
        CONF_KEYWORDS: ["Lego", "TKKG", "???"],
        CONF_FIELDS: list(DEFAULT_FIELDS),
    }


async def test_validation_errors(hass: HomeAssistant):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _form(name=" ", players=[], keywords="\n \n", fields=[])
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {
        CONF_NAME: "name_required",
        CONF_PLAYERS: "no_players",
        CONF_KEYWORDS: "no_keywords",
        CONF_FIELDS: "no_fields",
    }


async def test_duplicate_name_aborts(hass: HomeAssistant):
    MockConfigEntry(
        domain=DOMAIN, title="Living room", data=build_entry_data(name="Living room")
    ).add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _form(name="living ROOM")
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_player_may_be_in_several_rules(hass: HomeAssistant):
    await setup_rule(hass, name="Kids")
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], _form(name="Evening")
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_edits_blocklist(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    entry = await setup_rule(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    # The current list is offered as one keyword per line.
    defaults = {str(k): k.default() for k in result["data_schema"].schema if callable(k.default)}
    assert defaults[CONF_KEYWORDS] == "Lego\n???\nTKKG\nBibi"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        _form(name="Living room", keywords="Paw Patrol\nLego", fields=["media_title"]),
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_KEYWORDS] == ["Paw Patrol", "Lego"]
    assert entry.state is ConfigEntryState.LOADED
    guard = entry.runtime_data
    assert guard.keywords == ["Paw Patrol", "Lego"]
    assert guard.fields == ["media_title"]


async def test_options_flow_rename(hass: HomeAssistant):
    entry = await setup_rule(hass)
    unique_id = entry.unique_id
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _form(name="Wohnzimmer")
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.title == "Wohnzimmer"
    assert entry.unique_id == unique_id
    assert entry.runtime_data.name == "Wohnzimmer"
    # Entity IDs are kept (registry wins).
    assert hass.states.get("switch.content_guard_living_room_active") is not None


async def test_options_flow_rejects_name_of_other_rule(hass: HomeAssistant):
    await setup_rule(hass, name="Kids", players=[OTHER_PLAYER])
    entry = await setup_rule(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _form(name="kids")
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "name_in_use"}


async def test_options_change_rechecks_playing_content(hass: HomeAssistant, speaker):
    """A keyword added in the options stops what is already playing."""
    play(hass, state="idle")
    entry = await setup_rule(hass)
    play(hass, media_title="Paw Patrol")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == []

    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], _form(keywords="Paw Patrol")
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 1
