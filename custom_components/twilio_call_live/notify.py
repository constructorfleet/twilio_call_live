"""Support for twilio_call_live notify."""

from homeassistant.core import HomeAssistant
from homeassistant.components import notify
from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

DEFAULT_NAME = "Initiate Twilio Live Call"

PLATFORM_SCHEMA_MODERN = 


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up twilio_call_live notify thrown YAML."""


class TwilioCallLiveNotify(NotifyEntity):
    """Representation of a notification entity service that can initiate calls with Twilio."""
