# Elsner WS1000 – Home Assistant Custom Integration

Local Home Assistant integration for the **Elsner WS1000** building controller.

The integration communicates directly with the WS1000 over the local network using TCP port **4242**. No cloud service is required. Actuator names and supported physical drives are discovered dynamically from the controller; no actuator names are hard-coded.

## Features

### Actuators
- Automatic discovery of physical WS1000 actuators
- Separate Home Assistant device for every physical actuator
- Native Cover control for windows, awnings and blinds
- Open / close / stop
- Current travel position
- Writable travel position from 0–100 %
- Current blind lamella position
- Writable lamella position from 0–100 % for blinds
- Operating mode **Auto / Manual**
- **Auto-Sperre** per actuator
- **Aktor-Sperre** per actuator
- Per-actuator rain, wind and frost alarm states
- Additional decoded WS1000 GUI_DF status information

### Building automation
- **Gebäude auf Automatik** button on the WS1000 controller device
- The button is available when at least one actuator is in Manual mode
- Pressing it returns all currently manual actuators to Automatic mode
- Uses the confirmed per-actuator Auto command; no undocumented broadcast command is used

### Weather
- Inside temperature
- Inside humidity
- Outside temperature
- Brightness / illuminance
- Wind speed
- Rain status

The WS1000 itself remains responsible for its protection and automation logic. Home Assistant reads states and sends control commands but does not replace the controller's internal safety functions.

## Communication and polling

Communication is completely local over TCP port **4242**.

The integration uses a fixed polling interval of **1 second**. The polling interval is intentionally not configurable in the Home Assistant setup. Testing showed that a 1-second interval provides responsive state updates while keeping the configuration simple.

## Installation

### HACS

1. Add this GitHub repository to HACS as a **Custom repository** with category **Integration**.
2. Install **Elsner WS1000** in HACS.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → Elsner WS1000**.
5. Enter the IP address or hostname of the WS1000.

### Manual installation

Copy:

`custom_components/elsner_ws1000`

to:

`/config/custom_components/elsner_ws1000`

Restart Home Assistant.

Then open:

**Settings → Devices & services → Add integration → Elsner WS1000**

Enter only the **IP address or hostname** of the WS1000. TCP port 4242 and the 1-second polling interval are handled automatically.

The host can later be changed through the integration's reconfigure dialog.

## Device structure

Home Assistant creates:

- one controller device **Elsner WS1000** for weather data and controller functions
- one child device for every discovered physical actuator

The actuator device name is read directly from the WS1000 configuration. Actuator identity is based on the WS1000 object ID and therefore does not depend on the configured display name.

Virtual/group actuators are deliberately ignored.

## Position semantics

The native WS1000 position scale is:

- `0 %` = fully up / retracted
- `100 %` = fully down / extended

Home Assistant Cover position uses the opposite convention. The integration therefore inverts the value only for the native HA Cover state. Dedicated WS1000 position sensors and sliders retain the original Elsner 0–100 % semantics.

For blinds, direct travel-position commands use the WS1000 combined position/lamella telegram:

- travel position `0 %` → lamella position `0 %`
- travel position `100 %` → lamella position `100 %`
- intermediate travel positions preserve the currently known lamella target/value

Windows and awnings are unaffected by this blind-specific behavior.

## Stop behavior

Home Assistant's native Cover STOP command uses the experimentally validated WS1000 stop sequence. Full UP and DOWN commands remain independent.

## Alarm states

Per-actuator rain, wind and frost alarms use the decoded WS1000 GUI_DF status values:

- `0` = Disabled
- `1` = Visible
- `2` = Highlighted / Active
- `3` = Alarm

Dedicated binary alarm entities are active only when the corresponding raw state is `3`.

## Compatibility

Developed and tested as a Home Assistant custom integration against a real Elsner WS1000 installation.

The integration uses Home Assistant's current device-registry API, including `via_device_id`, and avoids the deprecated `via_device` parameter.

## Version 1.19.0

- Fixed polling interval at **1 second**
- Removed polling-interval input from initial setup
- Removed polling-interval input from reconfiguration
- Setup now requires only the WS1000 IP address or hostname
- Cleaned and consolidated README for the current integration state
- No changes to the validated WS1000 protocol implementation or actuator-control behavior from 1.17

## Previous notable changes

### 1.17
- Added the Elsner-style **Gebäude auf Automatik** controller button
- Includes the blind end-position correction introduced during the 1.16.x development cycle

### 1.16
- Added **Aktor-Sperre** using the official Elsner `Send_WS1000_Automatik_Flags` structure
- Corrected blind end positions so direct `0 %` and `100 %` travel commands send the corresponding lamella end position in the same WS1000 telegram

### 1.15
- Added current position to native Home Assistant Cover entities
- Preserved native Elsner position semantics for dedicated position sensors and controls

### 1.14
- Added writable travel-position and lamella-position controls
- Corrected actual/target position mapping
- Added validated direct WS1000 position commands

### 1.13
- Added decoded per-actuator GUI_DF status entities
- Corrected GUI_DF state semantics

### 1.10
- Added per-actuator rain, wind and frost alarm states

### 1.09
- Added native Home Assistant Cover STOP support and refined the stop implementation

### 1.02
- Introduced the controller/child-device structure used by the current integration

## Notes

This is an independent Home Assistant custom integration for Elsner WS1000 controllers. It communicates locally with the controller and does not require an external cloud service.


## V1.21.0 - native Home Assistant Child Devices

Basis: V1.19.1

Gerätemodell:
- Elsner WS1000 bleibt das physische Hauptgerät.
- Physische Aktoren werden als native Home-Assistant-Child-Devices angelegt.
- Benutzergruppen werden ebenfalls als native Child Devices angelegt.
- Keine künstlichen 00/01/02-Präfixe.

Gruppen:
- Die WS1000 stellt 20 Benutzergruppen bereit.
- Protokollseitig sind dies die Objekt-IDs 0..19.
- Interne System-/Alarmobjekte wie Einbruch, Sabotage, Verschluss,
  Störung, Überfall und technische Alarme (z.B. 70..76) werden niemals
  als Gruppen-Cover angelegt.
- Gruppen besitzen nur Hoch, Stop und Runter.
- Keine Prozentposition und keine Lamellensteuerung für Gruppen.

Migration:
- Vorhandene Aktorgeräte werden soweit möglich in-place auf gültige
  Child-Device-Identifier migriert, damit ihre HA-Geräte-ID erhalten bleibt.
- Echte Gruppen aus unseren V1.20-Testversionen werden ebenfalls migriert.
- Interne/technische Testgruppen ab ID 20 werden aus Device- und
  Entity-Registry entfernt.

Hinweis:
Home Assistant Child Devices wurden mit Core 2026.9 eingeführt und sind
laut HA-Entwicklerdokumentation noch ein neues API-Konzept.


## V1.21.1 - Zwei unabhängige Parent-Geräte

Native HA-Struktur:
- `Elsner WS1000`
  - alle physischen Aktoren als Child Devices
- `Elsner WS1000 - Gruppen`
  - ausschließlich die 20 Benutzergruppen-Slots (Protokoll-IDs 0..19)
    als Child Devices

Es gibt keine verschachtelten Child Devices. Beide Parent-Geräte sind
gleichrangige Main Devices derselben Integration.

Keine 00/01/02-Präfixe.

Mehrsprachigkeit:
Die semantische Bezeichnung für den Gruppen-Parent ist in den
Übersetzungsdateien bereits als `Gruppen` / `Groups` vorbereitet. Der
Device-Registry-Anzeigename selbst ist in dieser Version weiterhin
`Elsner WS1000 - Gruppen`, da Home Assistant Device-Namen nicht über
die normale Entity-Translation-API dynamisch lokalisiert.

Die bestätigte Gruppenbegrenzung 0..19 bleibt unverändert; interne
System-/Alarmobjekte 70..76 werden nicht exponiert.


## V1.21.2 - Migration der Gruppen auf den zweiten Parent

Fix für Upgrades von V1.21.0/V1.21.1:

Home Assistant erlaubt bei Child Devices kein Reparenting in-place.
Bereits vorhandene Gruppen-Children unter `Elsner WS1000` werden deshalb
beim Start einmal aus der Device Registry entfernt und anschließend durch
die normale Entity-Registrierung mit demselben Gruppen-Identifier unter
`Elsner WS1000 - Gruppen` neu angelegt.

Zielstruktur:

Elsner WS1000
- Fenster
- Grosse Markise
- Jalousie ...
- Kleine Markise

Elsner WS1000 - Gruppen
- ALLE ohne Fenster
- Jal. Str. / Gr. Markise
- Jalousien
- Markisen

Entity-Unique-IDs und Gruppensteuerung bleiben unverändert.
Gruppen bleiben strikt auf Protokoll-IDs 0..19 begrenzt.


## V1.22.0 - Code Cleanup ohne Funktionsänderung

Basis: V1.21.2

Aufgeräumt:
- WS1000-Konfiguration wird beim Setup nur noch einmal gelesen.
  `discover_topology()` liefert Aktoren und Benutzergruppen gemeinsam.
- Fahrlogik für Aktoren und Gruppen nutzt intern gemeinsame Helfer.
  Die öffentlichen Methoden und Telegrammsequenzen bleiben unverändert.
- `cover.py` greift für den Gruppen-STOP nicht mehr direkt auf die private
  `_sequence()`-Methode des Protokollclients zu.
- Öffentliche Fallback-Methode `group_stop_unknown_direction()` ergänzt.
- Nicht verwendete `channel`-Felder aus den Topologie-Dataclasses entfernt.
- Registry-Migrationscode in `__init__.py` klarer gegliedert.
- Unbenutzte vorbereitende `device_labels`-Übersetzung entfernt; bestehende
  funktionierende Übersetzungen bleiben unverändert.

Bewusst unverändert:
- Entity Unique IDs
- Entity-Namen und Entity IDs
- Device-Identifier
- beide Parent-Geräte und Child-Device-Hierarchie
- Wetter-/GUI_DF-/Alarmdecodierung
- Position/Lamellensteuerung
- Auto/Manuell, Auto-Sperre und Aktor-Sperre
- Smart STOP
- Gruppensteuerung und Gruppenbereich 0..19
- alle bestätigten Telegrammbytes und Fahrsequenzen


## V1.22.1 - Home Assistant API / Startup Cleanup

Fixes:
- `WS1000GroupCover` no longer uses the reserved Home Assistant Entity
  attribute `group`. The protocol object is stored as `ws1000_group`.
  This removes the HA 2027.2 compatibility warning:
  `sets a group attribute ... which is not a Group instance`.
- Parent device IDs for both native Child-Device trees are cached once during
  integration setup. Per-entity DeviceInfo construction no longer performs
  repeated Device Registry lookups for the same parent IDs.
- This reduces unnecessary startup work for the large number of GUI_DF
  entities and addresses the observed one-off slow-state warning path.

Unchanged:
- entity unique IDs and entity names
- device identifiers / child hierarchy
- protocol bytes and movement commands
- sensors, alarms, GUI_DF semantics
- positioning, Smart STOP and group control


## V1.3.0 - New master version

Release/versioning cleanup only. No functional protocol or entity behavior was intentionally changed compared with V1.23.0.

- version normalized to `1.3.0` for the new GitHub/HACS master
- runtime logic unchanged
- protocol commands unchanged
- entity unique IDs unchanged
- device identifiers unchanged
- migration behavior unchanged


## V1.23.0 - Structural cleanup

No functional protocol or entity behavior was intentionally changed.

- registry migration/cleanup moved to `migration.py`
- `__init__.py` reduced to runtime data and config-entry lifecycle
- unused compatibility discovery wrappers removed
- unused protocol helper removed
- development/POC history moved from runtime code to `PROTOCOL.md`
- established German fixed entity labels centralized in `labels.py`
- dynamic WS1000 names remain dynamic and unchanged
- protocol constants, command sequences, entity unique IDs and device
  identifiers were checked automatically against V1.22.1
