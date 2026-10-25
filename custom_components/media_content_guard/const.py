"""Constants for the Media Content Guard integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "media_content_guard"

# --- Config / Options keys -------------------------------------------------
CONF_NAME = "name"
CONF_PLAYERS = "players"
CONF_KEYWORDS = "keywords"  # stored as list[str]; edited as one keyword per line
CONF_FIELDS = "fields"  # media_player attributes that are searched

# Media player attributes that can be searched. The first four are the ones
# the original YAML automation checked and are the default.
FIELD_TITLE = "media_title"
FIELD_ALBUM = "media_album_name"
FIELD_ARTIST = "media_artist"
FIELD_CONTENT_ID = "media_content_id"
FIELD_PLAYLIST = "media_playlist"
FIELD_SERIES = "media_series_title"
FIELD_CHANNEL = "media_channel"
FIELD_APP = "app_name"
FIELD_SOURCE = "source"

AVAILABLE_FIELDS = [
    FIELD_TITLE,
    FIELD_ALBUM,
    FIELD_ARTIST,
    FIELD_CONTENT_ID,
    FIELD_PLAYLIST,
    FIELD_SERIES,
    FIELD_CHANNEL,
    FIELD_APP,
    FIELD_SOURCE,
]
DEFAULT_FIELDS = [FIELD_TITLE, FIELD_ALBUM, FIELD_ARTIST, FIELD_CONTENT_ID]

# --- Player states ---------------------------------------------------------
STATE_PLAYING = "playing"

# --- Timing ----------------------------------------------------------------
# Pause between two stop attempts while blocked content keeps playing. Sonos
# sometimes resumes (or the app retries) right after a stop; the loop catches
# that. Same rhythm as the original automation.
STOP_RETRY_DELAY = 2.0
# Upper bound for one enforcement run (MAX_STOP_ATTEMPTS * STOP_RETRY_DELAY
# seconds). A player that ignores the stop is not hammered forever; the
# periodic check starts a new run.
MAX_STOP_ATTEMPTS = 15
# Timeout for a single media_stop/media_pause call.
STOP_CALL_TIMEOUT = 10.0
# Redundant periodic check of all players. Catches state changes that were
# missed (e.g. during a restart) and players that resumed after a run ended.
POLL_INTERVAL = timedelta(seconds=30)

# --- Storage ---------------------------------------------------------------
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}."
SAVE_DELAY = 5

# --- Services --------------------------------------------------------------
SERVICE_ADD_KEYWORD = "add_keyword"
SERVICE_REMOVE_KEYWORD = "remove_keyword"

ATTR_RULE = "rule"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_KEYWORD = "keyword"

# --- Events ----------------------------------------------------------------
EVENT_BLOCKED = f"{DOMAIN}_blocked"

# --- Entity / event attribute keys -----------------------------------------
ATTR_RULE_NAME = "rule_name"
ATTR_ENTRY_ID = "entry_id"
ATTR_PLAYER = "player"
ATTR_MATCHED_KEYWORD = "matched_keyword"
ATTR_MATCHED_FIELD = "matched_field"
ATTR_MEDIA_TITLE = "media_title"
ATTR_MEDIA_ARTIST = "media_artist"
ATTR_MEDIA_ALBUM = "media_album_name"
ATTR_BLOCKED_AT = "blocked_at"
ATTR_KEYWORD_COUNT = "keyword_count"
ATTR_PLAYERS = "players"
