"""Tests for the pure keyword matching."""

from __future__ import annotations

from custom_components.media_content_guard.const import DEFAULT_FIELDS
from custom_components.media_content_guard.matching import (
    Match,
    find_match,
    keywords_to_text,
    normalize,
    parse_keywords,
)

KEYWORDS = ["Lego", "???", "Major Tom", "TKKG", "Bibi", "Gregs"]


def test_case_insensitive_substring():
    attrs = {"media_album_name": "  tkkg – Folge 200: Gefährliche Diamanten "}
    assert find_match(attrs, KEYWORDS, DEFAULT_FIELDS) == Match("TKKG", "media_album_name")


def test_question_marks_keyword():
    attrs = {"media_artist": "Die drei ???", "media_title": "Kapitel 1"}
    assert find_match(attrs, KEYWORDS, DEFAULT_FIELDS) == Match("???", "media_artist")


def test_content_id_is_searched():
    attrs = {"media_content_id": "x-sonos-http:librarytrack%3aLEGO_City.mp4"}
    assert find_match(attrs, KEYWORDS, DEFAULT_FIELDS).keyword == "Lego"


def test_harmless_content_and_missing_attributes():
    assert find_match({"media_title": "Bohemian Rhapsody"}, KEYWORDS, DEFAULT_FIELDS) is None
    assert find_match({}, KEYWORDS, DEFAULT_FIELDS) is None
    assert find_match({"media_title": None, "media_artist": ""}, KEYWORDS, DEFAULT_FIELDS) is None


def test_only_selected_fields_are_searched():
    attrs = {"media_playlist": "Bibi und Tina", "media_title": "Song"}
    assert find_match(attrs, KEYWORDS, DEFAULT_FIELDS) is None
    assert find_match(attrs, KEYWORDS, ["media_playlist"]) == Match("Bibi", "media_playlist")


def test_first_keyword_in_list_order_wins():
    attrs = {"media_title": "Bibi trifft Lego"}
    assert find_match(attrs, KEYWORDS, DEFAULT_FIELDS).keyword == "Lego"


def test_non_string_values_and_unicode():
    assert find_match({"media_title": 1234}, ["23"], DEFAULT_FIELDS) is not None
    # casefold: ß == ss, NFKC: full-width letters
    assert find_match({"media_title": "STRASSE"}, ["straße"], DEFAULT_FIELDS) is not None
    assert find_match({"media_title": "ＬＥＧＯ Ninjago"}, ["lego"], DEFAULT_FIELDS) is not None


def test_blank_keywords_never_match():
    assert find_match({"media_title": "x"}, ["", "  "], DEFAULT_FIELDS) is None


def test_parse_keywords():
    raw = "Lego\n\n  TKKG  \nlego\r\n???\n"
    assert parse_keywords(raw) == ["Lego", "TKKG", "???"]
    assert parse_keywords(["a", " A ", "b"]) == ["a", "b"]
    assert parse_keywords(None) == []
    assert keywords_to_text(["a", "b"]) == "a\nb"


def test_normalize():
    assert normalize(None) == ""
    assert normalize("  Bibi  ") == "bibi"
