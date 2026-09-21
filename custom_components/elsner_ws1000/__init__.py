from __future__ import annotations

import asyncio
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, DEFAULT_SCAN_INTERVAL, PLATFORMS
from .coordinator import WS1000Coordinator
from .migration import prepare_device_registry
from .protocol import WS1000Client, WS1000Drive, WS1000Group


@dataclass
class WS1000RuntimeData:
    client: WS1000Client
    coordinator: WS1000Coordinator
    drives: list[WS1000Drive]
    groups: list[WS1000Group]
    actuator_parent_device_id: str
    groups_parent_device_id: str


type WS1000ConfigEntry = ConfigEntry[WS1000RuntimeData]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WS1000ConfigEntry,
) -> bool:
    actuator_parent_device_id, groups_parent_device_id = prepare_device_registry(
        hass,
        entry,
    )

    client = WS1000Client(entry.data[CONF_HOST])
    drives, groups = await asyncio.to_thread(client.discover_topology)

    coordinator = WS1000Coordinator(
        hass,
        client,
        drives,
        DEFAULT_SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = WS1000RuntimeData(
        client=client,
        coordinator=coordinator,
        drives=drives,
        groups=groups,
        actuator_parent_device_id=actuator_parent_device_id,
        groups_parent_device_id=groups_parent_device_id,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: WS1000ConfigEntry,
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
