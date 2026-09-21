"""Fixed UI labels used by WS1000 entities.

The current release intentionally keeps the established German entity labels.
They are centralized here so a future translation-key migration can be done
without changing protocol or entity behavior.
"""

# Global/controller entities
NAME_BUILDING_AUTO = "Gebäude auf Automatik"
NAME_RAIN = "Regen"
NAME_INSIDE_TEMPERATURE = "Innentemperatur"
NAME_INSIDE_HUMIDITY = "Luftfeuchtigkeit innen"
NAME_OUTSIDE_TEMPERATURE = "Außentemperatur"
NAME_BRIGHTNESS = "Helligkeit"
NAME_WIND_SPEED = "Windgeschwindigkeit"

# Per-actuator entities
NAME_POSITION = "Position"
NAME_TILT_POSITION = "Lamellenposition"
NAME_DRIVE_POSITION = "Fahrposition"
NAME_MODE = "Betriebsmodus"
NAME_AUTO_LOCK = "Auto-Sperre"
NAME_ACTUATOR_LOCK = "Aktor-Sperre"
NAME_RAIN_ALARM = "Regenalarm"
NAME_WIND_ALARM = "Windalarm"
NAME_FROST_ALARM = "Frostalarm"

# GUI_DF enum states
GUI_STATE_DISABLED = "Deaktiviert"
GUI_STATE_VISIBLE = "Sichtbar"
GUI_STATE_ACTIVE = "Aktiv"
GUI_STATE_ALARM = "Alarm"
