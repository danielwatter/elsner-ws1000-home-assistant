from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import ChildDeviceInfo

from .const import DOMAIN


def controller_device_info(entry):
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": "Elsner WS1000",
        "manufacturer": "Elsner Elektronik",
        "model": "WS1000",
        "configuration_url": f"http://{entry.data['host']}",
    }


def groups_controller_device_info(entry):
    """Return the independent parent device for WS1000 user groups."""
    return {
        "identifiers": {(DOMAIN, f"{entry.entry_id}:groups")},
        "name": "Elsner WS1000 - Gruppen",
        "manufacturer": "Elsner Elektronik",
        "model": "WS1000 Gruppen",
        "configuration_url": f"http://{entry.data['host']}",
    }


def _parent_device_id(hass, entry) -> str:
    """Return cached main parent ID; fall back only during migration/setup."""
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is not None:
        device_id = getattr(runtime_data, "actuator_parent_device_id", None)
        if device_id is not None:
            return device_id

    return dr.async_get_device_id_by_identifier(
        hass,
        (DOMAIN, entry.entry_id),
        config_entry_id=entry.entry_id,
    )


def drive_device_info(hass, entry, drive) -> ChildDeviceInfo:
    """Represent a physical actuator as a native HA child device."""
    return ChildDeviceInfo(
        identifiers={
            (DOMAIN, f"{entry.entry_id}:drive:{drive.object_id}")
        },
        name=drive.name,
        parent_device_id=_parent_device_id(hass, entry),
    )


def _groups_parent_device_id(hass, entry) -> str:
    """Return cached groups parent ID; fall back only during migration/setup."""
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is not None:
        device_id = getattr(runtime_data, "groups_parent_device_id", None)
        if device_id is not None:
            return device_id

    return dr.async_get_device_id_by_identifier(
        hass,
        (DOMAIN, f"{entry.entry_id}:groups"),
        config_entry_id=entry.entry_id,
    )


def group_device_info(hass, entry, group) -> ChildDeviceInfo:
    """Represent a WS1000 user group below the independent groups parent."""
    return ChildDeviceInfo(
        identifiers={
            (DOMAIN, f"{entry.entry_id}:group:{group.object_id}")
        },
        name=group.name,
        parent_device_id=_groups_parent_device_id(hass, entry),
    )


class WS1000Entity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, unique_suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"

    @property
    def device_info(self):
        return controller_device_info(self._entry)
