from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfRatio, UnitOfTemperature

from .entity import WS1000Entity, drive_device_info
from .labels import GUI_STATE_ALARM, GUI_STATE_ACTIVE, GUI_STATE_BY_RAW, GUI_STATE_DISABLED, GUI_STATE_VISIBLE


@dataclass(frozen=True)
class Desc:
    key: str
    translation_key: str
    device_class: SensorDeviceClass | None
    unit: str | None
    state_class: SensorStateClass | None = SensorStateClass.MEASUREMENT


@dataclass(frozen=True)
class GuiDesc:
    key: str
    translation_key: str
    icon: str


DESCS = (
    Desc("inside_temperature", "inside_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
    Desc("inside_humidity", "inside_humidity", SensorDeviceClass.HUMIDITY, UnitOfRatio.PERCENTAGE),
    Desc("outside_temperature", "outside_temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
)

# GUI_DF fields that are not already represented by an existing control or
# dedicated alarm entity. These are read-only status/reason sensors.
GUI_DESCS = (
    GuiDesc("smoke_alarm", "gui_smoke_alarm", "mdi:smoke-detector-alert"),
    GuiDesc("motion_alarm", "gui_motion_alarm", "mdi:motion-sensor"),
    GuiDesc("automatic_delay", "gui_automatic_delay", "mdi:timer-sand"),
    GuiDesc("wind_direction", "gui_wind_direction", "mdi:compass-outline"),
    GuiDesc("wind_gap", "gui_wind_gap", "mdi:weather-windy-variant"),
    GuiDesc("air_condition", "gui_air_condition", "mdi:air-conditioner"),
    GuiDesc("fresh_air", "gui_fresh_air", "mdi:air-filter"),
    GuiDesc("outdoor_temp", "gui_outdoor_temperature_condition", "mdi:thermometer"),
    GuiDesc("indoor_temp", "gui_indoor_temperature_condition", "mdi:home-thermometer-outline"),
    GuiDesc("indoor_co2", "gui_indoor_co2_condition", "mdi:molecule-co2"),
    GuiDesc("indoor_rh", "gui_indoor_humidity_condition", "mdi:water-percent"),
    GuiDesc("opening_time", "gui_opening_time", "mdi:clock-start"),
    GuiDesc("keep_close_time", "gui_keep_closed_time", "mdi:clock-lock-outline"),
    GuiDesc("sun", "gui_sun", "mdi:white-balance-sunny"),
    GuiDesc("cloud", "gui_cloud", "mdi:weather-cloudy"),
    GuiDesc("sun_cloud_wait", "gui_sun_cloud_wait_time", "mdi:timer-sand"),
    GuiDesc("night", "gui_night", "mdi:weather-night"),
    GuiDesc("solar_position", "gui_solar_position", "mdi:sun-angle-outline"),
    GuiDesc("driving_limit", "gui_travel_limit", "mdi:arrow-collapse-vertical"),
    GuiDesc("night_cooling", "gui_night_cooling", "mdi:snowflake-thermometer"),
    GuiDesc("safety", "gui_safety_lock", "mdi:shield-lock-outline"),
    GuiDesc("sensor_error", "gui_sensor_error", "mdi:alert-circle-outline"),
    GuiDesc("clock_timer", "gui_timer", "mdi:timer-outline"),
    GuiDesc("outdoor_temp_block_hot", "gui_outdoor_temperature_lock_hot", "mdi:thermometer-high"),
    GuiDesc("outdoor_temp_block_cold", "gui_outdoor_temperature_lock_cold", "mdi:thermometer-low"),
    GuiDesc("indoor_temp_block_cold", "gui_indoor_temperature_lock_cold", "mdi:home-thermometer-outline"),
    GuiDesc("recirculation_heat_gain", "gui_recirculation_heat_gain", "mdi:autorenew"),
    GuiDesc("recirculation_condensation_reduction", "gui_recirculation_condensation_reduction", "mdi:autorenew"),
    GuiDesc("emergency_mode", "gui_emergency_mode", "mdi:alert-octagon-outline"),
    GuiDesc("actuator_lock_info", "gui_actuator_lock", "mdi:lock-outline"),
    GuiDesc("air_quality_block", "gui_air_quality_lock", "mdi:air-filter"),
    GuiDesc("hcl_start_stop", "gui_hcl_start_stop", "mdi:lightbulb-auto-outline"),
    GuiDesc("fancoil_auto", "gui_fancoil_auto", "mdi:fan-auto"),
    GuiDesc("reference_run", "gui_reference_run", "mdi:axis-arrow"),
)

GUI_DESC_BY_KEY = {desc.key: desc for desc in GUI_DESCS}


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
        # A field that is disabled at startup can later become visible, active,
        # or alarm without the integration being reloaded.
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
        self._attr_translation_key = desc.translation_key
        self._attr_device_class = desc.device_class
        self._attr_native_unit_of_measurement = desc.unit
        self._attr_state_class = desc.state_class

    @property
    def native_value(self):
        return self.coordinator.data["weather"].get(self.desc.key)


class WS1000BrightnessSensor(WS1000Entity, SensorEntity):
    _attr_translation_key = "brightness"
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
    _attr_translation_key = "wind_speed"
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
    _attr_translation_key = "position"
    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"position_{drive.object_id}")
        self.drive = drive

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def native_value(self):
        return self.coordinator.data["drives"][self.drive.object_id].get("position")


class WS1000DriveTiltSensor(WS1000Entity, SensorEntity):
    _attr_translation_key = "slat_position"
    _attr_native_unit_of_measurement = UnitOfRatio.PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"tilt_{drive.object_id}")
        self.drive = drive

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def native_value(self):
        return self.coordinator.data["drives"][self.drive.object_id].get("tilt")


class WS1000DriveGuiStatusSensor(WS1000Entity, SensorEntity):
    """Read-only four-state GUI_DF symbol/status for one WS1000 actuator."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = (
        GUI_STATE_DISABLED,
        GUI_STATE_VISIBLE,
        GUI_STATE_ACTIVE,
        GUI_STATE_ALARM,
    )
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
        self._attr_translation_key = desc.translation_key
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
        return GUI_STATE_BY_RAW.get(raw)

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
