# Media Content Guard — Technical Documentation

Audience: maintainers. User documentation is in the [README](../README.md).

## 1. Goal

Stop playback on selected `media_player` entities as soon as the media metadata contains a
keyword from a user-maintained blocklist. Origin: a YAML package that did this for one Sonos
speaker (keyword list in YAML, `input_boolean` as switch, automation with `mode: restart`,
triggers on `playing` + attribute changes, a `repeat/while` loop calling `media_stop` every 2 s
with a fresh template evaluation). The integration keeps that behaviour and adds multiple
players/rules, UI-maintained lists and a safety net.

## 2. Component overview

| File | Role |
|---|---|
| `matching.py` | Pure functions, no HA imports: `normalize` (NFKC + casefold + strip), `parse_keywords` (lines → clean, de-duplicated list), `find_match` (first keyword in list order found as substring in one of the fields). |
| `guard.py` | `ContentGuard` — runtime of one config entry: listeners, enforcement loops, persistence, event, repair issue. |
| `__init__.py` | Entry setup/unload, actions `add_keyword` / `remove_keyword`, reload on options change, cleanup on removal. |
| `config_flow.py` | One-step config flow and identical options flow. |
| `switch.py`, `sensor.py`, `entity.py` | Entities; they subscribe to guard callbacks (no polling). |
| `logbook.py` | Describes the `media_content_guard_blocked` event (message in the HA UI language). |
| `diagnostics.py` | Redacted diagnostics. |

## 3. Data

Config entry (`data`, later `options` — options win): `name`, `players` (list), `keywords`
(list of strings, stored as entered), `fields` (list of attribute names).

Store `.storage/media_content_guard.<entry_id>`: `enabled`, `block_count`, `last_block`
(`blocked_at`, `player`, `matched_keyword`, `matched_field`, `media_title`, `media_artist`,
`media_album_name`). Saved delayed (5 s) on change and immediately on unload, so a reload right
after a switch change reads the new value.

## 4. Triggers

1. `async_track_state_change_event` on the rule's players. Relevant when the new state is
   `playing` and either the old state was not `playing` or one of the searched attributes
   changed. Position/volume updates are ignored (Sonos sends them constantly).
2. `async_at_started` → `async_check_all` (content may already play at startup or after a
   reload — that produces no state change).
3. Switch turned on → `async_check_all`.
4. `async_track_time_interval` every 30 s → `async_check_all` (missed events, players that
   resumed after a run gave up).

`_async_check(state)`: guard enabled, state `playing`, no loop running for this player,
`find_match` hit → start a loop as an entry background task (cancelled on unload).

## 5. Enforcement loop

Per player at most one loop. Each round re-reads the state and re-matches; it ends as soon as
the guard is off/unloaded, the player is not `playing`, or the content no longer matches. In the
first round the block is recorded (counter, `last_block`, event, entity update) — one record per
run, not per retry. Then `media_stop` (or `media_pause` when the player advertises PAUSE but not
STOP), with a 10 s timeout; errors are logged, not raised. Sleep 2 s, at most 15 rounds; after
that a warning is logged and the 30 s poll takes over.

Compared with the YAML original (`mode: restart`): a new trigger while a loop runs does not
restart it — the loop already re-evaluates fresh state each round, which yields the same result
without cancel races.

## 6. Matching details

- Each field is matched separately (the YAML joined them with ` | `; equivalent unless a keyword
  contains ` | `).
- Non-string attribute values are converted with `str()`. Missing/empty fields are skipped.
- Keyword order matters only for reporting: the first matching keyword is reported.

## 7. Actions

`rule` (name/slug/title, case-insensitive) or `config_entry_id` selects the entry.
`add_keyword` merges via `parse_keywords` (case-insensitive de-duplication); `remove_keyword`
compares normalised values and raises `keyword_not_found` if nothing was removed. Both write
the new list to the entry options → update listener reloads the entry → startup check runs.

## 8. Validation

`ruff check`, `ruff format --check`, `pytest` (pytest-homeassistant-custom-component, Python
3.14), hassfest and the HACS action in CI. Live smoke test against HA with demo media players
(2026-10-25): creating a rule stopped two playing demo players, sensors/logbook/actions OK.
