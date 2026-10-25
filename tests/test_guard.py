"""Tests for detection and enforcement."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.media_content_guard.const import DOMAIN, EVENT_BLOCKED, MAX_STOP_ATTEMPTS
from custom_components.media_content_guard.guard import missing_players_issue_id

from .conftest import OTHER_PLAYER, PLAYER, play, setup_rule

SWITCH = "switch.content_guard_living_room_active"
LAST = "sensor.content_guard_living_room_last_blocked"
COUNT = "sensor.content_guard_living_room_blocked_count"


async def test_blocked_content_is_stopped(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    await setup_rule(hass)
    events = async_capture_events(hass, EVENT_BLOCKED)

    play(hass, media_title="Folge 12", media_album_name="TKKG Junior", media_artist="TKKG")
    await hass.async_block_till_done(wait_background_tasks=True)

    assert speaker.calls == [("media_stop", PLAYER)]
    assert hass.states.get(PLAYER).state == "paused"
    assert len(events) == 1
    assert events[0].data["matched_keyword"] == "TKKG"
    assert events[0].data["entity_id"] == PLAYER
    assert events[0].data["rule_name"] == "Living room"

    last = hass.states.get(LAST)
    assert last.state not in ("unknown", "unavailable")
    assert last.attributes["player"] == PLAYER
    assert last.attributes["matched_keyword"] == "TKKG"
    assert last.attributes["media_title"] == "Folge 12"
    assert hass.states.get(COUNT).state == "1"


async def test_harmless_content_keeps_playing(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    await setup_rule(hass)
    play(hass, media_title="Bohemian Rhapsody", media_artist="Queen")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == []
    assert hass.states.get(COUNT).state == "0"


async def test_track_change_while_playing_is_checked(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    await setup_rule(hass)
    play(hass, media_title="Harmless song")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == []

    play(hass, media_title="Bibi Blocksberg – Hexen gibt es doch")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 1


async def test_position_updates_do_not_retrigger(hass: HomeAssistant, speaker):
    """A player that ignored the stop loop is not restarted by position ticks."""
    play(hass, state="idle")
    await setup_rule(hass)
    speaker.obey = False
    play(hass, media_title="Lego Ninjago", media_position=1)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == MAX_STOP_ATTEMPTS
    play(hass, media_title="Lego Ninjago", media_position=2)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == MAX_STOP_ATTEMPTS


async def test_stop_loop_repeats_until_stopped(hass: HomeAssistant, speaker):
    """Like the YAML automation: keep stopping while it still plays."""
    play(hass, state="idle")
    await setup_rule(hass)
    speaker.obey = False
    play(hass, media_title="Lego City")
    await hass.async_block_till_done(wait_background_tasks=True)
    # The speaker ignores every stop -> the loop gives up after the limit ...
    assert speaker.stops() == MAX_STOP_ATTEMPTS
    # ... and only one block is recorded for this run.
    assert hass.states.get(COUNT).state == "1"

    # ... and the periodic check starts a new run.
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 2 * MAX_STOP_ATTEMPTS


async def test_loop_ends_when_harmless_content_plays(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    await setup_rule(hass)
    speaker.obey = False

    original = speaker._make_handler("media_stop")

    async def _switch_track(call):
        await original(call)
        if speaker.stops() == 3:
            play(hass, media_title="Harmless")

    hass.services.async_register("media_player", "media_stop", _switch_track)
    play(hass, media_title="Lego City")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 3


async def test_disabled_switch_does_not_stop(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    await setup_rule(hass)
    await hass.services.async_call("switch", "turn_off", {"entity_id": SWITCH}, blocking=True)
    assert hass.states.get(SWITCH).state == "off"

    play(hass, media_title="Lego City")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == []

    # Switching on again checks what is playing right now.
    await hass.services.async_call("switch", "turn_on", {"entity_id": SWITCH}, blocking=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 1


async def test_switch_state_survives_reload(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    entry = await setup_rule(hass)
    await hass.services.async_call("switch", "turn_off", {"entity_id": SWITCH}, blocking=True)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.states.get(SWITCH).state == "off"
    assert entry.runtime_data.enabled is False


async def test_multiple_players(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    play(hass, OTHER_PLAYER, state="idle")
    await setup_rule(hass, players=[PLAYER, OTHER_PLAYER])

    play(hass, OTHER_PLAYER, media_artist="Die drei ???")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == [("media_stop", OTHER_PLAYER)]

    play(hass, PLAYER, media_title="TKKG")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops(PLAYER) == 1


async def test_unwatched_player_is_ignored(hass: HomeAssistant, speaker):
    await setup_rule(hass)
    play(hass, OTHER_PLAYER, media_title="Lego")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == []


async def test_already_playing_at_start_is_stopped(hass: HomeAssistant, speaker):
    """Content playing during HA start/reload produces no state change."""
    hass.set_state(CoreState.not_running)
    play(hass, media_title="Lego Movie")
    await setup_rule(hass)
    assert speaker.calls == []
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 1


async def test_pause_fallback_when_stop_not_supported(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    await setup_rule(hass)
    play(
        hass,
        media_title="Lego",
        supported_features=int(MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.PLAY),
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.calls == [("media_pause", PLAYER)]


async def test_failing_stop_is_logged_not_raised(hass: HomeAssistant, caplog):
    play(hass, state="idle")
    await setup_rule(hass)  # no media_player services registered at all
    play(hass, media_title="Lego")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert "could not stop media_player.sonos_move" in caplog.text


async def test_unload_cancels_loop(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    entry = await setup_rule(hass)
    speaker.obey = False
    with patch("custom_components.media_content_guard.const.STOP_RETRY_DELAY", 60):
        play(hass, media_title="Lego")
        await hass.async_block_till_done(wait_background_tasks=False)
        assert entry.runtime_data._tasks
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)
    assert speaker.stops() == 1


async def test_missing_player_creates_repair_issue(hass: HomeAssistant, speaker):
    entry = await setup_rule(hass, players=["media_player.gone"])
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, missing_players_issue_id(entry.entry_id))

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert registry.async_get_issue(DOMAIN, missing_players_issue_id(entry.entry_id)) is None
