"""Support for VeSync button."""

import logging

import voluptuous as vol

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import VeSyncBaseEntity
from .const import DOMAIN, VS_BUTTON, VS_DISCOVERY

_LOGGER = logging.getLogger(__name__)


SENSOR_TYPES_CS158 = {
    # unique_id,name # icon,
    "end": [
        "end",
        "End cooking or preheating ",
        "mdi:stop",
    ],
}

SERVICE_COOK = "cook"
SERVICE_STOP = "stop"
ATTR_TEMPERATURE = "temperature"
ATTR_TIME = "time"

COOK_SCHEMA = {
    vol.Required(ATTR_TEMPERATURE): vol.All(vol.Coerce(int), vol.Range(min=40, max=400)),
    vol.Required(ATTR_TIME): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
}
STOP_SCHEMA = {}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    @callback
    def discover(devices):
        """Add new devices to platform."""
        _setup_entities(devices, async_add_entities, coordinator)

    config_entry.async_on_unload(
        async_dispatcher_connect(hass, VS_DISCOVERY.format(VS_BUTTON), discover)
    )

    _setup_entities(
        hass.data[DOMAIN][config_entry.entry_id][VS_BUTTON],
        async_add_entities,
        coordinator,
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_COOK,
        COOK_SCHEMA,
        "async_cook",
    )
    platform.async_register_entity_service(
        SERVICE_STOP,
        STOP_SCHEMA,
        "async_stop",
    )


@callback
def _setup_entities(devices, async_add_entities, coordinator):
    """Check if device is online and add entity."""
    entities = []
    for dev in devices:
        if hasattr(dev, "cook_set_temp"):
            for stype in SENSOR_TYPES_CS158.values():
                entities.append(  # noqa: PERF401
                    VeSyncairfryerButton(
                        dev,
                        coordinator,
                        stype,
                    )
                )

    async_add_entities(entities, update_before_add=True)


class VeSyncairfryerButton(VeSyncBaseEntity, ButtonEntity):
    """Base class for VeSync switch Device Representations."""

    def __init__(self, airfryer, coordinator, stype) -> None:
        """Initialize the VeSync humidifier device."""
        super().__init__(airfryer, coordinator)
        self.airfryer = airfryer
        self.stype = stype

    @property
    def unique_id(self):
        """Return unique ID for water tank lifted sensor on device."""
        return f"{super().unique_id}-" + self.stype[0]

    @property
    def name(self):
        """Return sensor name."""
        return self.stype[1]

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self.stype[2]

    def press(self) -> None:
        """Return True if device is on."""
        self.airfryer.end()

    async def async_cook(self, temperature: int, time: int) -> None:
        """Start cooking at the given temperature (°C) for the given time (minutes)."""
        await self.hass.async_add_executor_job(self.airfryer.cook, temperature, time)
        await self.coordinator.async_request_refresh()

    async def async_stop(self) -> None:
        """End the current cooking or preheating cycle."""
        await self.hass.async_add_executor_job(self.airfryer.end)
        await self.coordinator.async_request_refresh()
