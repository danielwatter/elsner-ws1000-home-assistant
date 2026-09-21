# Elsner WS1000 protocol notes

This file records protocol decisions that were experimentally verified during
development. Runtime modules intentionally contain only the current behavior.

## Object ranges

- Physical actuators used by the integration: object IDs `100..107`.
- User-configurable WS1000 groups: protocol object IDs `0..19`.
- Internal security/alarm objects such as IDs `70..76` are not drive groups
  and are not exposed as cover entities.

## Drive commands

The actuator/group command payload uses data type `0x14`.

Confirmed sequences:

- Short up: `U -> u`
- Short down: `D -> d`
- Full up/retract: `U -> P -> p`
- Full down/extend: `D -> N -> n`

For a moving actuator, STOP is performed by a short command in the opposite
direction. For physical actuators the integration determines direction from
actual versus target position. For groups, the integration tracks the last
direction initiated by Home Assistant and uses a fallback sequence when the
direction is unknown.

## Direct actuator positioning

Physical actuators support the direct position command:

`0B <obj_hi> <obj_lo> 06 01 14 42 <position> <tilt> 00 00 63`

`0x42` is ASCII `B`; position and tilt are percentages `0..100`.

This command is intentionally not exposed for WS1000 groups: testing showed
that a group percentage value does not represent a usable aggregate target
position.

## Status mapping

The actuator status structure supplied by Elsner maps:

- byte 81: actual travel position (`SFB_Position_In_Percent`)
- byte 82: actual blind/tilt position (`SFB_Blind_In_Percent`)
- byte 108: target travel position (`SH_Target_Position_Percentage`)
- byte 109: target blind/tilt position (`SH_Target_Blind_Percentage`)

GUI_DF fields use the four states:

- `0` = disabled
- `1` = visible
- `2` = highlighted/active
- `3` = alarm

## Automatic flags

Data type `0x17` (`DT_AUTOMATIC_FLAG_DATA`) contains, in order:

1. automatic flag
2. frost flag
3. motor test flag
4. automatic lock
5. actuator lock
6. HCL on/off
7. fan auto
8. extension byte

Flag actions:

- `0` ignore
- `1` set
- `2` reset
- `3` set all slots
- `4` reset all slots

The current integration exposes the confirmed per-actuator controls required by
Home Assistant and leaves unrelated flags untouched.
