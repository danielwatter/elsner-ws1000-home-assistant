import asyncio

from homeassistant.components.switch import SwitchEntity

from .entity import WS1000Entity, drive_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    entities = []

    for drive in data.drives:
        entities.append(WS1000AutoLock(data.coordinator, entry, drive))
        entities.append(WS1000ActuatorLock(data.coordinator, entry, drive))

    async_add_entities(entities)


class WS1000AutoLock(WS1000Entity, SwitchEntity):
    _attr_translation_key = "automatic_lock"

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"autolock_{drive.object_id}")
        self.drive = drive

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def is_on(self):
        return bool(
            self.coordinator.data["drives"][self.drive.object_id].get("autolock")
        )

    async def async_turn_on(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.set_autolock, self.drive.object_id, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.set_autolock, self.drive.object_id, False
        )
        await self.coordinator.async_request_refresh()


class WS1000ActuatorLock(WS1000Entity, SwitchEntity):
    """Per-actuator lock confirmed by Elsner."""

    _attr_translation_key = "actuator_lock"
    _attr_icon = "mdi:lock"

    def __init__(self, coordinator, entry, drive):
        super().__init__(
            coordinator,
            entry,
            f"actuator_lock_{drive.object_id}",
        )
        self.drive = drive

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def is_on(self):
        raw = (
            self.coordinator.data["drives"]
            .get(self.drive.object_id, {})
            .get("gui_df", {})
            .get("actuator_lock_info")
        )
        # GUI_DF values: 0 disabled, 1 visible, 2 highlighted/active, 3 alarm.
        # Treat highlighted/active or alarm as locked.
        if raw is None:
            return None
        return raw in (2, 3)

    async def async_turn_on(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.set_actuator_lock,
            self.drive.object_id,
            True,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.set_actuator_lock,
            self.drive.object_id,
            False,
        )
        await self.coordinator.async_request_refresh()
