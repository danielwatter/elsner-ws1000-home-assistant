from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_HOST, DOMAIN


def cleanup_obsolete_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove obsolete entity-registry entries from earlier schemas."""
    registry = er.async_get(hass)
    obsolete_unique_ids = {
        f"{entry.entry_id}_binary_rain_alarm",
        f"{entry.entry_id}_binary_wind_alarm",
        f"{entry.entry_id}_binary_frost_alarm",
        f"{entry.entry_id}_sensor_wind_speed",
        f"{entry.entry_id}_sensor_wind_speed_ms",
        f"{entry.entry_id}_sensor_wind_speed_kmh",
        f"{entry.entry_id}_sensor_illuminance",
    }

    for entity in list(registry.entities.values()):
        if (
            entity.config_entry_id == entry.entry_id
            and entity.unique_id in obsolete_unique_ids
        ):
            registry.async_remove(entity.entity_id)

    for entity in list(registry.entities.values()):
        if (
            entity.config_entry_id == entry.entry_id
            and (
                entity.unique_id.endswith("_short_up")
                or entity.unique_id.endswith("_short_down")
            )
        ):
            registry.async_remove(entity.entity_id)


def ensure_parent_device(hass: HomeAssistant, entry: ConfigEntry):
    """Ensure the WS1000 actuator parent device exists."""
    registry = dr.async_get(hass)
    return registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Elsner WS1000",
        manufacturer="Elsner Elektronik",
        model="WS1000",
        configuration_url=f"http://{entry.data[CONF_HOST]}",
    )


def ensure_groups_parent_device(hass: HomeAssistant, entry: ConfigEntry):
    """Ensure the independent WS1000 groups parent device exists."""
    registry = dr.async_get(hass)
    return registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, f"{entry.entry_id}:groups")},
        translation_key="groups_controller",
        manufacturer="Elsner Elektronik",
        model="WS1000 Groups",
        configuration_url=f"http://{entry.data[CONF_HOST]}",
    )


def migrate_child_device_identifiers(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Normalize legacy actuator/group device identifiers."""
    registry = dr.async_get(hass)

    for device in list(registry.devices):
        if device.config_entry_id != entry.entry_id:
            continue

        if (DOMAIN, entry.entry_id) in device.identifiers:
            continue

        for identifier in list(device.identifiers):
            if not identifier or identifier[0] != DOMAIN:
                continue

            # Legacy physical actuator identifier:
            #   (DOMAIN, entry_id, object_id)
            if len(identifier) == 3 and identifier[1] == entry.entry_id:
                try:
                    oid = int(identifier[2])
                except (TypeError, ValueError):
                    continue

                if 100 <= oid <= 107:
                    registry.async_update_device(
                        device.id,
                        new_identifiers={
                            (DOMAIN, f"{entry.entry_id}:drive:{oid}")
                        },
                    )
                    break

            # Legacy group identifier:
            #   (DOMAIN, entry_id, "group", object_id)
            if (
                len(identifier) == 4
                and identifier[1] == entry.entry_id
                and identifier[2] == "group"
            ):
                try:
                    gid = int(identifier[3])
                except (TypeError, ValueError):
                    continue

                if 0 <= gid < 20:
                    registry.async_update_device(
                        device.id,
                        new_identifiers={
                            (DOMAIN, f"{entry.entry_id}:group:{gid}")
                        },
                    )
                else:
                    registry.async_remove_device(device.id)
                break


def cleanup_obsolete_group_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove obsolete entity-registry entries for non-user group objects."""
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_group_cover_"

    for entity in list(registry.entities.values()):
        if entity.config_entry_id != entry.entry_id:
            continue
        if not entity.unique_id.startswith(prefix):
            continue

        try:
            gid = int(entity.unique_id[len(prefix):])
        except ValueError:
            continue

        if gid >= 20:
            registry.async_remove(entity.entity_id)


def reparent_existing_group_children(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Recreate user-group child devices below the dedicated groups parent.

    Home Assistant does not support changing a Child Device parent in place.
    Existing group child devices below the actuator parent are therefore
    removed once; normal entity registration recreates them below the groups
    parent with unchanged entity unique IDs.
    """
    registry = dr.async_get(hass)

    main_parent_id = dr.async_get_device_id_by_identifier(
        hass,
        (DOMAIN, entry.entry_id),
        config_entry_id=entry.entry_id,
    )
    groups_parent_id = dr.async_get_device_id_by_identifier(
        hass,
        (DOMAIN, f"{entry.entry_id}:groups"),
        config_entry_id=entry.entry_id,
    )

    if main_parent_id is None or groups_parent_id is None:
        return

    for child in list(
        dr.async_entries_for_parent_device(registry, main_parent_id)
    ):
        group_id = None

        for identifier in child.identifiers:
            if len(identifier) != 2 or identifier[0] != DOMAIN:
                continue

            value = identifier[1]
            prefix = f"{entry.entry_id}:group:"
            if not value.startswith(prefix):
                continue

            try:
                group_id = int(value[len(prefix):])
            except ValueError:
                group_id = None
            break

        if group_id is None or not 0 <= group_id < 20:
            continue

        registry.async_remove_device(child.id)


def prepare_device_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> tuple[str, str]:
    """Run registry cleanup/migration and return both parent device IDs."""
    cleanup_obsolete_entities(hass, entry)
    cleanup_obsolete_group_entities(hass, entry)

    main_parent = ensure_parent_device(hass, entry)
    groups_parent = ensure_groups_parent_device(hass, entry)

    migrate_child_device_identifiers(hass, entry)
    reparent_existing_group_children(hass, entry)

    return main_parent.id, groups_parent.id
