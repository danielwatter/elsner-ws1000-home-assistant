from __future__ import annotations
from datetime import timedelta
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .protocol import WS1000Client, WS1000Drive


class WS1000Coordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, client: WS1000Client, drives: list[WS1000Drive], scan_interval: int) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.drives = drives

    async def _async_update_data(self) -> dict:
        try:
            weather = await asyncio.to_thread(self.client.read_weather)
            statuses = {}
            for drive in self.drives:
                statuses[drive.object_id] = await asyncio.to_thread(
                    self.client.read_status, drive.object_id
                )
            return {"weather": weather, "drives": statuses}
        except Exception as exc:
            raise UpdateFailed(str(exc)) from exc
