# Changelog

All notable changes to **Media Content Guard** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-25

First release. Replaces a hand-written YAML package (keyword list + `input_boolean` +
stop-loop automation for one Sonos speaker) and keeps its behaviour.

### Added

- Rules configured in the UI: name, any number of media players, blocklist (one keyword per
  line) and the media attributes to search (title, album, artist, content ID by default;
  playlist, series, channel, app and source optional). Everything editable via **Configure**.
- Case-insensitive substring matching (Unicode-normalised, trimmed).
- Enforcement: checked on start of playback and on every change of a searched attribute;
  blocked content is stopped every 2 s (re-checked each round) until something harmless plays,
  at most 15 times per run; `media_pause` fallback for players that cannot stop.
- Safety net: check after Home Assistant has started, after editing the rule, when the rule is
  switched on and every 30 s.
- Entities per rule: switch *Blocklist active*, sensor *Last blocked* (timestamp + details),
  sensor *Blocked plays* (total increasing). State survives restarts.
- Event `media_content_guard_blocked` and a logbook entry for every stop.
- Actions `add_keyword` and `remove_keyword`.
- Repair issue for watched players that no longer exist; diagnostics without personal data.
- Translations: English, German, Spanish, French.

[1.0.0]: https://github.com/Jo-Highness/media_content_guard/releases/tag/v1.0.0
