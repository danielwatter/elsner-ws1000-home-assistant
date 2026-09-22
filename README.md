# Elsner WS1000 – Home Assistant Custom Integration

Local Home Assistant integration for the **Elsner WS1000** building controller.

The integration communicates directly with the WS1000 over the local network using TCP port **4242**. No cloud service is required. Actuator names and supported physical drives are discovered dynamically from the controller; no actuator names are hard-coded.

## Features

### Actuators
- Automatic discovery of physical WS1000 actuators
- Separate Home Assistant child device for every physical actuator
- Native Cover control for windows, awnings and blinds
- Open / close / stop
- Current travel position
- Writable travel position from 0–100 %
- Current blind slat position
- Writable slat position from 0–100 % for blinds
- Operating mode **Automatic / Manual**
- Automatic lock per actuator
- Actuator lock per actuator
- Per-actuator rain, wind and frost alarm states
- Additional decoded WS1000 GUI_DF status information

### Building automation
- **Building automatic mode** button on the WS1000 controller device
- The button is available when at least one actuator is in Manual mode
- Pressing it returns all currently manual actuators to Automatic mode
- Uses the confirmed per-actuator automatic-mode command; no undocumented broadcast command is used

### Weather
- Indoor temperature
- Indoor humidity
- Outdoor temperature
- Brightness / illuminance
- Wind speed
- Rain status

### Localization
- Full German and English localization for config flow, entity names, device names and translated enum/select states
- Internal select and enum values are language-neutral (`auto`, `manual`, `disabled`, `visible`, `active`, `alarm`)
- Entity unique IDs and device identifiers remain unchanged across language changes and upgrades

The WS1000 itself remains responsible for its protection and automation logic. Home Assistant reads states and sends control commands but does not replace the controller's internal safety functions.

## Communication and polling

Communication is completely local over TCP port **4242**.

The integration uses a fixed polling interval of **1 second**. The polling interval is intentionally not configurable in the Home Assistant setup. Testing showed that a 1-second interval provides responsive state updates while keeping the configuration simple.

## Installation

### HACS

1. Install **Elsner WS1000** from HACS.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Elsner WS1000**.
4. Enter the IP address or hostname of the WS1000.

Until the repository is included in the HACS default catalog, add this GitHub repository to HACS as a **Custom repository** with category **Integration**.

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
- one translated groups parent device for WS1000 user groups
- one child device for every discovered physical actuator
- one child device for every exposed WS1000 user group

The actuator and group device names are read directly from the WS1000 configuration. Their identity is based on the WS1000 object ID and therefore does not depend on the configured display name.

Only the confirmed WS1000 user-group range 0–19 is exposed. Internal system/alarm objects are not exposed as group covers.

## Position semantics

The native WS1000 position scale is:

- `0 %` = fully up / retracted
- `100 %` = fully down / extended

Home Assistant Cover position uses the opposite convention. The integration therefore inverts the value only for the native HA Cover state. Dedicated WS1000 position sensors and sliders retain the original Elsner 0–100 % semantics.

For blinds, direct travel-position commands use the WS1000 combined position/slat telegram:

- travel position `0 %` → slat position `0 %`
- travel position `100 %` → slat position `100 %`
- intermediate travel positions preserve the currently known slat target/value

Windows and awnings are unaffected by this blind-specific behavior.

## Stop behavior

Home Assistant's native Cover STOP command uses the experimentally validated WS1000 stop sequence. Full UP and DOWN commands remain independent.

## Alarm and GUI_DF states

Per-actuator rain, wind and frost alarms use the decoded WS1000 GUI_DF status values:

- raw `0` = `disabled`
- raw `1` = `visible`
- raw `2` = `active`
- raw `3` = `alarm`

Home Assistant translates these language-neutral internal states for display. Dedicated binary alarm entities are active only when the corresponding raw state is `3`.

## Automation compatibility note for 1.4.0

Version 1.4.0 changes the raw operating-mode options from the previous localized values to stable language-neutral values:

- previous localized automatic option → `auto`
- previous localized manual option → `manual`

GUI_DF enum sensor states are likewise language-neutral internally:

- previous localized disabled state → `disabled`
- previous localized visible state → `visible`
- previous localized active state → `active`
- alarm state remains language-neutral as `alarm`

Existing entity unique IDs and device identifiers are unchanged. Existing entity IDs are preserved by the Home Assistant entity registry. Automations or templates that compare the previous localized raw state strings must be updated once.

## Compatibility

Developed and tested as a Home Assistant custom integration against a real Elsner WS1000 installation.

The integration uses Home Assistant's current device-registry API, including native child devices and translated entity/device metadata.

## Version history

### 1.4.0 – Full German and English localization

- Added complete German and English translations for entity names, the groups parent device, config flow and enum/select states
- Replaced localized raw operating-mode values with stable `auto` / `manual` options
- Replaced localized GUI_DF enum values with stable `disabled` / `visible` / `active` / `alarm` states
- Kept entity unique IDs, device identifiers, protocol bytes, movement commands and migration behavior unchanged
- Converted integration source comments and changelog text to English
- Updated the documentation for the new language-neutral automation values

### 1.3.0 – First public GitHub/HACS master

- Normalized public versioning to `1.3.0`
- Added HACS packaging, validation workflows and public release metadata
- Runtime protocol and entity behavior remained aligned with the preceding 1.23.0 development master

### 1.23.0 – Structural cleanup

- Moved registry migration/cleanup to `migration.py`
- Reduced `__init__.py` to runtime data and config-entry lifecycle
- Removed unused compatibility discovery wrappers and protocol helpers
- Moved development/POC history from runtime code to `PROTOCOL.md`
- Centralized fixed entity labels in preparation for translation-key migration
- Kept protocol constants, command sequences, entity unique IDs and device identifiers unchanged

### 1.22.1 – Home Assistant API / startup cleanup

- `WS1000GroupCover` no longer uses the reserved Home Assistant Entity attribute `group`; the protocol object is stored as `ws1000_group`
- Cached parent device IDs for both native child-device trees during integration setup
- Reduced repeated Device Registry lookups during startup
- Kept protocol bytes, movement commands, entity unique IDs and GUI_DF semantics unchanged

### 1.22.0 – Code cleanup without functional changes

- Read WS1000 topology once during setup through `discover_topology()`
- Consolidated actuator and group movement helpers without changing public command behavior
- Added the public `group_stop_unknown_direction()` fallback
- Removed unused topology fields and obsolete translation preparation
- Kept entity IDs, device identifiers, protocol bytes, positioning, STOP behavior and group range unchanged

### 1.21.2 – Group migration to the dedicated groups parent

- Added upgrade handling for existing group child devices
- Recreated existing group child devices below the dedicated groups parent while keeping group identifiers and entity unique IDs stable
- Kept groups strictly limited to protocol object IDs 0–19

### 1.21.1 – Two independent parent devices

- Added one parent device for physical actuators and one independent parent device for user groups
- Kept both parents at the same hierarchy level; no nested child devices
- Kept the confirmed user-group range 0–19 and excluded internal system/alarm objects

### 1.21.0 – Native Home Assistant child devices

- Converted physical actuators to native Home Assistant child devices
- Added WS1000 user groups as native child devices
- Removed artificial numeric display prefixes
- Added migration for legacy actuator/group identifiers and cleanup of internal test groups

### 1.19.0

- Fixed polling interval at **1 second**
- Removed polling-interval input from setup and reconfiguration
- Setup requires only the WS1000 IP address or hostname
- Consolidated documentation for the current integration state

### 1.17

- Added the controller-wide automatic-mode button
- Included the blind end-position correction introduced during the 1.16.x development cycle

### 1.16

- Added actuator lock using the official Elsner automation-flags structure
- Corrected blind end positions so direct `0 %` and `100 %` travel commands send the corresponding slat end position in the same WS1000 telegram

### 1.15

- Added current position to native Home Assistant Cover entities
- Preserved native Elsner position semantics for dedicated position sensors and controls

### 1.14

- Added writable travel-position and slat-position controls
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

## License

This project is licensed under the GNU General Public License v3.0. See `LICENSE`.

## Notes

This is an independent Home Assistant custom integration for Elsner WS1000 controllers. It communicates locally with the controller and does not require an external cloud service.
