from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity

from .entity import WS1000Entity


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data
    async_add_entities([
        WS1000BuildingAutoButton(data.coordinator, entry),
    ])


class WS1000BuildingAutoButton(WS1000Entity, ButtonEntity):
    """Set all currently manual WS1000 drives back to automatic mode."""

    _attr_translation_key = "building_automatic_mode"
    _attr_icon = "mdi:home-automation"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "building_auto")

    async def async_press(self) -> None:
        """Return all currently manual drives to automatic mode."""
        drives = self.coordinator.data.get("drives", {})
        manual_object_ids = [
            object_id
            for object_id, status in drives.items()
            if status.get("mode") == "manual"
        ]

        for object_id in manual_object_ids:
            await asyncio.to_thread(self.coordinator.client.set_auto, object_id)

        if manual_object_ids:
            await self.coordinator.async_request_refresh()
