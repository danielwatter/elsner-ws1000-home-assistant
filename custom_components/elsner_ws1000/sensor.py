from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfRatio, UnitOfTemperature

from .entity import WS1000Entity, drive_device_info
from .labels import (
    GUI_STATE_ACTIVE,
    GUI_STATE_ALARM,
    GUI_STATE_DISABLED,
    GUI_STATE_VISIBLE,
    NAME_BRIGHTNESS,
    NAME_INSIDE_HUMIDITY,
    NAME_INSIDE_TEMPERATURE,
    NAME_OUTSIDE_TEMPERATURE,
    NAME_POSITION,
    NAME_TILT_POSITION,
    NAME_WIND_SPEED,
)


@dataclass(frozen=True)
class Desc:
    key: str
    name: str
    device_class: SensorDeviceClass | None
    unit: str | None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


@dataclass(frozen=True)
class GuiDesc:
    key: str
    name: str
    icon: str


DESCS = (
    Desc("inside_temperature", NAME_INSIDE_TEMPERATURE, SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    Desc("inside_humidity", NAME_INSIDE_HUMIDITY, SensorDeviceClass.HUMIDITY, UnitOfRatio.PERCENTAGE),
    Desc("outside_temperature", NAME_OUTSIDE_TEMPERATURE, SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
)

# GUI_DF fields that are not already represented by an existing control or
# dedicated alarm entity. These are read-only status/reason sensors.
GUI_DESCS = (
    GuiDesc("smoke_alarm", "Rauchalarm", "mdi:smoke-detector-alert"),
    GuiDesc("motion_alarm", "Bewegungsalarm", "mdi:motion-sensor"),
    GuiDesc("automatic_delay", "Automatikverzögerung", "mdi:timer-sand"),
    GuiDesc("wind_direction", "Windrichtung", "mdi:compass-outline"),
    GuiDesc("wind_gap", "Windlücke", "mdi:weather-windy-variant"),
    GuiDesc("air_condition", "Klimaanlage", "mdi:air-conditioner"),
    GuiDesc("fresh_air", "Frischluft", "mdi:air-filter"),
    GuiDesc("outdoor_temp", "Außentemperatur-Bedingung", "mdi:thermometer"),
    GuiDesc("indoor_temp", "Innentemperatur-Bedingung", "mdi:home-thermometer-outline"),
    GuiDesc("indoor_co2", "CO₂-Bedingung", "mdi:molecule-co2"),
    GuiDesc("indoor_rh", "Luftfeuchte-Bedingung", "mdi:water-percent"),
    GuiDesc("opening_time", "Öffnungszeit", "mdi:clock-start"),
    GuiDesc("keep_close_time", "Geschlossenhaltezeit", "mdi:clock-lock-outline"),
    GuiDesc("sun", "Sonne", "mdi:white-balance-sunny"),
    GuiDesc("cloud", "Wolke", "mdi:weather-cloudy"),
    GuiDesc("sun_cloud_wait", "Sonne/Wolke Wartezeit", "mdi:timer-sand"),
    GuiDesc("night", "Nacht", "mdi:weather-night"),
    GuiDesc("solar_position", "Sonnenstand", "mdi:sun-angle-outline"),
    GuiDesc("driving_limit", "Fahrbegrenzung", "mdi:arrow-collapse-vertical"),
    GuiDesc("night_cooling", "Nachtrückkühlung", "mdi:snowflake-thermometer"),
    GuiDesc("safety", "Sicherheitssperre", "mdi:shield-lock-outline"),
    GuiDesc("sensor_error", "Sensorfehler", "mdi:alert-circle-outline"),
    GuiDesc("clock_timer", "Zeitschaltuhr", "mdi:timer-outline"),
    GuiDesc("outdoor_temp_block_hot", "Außentemperatur-Sperre warm", "mdi:thermometer-high"),
    GuiDesc("outdoor_temp_block_cold", "Außentemperatur-Sperre kalt", "mdi:thermometer-low"),
    GuiDesc("indoor_temp_block_cold", "Innentemperatur-Sperre kalt", "mdi:home-thermometer-outline"),
    GuiDesc("recirculation_heat_gain", "Umluft Wärmegewinn", "mdi:autorenew"),
    GuiDesc("recirculation_condensation_reduction", "Umluft Kondenswasserreduzierung", "mdi:autorenew"),
    GuiDesc("emergency_mode", "Notbetrieb", "mdi:alert-octagon-outline"),
    GuiDesc("actuator_lock_info", "Aktor-Sperre", "mdi:lock-outline"),
    GuiDesc("air_quality_block", "Luftqualitäts-Sperre", "mdi:air-filter"),
    GuiDesc("hcl_start_stop", "HCL Start/Stopp", "mdi:lightbulb-auto-outline"),
    GuiDesc("fancoil_auto", "Fancoil Auto", "mdi:fan-auto"),
    GuiDesc("reference_run", "Referenzfahrt", "mdi:axis-arrow"),
)

GUI_DESC_BY_KEY = {desc.key: desc for desc in GUI_DESCS}
GUI_STATE_NAMES = {
    0: GUI_STATE_DISABLED,
    1: GUI_STATE_VISIBLE,
    2: GUI_STATE_ACTIVE,
    3: GUI_STATE_ALARM,
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data.coordinator
    entities = [WS1000Sensor(coordinator, entry, d) for d in DESCS]
    entities.append(WS1000BrightnessSensor(coordinator, entry))
    entities.append(WS1000CombinedWindSensor(coordinator, entry))

    for drive in entry.runtime_data.drives:
        entities.append(WS1000DrivePositionSensor(coordinator, entry, drive))
        if drive.kind == "blind":
            entities.append(WS1000DriveTiltSensor(coordinator, entry, drive))

        # GUI_DF status entities are deliberately created for every actuator
        # during integration setup, regardless of their current raw value.
        #
        # Reason: GUI_DF_DISABLED (0) can also occur temporarily when an
        # actuator is in manual mode. A field that is 0 at startup can later
        # become VISIBLE/HIGHLIGHTED/ALARM without the integration being
        # reloaded. Therefore entity existence must not depend on the current
        # GUI_DF state.
        for desc in GUI_DESCS:
            entities.append(
                WS1000DriveGuiStatusSensor(
                    coordinator,
                    entry,
                    drive,
                    desc,
                )
            )

    async_add_entities(entities)


class WS1000Sensor(WS1000Entity, SensorEntity):
    def __init__(self, coordinator, entry, desc):
        super().__init__(coordinator, entry, f"sensor_{desc.key}")
        self.desc = desc
        self._attr_name = desc.name
        self._attr_device_class = desc.device_class
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_state_class = desc.state_class

    @property
    def native_value(self):
        return self.coordinator.data["weather"].get(self.desc.key)


class WS1000BrightnessSensor(WS1000Entity, SensorEntity):
    _attr_name = NAME_BRIGHTNESS
    _attr_icon = "mdi:white-balance-sunny"
    _attr_state_class = None
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "sensor_illuminance_dynamic")

    @property
    def native_value(self):
        lux = self.coordinator.data["weather"].get("illuminance")
        if lux is None:
            return None
        if lux < 1000:
            return f"{int(round(lux))} lx"
        return f"{lux / 1000.0:.1f} klx"


class WS1000CombinedWindSensor(WS1000Entity, SensorEntity):
    _attr_name = NAME_WIND_SPEED
    _attr_icon = "mdi:weather-windy"
    _attr_state_class = None
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "sensor_wind_combined")

    @property
    def native_value(self):
        weather = self.coordinator.data["weather"]
        ms = weather.get("wind_speed_ms")
        kmh = weather.get("wind_speed_kmh")
        if ms is None or kmh is None:
            return None
        return f"{ms:.1f} m/s | {kmh:.2f} km/h"


class WS1000DrivePositionSensor(WS1000Entity, SensorEntity):
    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"position_{drive.object_id}")
        self.drive = drive
        self._attr_name = NAME_POSITION

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def native_value(self):
        return self.coordinator.data["drives"][self.drive.object_id].get("position")


class WS1000DriveTiltSensor(WS1000Entity, SensorEntity):
    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"tilt_{drive.object_id}")
        self.drive = drive
        self._attr_name = NAME_TILT_POSITION

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def native_value(self):
        return self.coordinator.data["drives"][self.drive.object_id].get("tilt")


class WS1000DriveGuiStatusSensor(WS1000Entity, SensorEntity):
    """Read-only four-state GUI_DF symbol/status for one WS1000 actuator."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = (GUI_STATE_DISABLED, GUI_STATE_VISIBLE, GUI_STATE_ACTIVE, GUI_STATE_ALARM)
    _attr_state_class = None
    _attr_native_unit_of_measurement = None

    def __init__(self, coordinator, entry, drive, desc):
        super().__init__(
            coordinator,
            entry,
            f"gui_{drive.object_id}_{desc.key}",
        )
        self.drive = drive
        self.desc = desc
        self._attr_name = desc.name
        self._attr_icon = desc.icon

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def native_value(self):
        raw = (
            self.coordinator.data["drives"]
            .get(self.drive.object_id, {})
            .get("gui_df", {})
            .get(self.desc.key)
        )
        if raw is None:
            return None
        return GUI_STATE_NAMES.get(raw)

    @property
    def extra_state_attributes(self):
        raw = (
            self.coordinator.data["drives"]
            .get(self.drive.object_id, {})
            .get("gui_df", {})
            .get(self.desc.key)
        )
        return {
            "raw_value": raw,
            "elsner_state": {
                0: "GUI_DF_DISABLED",
                1: "GUI_DF_VISIBLE",
                2: "GUI_DF_HIGHLIGHTED",
                3: "GUI_DF_ALARM",
            }.get(raw, "UNKNOWN"),
        }
