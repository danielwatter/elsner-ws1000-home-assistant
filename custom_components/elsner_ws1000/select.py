import asyncio

from homeassistant.components.select import SelectEntity

from .entity import WS1000Entity, drive_device_info
from .labels import MODE_AUTO, MODE_MANUAL


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    async_add_entities(
        WS1000Mode(data.coordinator, entry, drive)
        for drive in data.drives
    )


class WS1000Mode(WS1000Entity, SelectEntity):
    _attr_translation_key = "operating_mode"
    _attr_options = [MODE_AUTO, MODE_MANUAL]

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"mode_{drive.object_id}")
        self.drive = drive

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def current_option(self):
        mode = self.coordinator.data["drives"][self.drive.object_id].get("mode")
        return mode if mode in (MODE_AUTO, MODE_MANUAL) else None

    async def async_select_option(self, option: str):
        if option == MODE_AUTO:
            await asyncio.to_thread(self.coordinator.client.set_auto, self.drive.object_id)
        elif option == MODE_MANUAL:
            await asyncio.to_thread(self.coordinator.client.set_manual, self.drive.object_id)
        else:
            raise ValueError(f"Unsupported operating mode: {option}")
        await self.coordinator.async_request_refresh()
