"""Tests for the add_keyword / remove_keyword actions."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components.media_content_guard.const import CONF_KEYWORDS, DOMAIN

from .conftest import play, setup_rule


async def test_add_keyword_by_name(hass: HomeAssistant, speaker):
    play(hass, state="idle")
    entry = await setup_rule(hass, keywords=["Lego"])
    play(hass, media_title="Paw Patrol")
    await hass.async_block_till_done(wait_background_tasks=True)

    await hass.services.async_call(
        DOMAIN,
        "add_keyword",
        {"rule": "living room", "keyword": ["Paw Patrol", "lego", " Bibi "]},
        blocking=True,
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.options[CONF_KEYWORDS] == ["Lego", "Paw Patrol", "Bibi"]
    # Content that is playing right now is checked after the change.
    assert speaker.stops() == 1


async def test_add_keyword_by_entry_id_single_string(hass: HomeAssistant):
    entry = await setup_rule(hass, keywords=["Lego"])
    await hass.services.async_call(
        DOMAIN,
        "add_keyword",
        {"config_entry_id": entry.entry_id, "keyword": "TKKG"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.keywords == ["Lego", "TKKG"]


async def test_remove_keyword(hass: HomeAssistant):
    entry = await setup_rule(hass, keywords=["Lego", "TKKG"])
    await hass.services.async_call(
        DOMAIN, "remove_keyword", {"rule": "Living room", "keyword": "lego"}, blocking=True
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.keywords == ["TKKG"]

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "remove_keyword", {"rule": "Living room", "keyword": "Bibi"}, blocking=True
        )
    assert err.value.translation_key == "keyword_not_found"


async def test_unknown_rule_and_entry(hass: HomeAssistant):
    await setup_rule(hass)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "add_keyword", {"rule": "Attic", "keyword": "x"}, blocking=True
        )
    assert err.value.translation_key == "rule_not_found"

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "add_keyword", {"config_entry_id": "nope", "keyword": "x"}, blocking=True
        )
    assert err.value.translation_key == "entry_not_found"


async def test_target_is_required(hass: HomeAssistant):
    await setup_rule(hass)
    with pytest.raises(Exception):  # noqa: B017 - voluptuous error type varies
        await hass.services.async_call(DOMAIN, "add_keyword", {"keyword": "x"}, blocking=True)
