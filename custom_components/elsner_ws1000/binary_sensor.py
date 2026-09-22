from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import WS1000Entity, drive_device_info


@dataclass(frozen=True)
class Desc:
    key: str
    translation_key: str
    device_class: BinarySensorDeviceClass | None = None
    icon: str | None = None


# Controller/weather-level binary sensors.
WEATHER_DESCS = (
    Desc("rain", "rain", BinarySensorDeviceClass.MOISTURE),
)

# Per-actuator alarm/protection states.
DRIVE_ALARM_DESCS = (
    Desc("rain_alarm", "rain_alarm", None, "mdi:weather-rainy"),
    Desc("wind_alarm", "wind_alarm", None, "mdi:weather-windy"),
    Desc("frost_alarm", "frost_alarm", None, "mdi:snowflake"),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data.coordinator
    entities = [
        WS1000WeatherBinarySensor(coordinator, entry, desc)
        for desc in WEATHER_DESCS
    ]

    for drive in entry.runtime_data.drives:
        for desc in DRIVE_ALARM_DESCS:
            entities.append(
                WS1000DriveAlarmBinarySensor(
                    coordinator,
                    entry,
                    drive,
                    desc,
                )
            )

    async_add_entities(entities)


class WS1000WeatherBinarySensor(WS1000Entity, BinarySensorEntity):
    def __init__(self, coordinator, entry, desc):
        super().__init__(coordinator, entry, f"binary_{desc.key}")
        self.desc = desc
        self._attr_translation_key = desc.translation_key
        self._attr_device_class = desc.device_class
        self._attr_icon = desc.icon

    @property
    def is_on(self):
        return bool(self.coordinator.data["weather"].get(self.desc.key))


class WS1000DriveAlarmBinarySensor(WS1000Entity, BinarySensorEntity):
    """Alarm/protection state belonging to one physical WS1000 actuator."""

    def __init__(self, coordinator, entry, drive, desc):
        super().__init__(
            coordinator,
            entry,
            f"binary_{drive.object_id}_{desc.key}",
        )
        self.drive = drive
        self.desc = desc
        self._attr_translation_key = desc.translation_key
        self._attr_device_class = desc.device_class
        self._attr_icon = desc.icon

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def is_on(self):
        status = self.coordinator.data["drives"].get(self.drive.object_id, {})
        return bool(status.get(self.desc.key))
