"""Runtime of one Media Content Guard rule: watch players, stop blocked content."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_STOP,
    MediaPlayerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify

from . import const
from .const import (
    ATTR_BLOCKED_AT,
    ATTR_ENTRY_ID,
    ATTR_MATCHED_FIELD,
    ATTR_MATCHED_KEYWORD,
    ATTR_MEDIA_ALBUM,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_TITLE,
    ATTR_PLAYER,
    ATTR_RULE_NAME,
    CONF_FIELDS,
    CONF_KEYWORDS,
    CONF_NAME,
    CONF_PLAYERS,
    DEFAULT_FIELDS,
    DOMAIN,
    EVENT_BLOCKED,
    POLL_INTERVAL,
    SAVE_DELAY,
    STATE_PLAYING,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
)
from .matching import Match, find_match, parse_keywords

_LOGGER = logging.getLogger(__name__)


def missing_players_issue_id(entry_id: str) -> str:
    """Return the repair issue id for missing players of an entry."""
    return f"missing_players_{entry_id}"


class ContentGuard:
    """Watch the players of one rule and stop content that matches a keyword.

    Robustness, carried over from the original YAML automation and extended:

    * checked when a player starts ``playing`` **and** whenever one of the
      searched attributes changes while it plays (next track, new album, …);
    * blocked content is stopped in a loop (every 2 s) for as long as the
      player keeps playing it - each round re-reads the current state, so the
      loop ends as soon as harmless content plays or the guard is switched off;
    * at most one loop per player; further triggers while it runs are absorbed;
    * extra safety net: a check after Home Assistant has started, when the
      guard is switched on, after a reload and every 30 s.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        conf = {**entry.data, **entry.options}
        self.name: str = conf.get(CONF_NAME) or entry.title
        self.slug: str = slugify(self.name) or entry.entry_id[:8]
        self.players: list[str] = list(conf.get(CONF_PLAYERS, []))
        self.keywords: list[str] = parse_keywords(conf.get(CONF_KEYWORDS, []))
        self.fields: list[str] = list(conf.get(CONF_FIELDS) or DEFAULT_FIELDS)

        self.enabled = True
        self.block_count = 0
        self.last_block: dict[str, Any] | None = None

        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}"
        )
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._listeners: list[CALLBACK_TYPE] = []
        self._unloaded = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_setup(self) -> None:
        """Restore the saved state and start watching the players."""
        stored = await self._store.async_load() or {}
        self.enabled = bool(stored.get("enabled", True))
        self.block_count = int(stored.get("block_count", 0))
        self.last_block = stored.get("last_block")

        if self.players:
            self.entry.async_on_unload(
                async_track_state_change_event(self.hass, self.players, self._async_on_state)
            )
        self.entry.async_on_unload(
            async_track_time_interval(
                self.hass, self._async_poll, POLL_INTERVAL, name=f"{DOMAIN} {self.name} check"
            )
        )
        self.entry.async_on_unload(self._async_shutdown)

    async def _async_shutdown(self) -> None:
        """Stop running loops and write the state on unload.

        Saved right away (not delayed) so a reload directly afterwards - e.g.
        after editing the blocklist - reads the current switch state.
        """
        self._unloaded = True
        for task in list(self._tasks.values()):
            task.cancel()
        self._tasks.clear()
        await self._store.async_save(self._data_to_save())

    @callback
    def async_check_missing_players(self) -> None:
        """Raise (or clear) a repair issue for players that no longer exist."""
        missing = [p for p in self.players if self.hass.states.get(p) is None]
        issue_id = missing_players_issue_id(self.entry.entry_id)
        if not missing:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_players",
            translation_placeholders={"name": self.name, "entities": ", ".join(missing)},
        )

    # ------------------------------------------------------------------
    # Listeners for entities
    # ------------------------------------------------------------------
    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> Callable[[], None]:
        """Register an entity callback; returns a function to remove it."""
        self._listeners.append(update_callback)

        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    @callback
    def _async_notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------
    async def async_set_enabled(self, enabled: bool) -> None:
        """Switch the guard on or off. Switching on checks right away."""
        self.enabled = enabled
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        self._async_notify()
        if enabled:
            self.async_check_all()

    def match_state(self, state: State | None) -> Match | None:
        """Return the keyword match for a player state (``None`` = harmless)."""
        if state is None or not self.keywords:
            return None
        return find_match(state.attributes, self.keywords, self.fields)

    @callback
    def async_check_all(self) -> None:
        """Check every player of this rule."""
        for entity_id in self.players:
            self._async_check(self.hass.states.get(entity_id))

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------
    @callback
    def _async_on_state(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data["new_state"]
        if new_state is None or new_state.state != STATE_PLAYING:
            return
        old_state = event.data["old_state"]
        if (
            old_state is not None
            and old_state.state == STATE_PLAYING
            and all(
                old_state.attributes.get(field) == new_state.attributes.get(field)
                for field in self.fields
            )
        ):
            # Only position/volume changed - nothing new to look at. The poll
            # still covers this player.
            return
        self._async_check(new_state)

    @callback
    def _async_poll(self, _now: datetime) -> None:
        self.async_check_all()

    @callback
    def _async_check(self, state: State | None) -> None:
        """Start an enforcement loop if ``state`` plays blocked content."""
        if self._unloaded or not self.enabled or state is None:
            return
        if state.state != STATE_PLAYING:
            return
        entity_id = state.entity_id
        running = self._tasks.get(entity_id)
        if running is not None and not running.done():
            return  # the running loop re-checks on every round
        if self.match_state(state) is None:
            return
        self._tasks[entity_id] = self.entry.async_create_background_task(
            self.hass,
            self._async_enforce(entity_id),
            name=f"{DOMAIN} stop {entity_id}",
        )

    # ------------------------------------------------------------------
    # Enforcement
    # ------------------------------------------------------------------
    async def _async_enforce(self, entity_id: str) -> None:
        """Stop the player until it no longer plays blocked content."""
        try:
            for attempt in range(const.MAX_STOP_ATTEMPTS):
                state = self.hass.states.get(entity_id)
                # Fresh evaluation in every round (never trust a stale match).
                if self._unloaded or not self.enabled or state is None:
                    return
                if state.state != STATE_PLAYING:
                    return
                match = self.match_state(state)
                if match is None:
                    return
                if attempt == 0:
                    self._async_record_block(state, match)
                await self._async_stop(state)
                await asyncio.sleep(const.STOP_RETRY_DELAY)
            _LOGGER.warning(
                "%s: %s still plays blocked content after %s stop attempts; "
                "will try again with the next check",
                self.name,
                entity_id,
                const.MAX_STOP_ATTEMPTS,
            )
        finally:
            if self._tasks.get(entity_id) is asyncio.current_task():
                self._tasks.pop(entity_id, None)

    async def _async_stop(self, state: State) -> None:
        """Stop the player; fall back to pause if it cannot stop."""
        features = int(state.attributes.get(ATTR_SUPPORTED_FEATURES) or 0)
        service = SERVICE_MEDIA_STOP
        if (
            features
            and not features & MediaPlayerEntityFeature.STOP
            and features & MediaPlayerEntityFeature.PAUSE
        ):
            service = SERVICE_MEDIA_PAUSE
        try:
            async with asyncio.timeout(const.STOP_CALL_TIMEOUT):
                await self.hass.services.async_call(
                    MEDIA_PLAYER_DOMAIN,
                    service,
                    {ATTR_ENTITY_ID: state.entity_id},
                    blocking=True,
                )
        except (HomeAssistantError, TimeoutError) as err:
            _LOGGER.warning(
                "%s: could not %s %s: %s",
                self.name,
                service.removeprefix("media_"),
                state.entity_id,
                err or type(err).__name__,
            )

    @callback
    def _async_record_block(self, state: State, match: Match) -> None:
        """Remember the block, fire the event and update the entities."""
        now = dt_util.utcnow()
        self.block_count += 1
        self.last_block = {
            ATTR_BLOCKED_AT: now.isoformat(),
            ATTR_PLAYER: state.entity_id,
            ATTR_MATCHED_KEYWORD: match.keyword,
            ATTR_MATCHED_FIELD: match.field,
            ATTR_MEDIA_TITLE: state.attributes.get(ATTR_MEDIA_TITLE),
            ATTR_MEDIA_ARTIST: state.attributes.get(ATTR_MEDIA_ARTIST),
            ATTR_MEDIA_ALBUM: state.attributes.get(ATTR_MEDIA_ALBUM),
        }
        _LOGGER.info(
            "%s: stopping %s - keyword %r found in %s",
            self.name,
            state.entity_id,
            match.keyword,
            match.field,
        )
        self.hass.bus.async_fire(
            EVENT_BLOCKED,
            {
                ATTR_ENTRY_ID: self.entry.entry_id,
                ATTR_RULE_NAME: self.name,
                **{
                    k: v
                    for k, v in self.last_block.items()
                    if k not in (ATTR_BLOCKED_AT, ATTR_PLAYER)
                },
                ATTR_ENTITY_ID: state.entity_id,
            },
        )
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        self._async_notify()

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "block_count": self.block_count,
            "last_block": self.last_block,
        }
