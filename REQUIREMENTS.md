---
service: media_content_guard
typ: requirements
version: 1.0
status: current
stand: 2026-10-25
quellen: [homeassistant/packages/sonos_move.yaml (Ursprung), Auftrag 2026-10-25, ADR a333581c]
---

# Anforderungen: Media Content Guard (HA Custom Integration)

> Code-unabhängige Soll-Beschreibung für eine Neuentwicklung von Grund auf (WAS/WARUM).

## 1. Zweck & Kontext
HACS-installierbare Home-Assistant-Integration (Domain `media_content_guard`), die auf ausgewählten
`media_player` die Wiedergabe **stoppt, sobald die Medien-Metadaten ein Stichwort aus einer
Sperrliste enthalten**. Ursprung: HA-Package `sonos_move.yaml`, das Kinder-Hörspiele
(Lego, Die drei ???, TKKG, Bibi Blocksberg …) auf der Wohnzimmer-Box (Sonos Move) unterband.
- **Nutzer:** HA-Haushalt (Eltern pflegen die Liste).
- **Use-Cases:** bestimmte Inhalte in bestimmten Räumen unterbinden; Liste ohne YAML pflegen;
  bei Stopp benachrichtigt werden.

## 2. Geltungsbereich
**In Scope:** UI-Konfiguration, Stichwortabgleich gegen Player-Attribute, Durchsetzung (Stopp-Schleife),
Ein/Aus je Regel, Statistik/letzte Sperre, Ereignis + Logbuch, Aktionen zum Pflegen der Liste.
**Out of Scope:** Zeitbudgets (siehe media_time_guard), Allowlist, Altersfreigaben/Cloud-Kataloge,
Vorab-Blockieren vor Wiedergabebeginn, Inhalte ohne Metadaten.

## 3. Funktionale Anforderungen
- **FR-1 Regeln (nur UI):** beliebig viele Regeln; je Regel eindeutiger Name, ≥1 `media_player`
  (ein Player darf in mehreren Regeln sein), Sperrliste (mehrzeilig, ein Stichwort je Zeile, ≥1),
  durchsuchte Felder (Auswahl aus Titel, Album, Interpret, Content-ID, Playlist, Serie, Sender, App,
  Quelle; Default die ersten vier, ≥1). Alles nachträglich änderbar; Änderung wirkt sofort.
- **FR-2 Abgleich:** Teilstring, Groß-/Kleinschreibung egal (Unicode-normalisiert), Leerraum getrimmt;
  leere Zeilen/Duplikate fallen weg; erstes Listen-Stichwort mit Treffer wird gemeldet.
- **FR-3 Auslöser:** Wechsel auf `playing`; Änderung eines durchsuchten Attributs während `playing`;
  nach HA-Start; nach Regeländerung; beim Einschalten; periodisch (≤30 s) als Sicherheitsnetz.
- **FR-4 Durchsetzung:** bei Treffer stoppen; solange weiterhin `playing` + Treffer: alle 2 s erneut
  (jede Runde frisch prüfen), begrenzt (≈30 s) je Durchlauf, danach übernimmt FR-3-Periodik.
  Fallback Pause, wenn Player nicht stoppen kann. Fehler beim Stoppen loggen, nicht abbrechen.
- **FR-5 Schalter je Regel** („Sperrliste aktiv"), Zustand persistent; aus = keine Eingriffe.
- **FR-6 Sensoren je Regel:** letzte Sperre (Zeitstempel + Player, Stichwort, Fundfeld, Titel,
  Interpret, Album) und Zähler (steigend), persistent.
- **FR-7 Ereignis** `media_content_guard_blocked` (einmal je Durchlauf) + Logbuch-Eintrag
  in UI-Sprache.
- **FR-8 Aktionen** `add_keyword`, `remove_keyword` (Ziel per Regelname oder config_entry_id;
  ein Stichwort oder Liste); remove meldet, wenn nichts entfernt wurde.
- **FR-9 Reparaturhinweis** für nicht (mehr) existierende Player.

## 4. Nicht-funktionale Anforderungen
- **NFR-1** vollständig async, lokal, keine externen Abhängigkeiten.
- **NFR-2 Robustheit** mind. wie Ursprungs-Package (frische Prüfung, Schleife, keine
  String-Boolean-Fehler); verpasste Events werden durch Periodik/Startcheck aufgefangen.
- **NFR-3** keine Last durch Positions-Updates (nur relevante Attributwechsel auswerten).
- **NFR-4** Entity-IDs stabil bei Umbenennung; Zustand überlebt Neustart/Reload.
- **NFR-5** HACS/hassfest-konform; Mindest-HA 2025.2; Übersetzungen EN/DE/ES/FR.
- **NFR-6** Diagnose ohne personenbezogene Daten (Namen, Entity-IDs, Stichwörter).

## 5. Schnittstellen
- Eingang: `media_player`-States/Attribute. Ausgang: `media_player.media_stop`/`media_pause`,
  Event, Logbuch.
- Entitäten: `switch.content_guard_<regel>_active`, `sensor.content_guard_<regel>_last_blocked`,
  `sensor.content_guard_<regel>_blocked_count`.

## 6. Datenmodell
- Regel-Konfig: name, players[], keywords[], fields[].
- Laufzeit je Regel (persistent): enabled, block_count, last_block{…}.

## 7. Akzeptanzkriterien
- Abspielen eines Titels mit Stichwort auf überwachtem Player → binnen Sekunden gestoppt,
  Sensor/Logbuch/Event gesetzt.
- Harmloser Inhalt → kein Eingriff. Schalter aus → kein Eingriff; wieder an → sofortige Prüfung.
- Player ignoriert Stopp → wiederholte Versuche, kein Endlos-Hämmern, Periodik greift.
- Stichwort per Aktion ergänzt → laufender Inhalt wird sofort geprüft.
