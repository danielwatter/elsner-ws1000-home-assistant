from __future__ import annotations

import asyncio

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE

from .entity import WS1000Entity, drive_device_info
from .labels import NAME_DRIVE_POSITION, NAME_TILT_POSITION


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data.coordinator
    entities = []

    for drive in entry.runtime_data.drives:
        entities.append(
            WS1000DrivePositionNumber(coordinator, entry, drive)
        )

        if drive.kind == "blind":
            entities.append(
                WS1000DriveTiltNumber(coordinator, entry, drive)
            )

    async_add_entities(entities)


class WS1000BaseNumber(WS1000Entity, NumberEntity):
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, entry, drive, unique_suffix):
        super().__init__(coordinator, entry, unique_suffix)
        self.drive = drive

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    def _status(self):
        return (
            self.coordinator.data["drives"]
            .get(self.drive.object_id, {})
        )


class WS1000DrivePositionNumber(WS1000BaseNumber):
    _attr_name = NAME_DRIVE_POSITION
    _attr_icon = "mdi:arrow-expand-vertical"

    def __init__(self, coordinator, entry, drive):
        super().__init__(
            coordinator,
            entry,
            drive,
            f"number_position_{drive.object_id}",
        )

    @property
    def native_value(self):
        # Prefer the WS1000 target value (Sollposition). When the controller
        # has no active/valid target (e.g. after the drive has stopped), fall
        # back to the actual position. This mirrors the Elsner app display.
        status = self._status()
        value = status.get("target_position")
        if value is None:
            value = status.get("position")
        return value

    async def async_set_native_value(self, value):
        status = self._status()
        position = int(round(value))

        # The WS1000 B command always sends travel position and lamella
        # position together. For blinds, the two travel end positions also
        # have defined lamella end positions in the native Elsner UI:
        #   0 % travel   -> 0 % lamella
        #   100 % travel -> 100 % lamella
        # Preserve the currently known lamella target only for intermediate
        # travel positions.
        if self.drive.kind == "blind" and position in (0, 100):
            tilt = position
        else:
            tilt = status.get("target_tilt")
            if tilt is None:
                tilt = status.get("tilt")
            if tilt is None:
                tilt = 0

        await asyncio.to_thread(
            self.coordinator.client.set_position,
            self.drive.object_id,
            position,
            int(tilt),
        )
        await self.coordinator.async_request_refresh()


class WS1000DriveTiltNumber(WS1000BaseNumber):
    _attr_name = NAME_TILT_POSITION
    _attr_icon = "mdi:blinds-horizontal"

    def __init__(self, coordinator, entry, drive):
        super().__init__(
            coordinator,
            entry,
            drive,
            f"number_tilt_{drive.object_id}",
        )

    @property
    def native_value(self):
        # Prefer the target lamella value. If no valid target is reported,
        # use the actual lamella position, like the Elsner app.
        status = self._status()
        value = status.get("target_tilt")
        if value is None:
            value = status.get("tilt")
        return value

    async def async_set_native_value(self, value):
        status = self._status()

        # Preserve the currently known travel position when only the
        # lamella slider is changed.
        position = status.get("target_position")
        if position is None:
            position = status.get("position")

        if position is None:
            return

        await asyncio.to_thread(
            self.coordinator.client.set_position,
            self.drive.object_id,
            int(position),
            int(round(value)),
        )
        await self.coordinator.async_request_refresh()
