import asyncio

from homeassistant.components.select import SelectEntity

from .entity import WS1000Entity, drive_device_info
from .labels import NAME_MODE


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    async_add_entities(
        WS1000Mode(data.coordinator, entry, drive)
        for drive in data.drives
    )


class WS1000Mode(WS1000Entity, SelectEntity):
    _attr_options = ["Auto", "Manuell"]

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"mode_{drive.object_id}")
        self.drive = drive
        self._attr_name = NAME_MODE


    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def current_option(self):
        mode = self.coordinator.data["drives"][self.drive.object_id].get("mode")
        return "Auto" if mode == "auto" else "Manuell" if mode == "manual" else None

    async def async_select_option(self, option: str):
        if option == "Auto":
            await asyncio.to_thread(self.coordinator.client.set_auto, self.drive.object_id)
        else:
            await asyncio.to_thread(self.coordinator.client.set_manual, self.drive.object_id)
        await self.coordinator.async_request_refresh()
