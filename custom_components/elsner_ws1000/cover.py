from __future__ import annotations
import asyncio

from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass

from .entity import WS1000Entity, drive_device_info, group_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    data = entry.runtime_data

    entities = [
        WS1000Cover(data.coordinator, entry, drive)
        for drive in data.drives
    ]
    entities.extend(
        WS1000GroupCover(data.coordinator, entry, group)
        for group in data.groups
    )

    async_add_entities(entities)


class WS1000Cover(WS1000Entity, CoverEntity):
    """WS1000 actuator control.

    Deliberately stateless for command availability:
    Home Assistant must not disable OPEN/CLOSE based on the reported
    WS1000 position. The controller itself decides whether a command
    has an effect at the current position.

    Position and tilt remain available as separate read-only sensors.
    """

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.STOP
        | CoverEntityFeature.CLOSE
    )

    def __init__(self, coordinator, entry, drive):
        super().__init__(coordinator, entry, f"cover_{drive.object_id}")
        self.drive = drive
        self._attr_name = None
        self._attr_device_class = (
            CoverDeviceClass.AWNING if drive.kind == "awning"
            else CoverDeviceClass.BLIND if drive.kind == "blind"
            else CoverDeviceClass.WINDOW
        )

    @property
    def device_info(self):
        return drive_device_info(self.coordinator.hass, self._entry, self.drive)

    @property
    def current_cover_position(self):
        """Expose the current WS1000 position using Home Assistant semantics.

        WS1000:
          0   = fully up / retracted
          100 = fully down / extended

        Home Assistant cover position:
          100 = open / up
          0   = closed / down

        Therefore the percentage is inverted for the cover entity only.
        The dedicated WS1000 sensors/sliders keep their native Elsner values.
        """
        status = (
            self.coordinator.data["drives"]
            .get(self.drive.object_id, {})
        )
        position = status.get("position")
        if position is None:
            return None
        return 100 - int(position)

    @property
    def is_closed(self):
        position = self.current_cover_position
        if position is None:
            return None
        return position == 0

    @property
    def assumed_state(self):
        # Keep both direction buttons available even when HA knows the
        # current position. The WS1000 remains authoritative for commands.
        return True

    async def async_open_cover(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.full_up,
            self.drive.object_id,
        )
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.stop,
            self.drive.object_id,
        )
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs):
        await asyncio.to_thread(
            self.coordinator.client.full_down,
            self.drive.object_id,
        )
        await self.coordinator.async_request_refresh()


class WS1000GroupCover(WS1000Entity, CoverEntity):
    """Reduced WS1000 group control.

    Groups support full up, full down and stop via a short command in the
    opposite direction. Direct percentage positioning is intentionally not
    exposed because the WS1000 group command does not provide usable
    percentage positioning.
    """

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.STOP
        | CoverEntityFeature.CLOSE
    )
    _attr_device_class = CoverDeviceClass.SHUTTER

    def __init__(self, coordinator, entry, group):
        super().__init__(
            coordinator,
            entry,
            f"group_cover_{group.object_id}",
        )
        # "group" is reserved by Home Assistant Entity for native Group
        # metadata. Keep the WS1000 protocol object under a domain-specific
        # attribute instead.
        self.ws1000_group = group
        self._attr_has_entity_name = False
        self._attr_name = group.name
        self._last_direction: str | None = None

    @property
    def device_info(self):
        return group_device_info(
            self.coordinator.hass,
            self._entry,
            self.ws1000_group,
        )

    @property
    def is_closed(self):
        # No meaningful aggregate group position is available.
        return None

    @property
    def assumed_state(self):
        return True

    async def async_open_cover(self, **kwargs):
        self._last_direction = "up"
        await asyncio.to_thread(
            self.coordinator.client.group_full_up,
            self.ws1000_group.object_id,
        )

    async def async_close_cover(self, **kwargs):
        self._last_direction = "down"
        await asyncio.to_thread(
            self.coordinator.client.group_full_down,
            self.ws1000_group.object_id,
        )

    async def async_stop_cover(self, **kwargs):
        if self._last_direction == "down":
            await asyncio.to_thread(
                self.coordinator.client.group_short_up,
                self.ws1000_group.object_id,
            )
        elif self._last_direction == "up":
            await asyncio.to_thread(
                self.coordinator.client.group_short_down,
                self.ws1000_group.object_id,
            )
        else:
            # If the drive was started outside HA, the direction is unknown.
            # Keep the proven pragmatic fallback rather than exposing an
            # unavailable STOP control.
            await asyncio.to_thread(
                self.coordinator.client.group_stop_unknown_direction,
                self.ws1000_group.object_id,
            )

        self._last_direction = None
