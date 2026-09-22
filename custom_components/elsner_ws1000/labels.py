"""Stable internal keys used by WS1000 entities.

User-facing text is provided exclusively through Home Assistant translation
files. Internal option and enum values stay language-neutral so automations
remain independent of the configured Home Assistant language.
"""

MODE_AUTO = "auto"
MODE_MANUAL = "manual"

GUI_STATE_DISABLED = "disabled"
GUI_STATE_VISIBLE = "visible"
GUI_STATE_ACTIVE = "active"
GUI_STATE_ALARM = "alarm"

GUI_STATE_BY_RAW = {
    0: GUI_STATE_DISABLED,
    1: GUI_STATE_VISIBLE,
    2: GUI_STATE_ACTIVE,
    3: GUI_STATE_ALARM,
}
