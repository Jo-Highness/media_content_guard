> 🇬🇧 English (this page) · 🇩🇪 [Deutsch](README.de.md)

<p align="center">
  <img src="icon.png" alt="Media Content Guard" width="160" height="160">
</p>

<h1 align="center">Media Content Guard</h1>

<p align="center">
  <b>A keyword blocklist for your Home Assistant media players: as soon as a speaker plays something on the list, playback is stopped — again and again, if needed.</b>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/Jo-Highness/media_content_guard/actions/workflows/validate.yml"><img src="https://github.com/Jo-Highness/media_content_guard/actions/workflows/validate.yml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/Jo-Highness/media_content_guard/actions/workflows/test.yml"><img src="https://github.com/Jo-Highness/media_content_guard/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/Jo-Highness/media_content_guard/releases"><img src="https://img.shields.io/github/v/release/Jo-Highness/media_content_guard" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.2%2B-41BDF5.svg" alt="Home Assistant 2025.2+">
</p>

Typical use: the kids' audio dramas should play in the kids' room — but **not** on the living
room speaker. Or: no more of that one song on the kitchen speaker. Put the keywords on the
list, pick the speakers, done.

## Quick start

1. **Install** via HACS: [![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jo-Highness&repository=media_content_guard&category=integration) → **Download** → restart Home Assistant.
2. **Add** the integration: **Settings → Devices & services → Add integration → Media Content Guard**.
3. Give the rule a **name** (e.g. `Living room`), **pick the speakers** and enter the
   **blocklist** — one keyword per line.
4. **Done.** Start something on the list on one of the speakers: it is stopped within a
   moment, and `sensor.content_guard_living_room_last_blocked` tells you what, where and why.

Need different lists for different rooms? Add another rule (step 2–3).

## What it does

- 🔎 **Searches title, album, artist and content ID** — case does not matter and part of a word
  is enough: `tkkg` blocks “TKKG Folge 200”, `???` blocks “Die drei ???”. Playlist, series,
  channel, app and source can be searched too.
- 🔊 **Any number of speakers per rule, any number of rules** — a speaker may be in several rules.
- ✏️ **Blocklist in the UI** — edit it any time under **Configure**; no YAML, no restart. Or use
  the actions `add_keyword` / `remove_keyword` (e.g. from a dashboard button or voice).
- 🔁 **Stubborn about it** — if the content keeps playing (Sonos apps like to retry), it is
  stopped again every 2 seconds, re-checking each time; the moment something harmless plays,
  it lets go.
- 🛟 **Doesn't miss anything** — checked on start of playback, on every track/album change,
  right after Home Assistant starts or the list is edited, when the guard is switched on, and
  every 30 seconds as a safety net.
- 🔕 **On/off switch per rule** — the state survives restarts.
- 📒 **Logbook entry and event** for every stop (`media_content_guard_blocked`) — ideal for a
  push notification.
- 🌍 **Multilingual UI** — English, German, Spanish and French.
- 🧩 **Fully local** — no cloud, no dependencies.

### What it can't do

This is a convenience tool, not a lock-down:

- It only sees what the player reports to Home Assistant. If a stream reports no title (some
  radio stations, AirPlay/Bluetooth from a phone, TV input), there is nothing to match.
- It reacts *after* playback started — the first second or two may be audible.
- Stopping uses `media_player.media_stop` (or `media_pause` if the player can't stop). A player
  that is offline or ignores the command keeps playing; the attempt is logged and repeated.
- Anyone with access to Home Assistant can switch the rule off or edit the list.
- Keywords match parts of words: a very short keyword (e.g. `ego`) also blocks “Lego” and
  “Ego”. Prefer distinctive keywords.

## Screenshot

> Captured from a demo Home Assistant with fictional data.

![A rule with its switch, sensors and the logbook entry of a stopped track](images/device.png)

## Installation

### HACS (recommended)

1. Click the **Open in HACS** button above, or in **HACS → ⋮ → Custom repositories** add
   `https://github.com/Jo-Highness/media_content_guard` as type **Integration**.
2. Search for **Media Content Guard** and **download** it.
3. **Restart** Home Assistant.

### Manual

1. Copy `custom_components/media_content_guard/` into your `<config>/custom_components/` folder.
2. **Restart** Home Assistant.

Requires **Home Assistant 2025.2** or newer.

## Configuration

Setup and later changes (**Configure** on the rule) use the same form:

| Field | What you set |
|---|---|
| **Name of the rule** | Shown as device name and used by the actions, e.g. `Living room`. Must be unique. |
| **Media players to watch** | One or more `media_player` entities. |
| **Blocklist** | One keyword per line. Case does not matter, part of a word is enough, empty lines and duplicates are dropped. |
| **Check these details** | Which media attributes are searched. Default: title, album, artist, content ID. Optional: playlist, series, channel, app, source. |

Changes apply immediately — content that is already playing is checked again right away.

## Entities

Each rule gets a **device** named after the rule. `<rule>` is the slugified name at the time the
rule was created, e.g. `living_room`:

| Entity | Type | Purpose |
|---|---|---|
| `switch.content_guard_<rule>_active` | switch | **Blocklist active** — off = nothing is stopped. Attributes `players`, `keyword_count`. |
| `sensor.content_guard_<rule>_last_blocked` | sensor (timestamp) | When content was last stopped. Attributes `player`, `matched_keyword`, `matched_field`, `media_title`, `media_artist`, `media_album_name`. |
| `sensor.content_guard_<rule>_blocked_count` | sensor (total increasing) | How often this rule has stopped playback. |

Switch state, counter and the last block survive restarts. Renaming the rule keeps the entity
IDs. If a watched player is renamed or removed, a **repair issue** tells you which one —
those players are not protected until you select the current ones under **Configure**.

## Actions (services)

Both actions address one rule, either with **`rule`** (name, case-insensitive) or with
**`config_entry_id`** (stays valid after a rename). `keyword` takes one keyword or a list.

| Action | Description |
|---|---|
| `media_content_guard.add_keyword` | Adds keywords to the blocklist (duplicates are ignored). What's playing is checked right away. |
| `media_content_guard.remove_keyword` | Removes keywords (case-insensitive). Fails with a clear message if none of them is on the list. |

## Event

Every stop fires `media_content_guard_blocked` with `entry_id`, `rule_name`, `entity_id`,
`matched_keyword`, `matched_field`, `media_title`, `media_artist`, `media_album_name`.
One event is fired per stop *run* — not for every retry.

## Automation examples

**Push notification when something was stopped:**

```yaml
automation:
  - alias: "Notify when content was blocked"
    triggers:
      - trigger: event
        event_type: media_content_guard_blocked
    actions:
      - action: notify.mobile_app_parent_phone
        data:
          title: "{{ trigger.event.data.rule_name }}"
          message: >-
            Stopped “{{ trigger.event.data.media_title }}” on
            {{ state_attr(trigger.event.data.entity_id, 'friendly_name') }}
            (keyword: {{ trigger.event.data.matched_keyword }}).
```

**Only block during the evening:**

```yaml
automation:
  - alias: "Living room blocklist in the evening"
    triggers:
      - trigger: time
        at: "18:00:00"
        id: "on"
      - trigger: time
        at: "07:00:00"
        id: "off"
    actions:
      - action: "switch.turn_{{ trigger.id }}"
        target:
          entity_id: switch.content_guard_living_room_active
```

**Add a keyword from a script/button:**

```yaml
action: media_content_guard.add_keyword
data:
  rule: Living room
  keyword:
    - Paw Patrol
    - Bibi Blocksberg
```

## Migrating from a YAML automation

If you used a hand-written automation/package with a keyword list (e.g. an `input_boolean` plus
an automation that calls `media_player.media_stop` in a loop):

1. Create a rule with the same speakers and copy the keywords — one per line.
2. Check that it works (sensor *Last blocked*).
3. Remove the old automation/package and its `input_boolean`, then reload/restart. Running both
   is harmless (they'd both stop the same content), but redundant.

## Troubleshooting / FAQ

**Something on the list isn't stopped.**
Open *Developer tools → States* and look at the player while it plays: is the keyword really in
`media_title`, `media_album_name`, `media_artist` or `media_content_id`? Audio dramas often carry
the series name only in the album. If it's in another attribute, enable it under
**Check these details**. Also check that the rule's switch is on and that there is no repair
issue about missing players.

**Too much is stopped.**
A keyword matches parts of words. Use longer, more specific keywords; the sensor
*Last blocked* shows which keyword matched and where (`matched_keyword`, `matched_field`).

**The speaker starts again right after the stop.**
The guard keeps stopping it every 2 s for up to 30 s, then the 30-second check takes over.
If the log says *“could not stop …”*, the player rejected the command.

**Enable debug logging:**

```yaml
logger:
  logs:
    custom_components.media_content_guard: debug
```

Diagnostics (without names, entity IDs or keywords) can be downloaded from the rule's ⋮ menu.

Architecture and design decisions: [`docs/TECHNICAL.md`](docs/TECHNICAL.md).

## Contributing

Contributions are welcome. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and open an issue
or pull request on [GitHub](https://github.com/Jo-Highness/media_content_guard).

## License

Released under the [MIT License](LICENSE).

## Credits

Created and maintained by [@Jo-Highness](https://github.com/Jo-Highness).
Built as a custom [Home Assistant](https://www.home-assistant.io/) integration for
[HACS](https://hacs.xyz/).
