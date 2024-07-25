"""The twilio_call_live component."""

from typing import Any, override
import asyncio
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.components.twilio.const import DOMAIN as TWILIO_DOMAIN
from homeassistant.components.webhook import async_generate_url
from homeassistant.helpers import discovery
from homeassistant.helpers.event import _TypedDictT

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.NOTIFY]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize the twilio_call_live configuration entry."""
    _LOGGER.info("async_setup_entry")
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if hass.is_running:
        """Initialize immediately"""
        await async_init(hass, entry, None)
    else:
        """Schedule initialization when HA is started and initialized"""

        # https://developers.home-assistant.io/docs/asyncio_working_with_async/#calling-async-functions-from-threads

        @callback
        def init(hass: HomeAssistant, entry: ConfigEntry, twilio_live_call: None):
            asyncio.run_coroutine_threadsafe(
                async_init(hass, entry, twilio_live_call), hass.loop
            ).result()

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, lambda params: init(hass, entry, None)
        )
    return True


async def async_init(hass: HomeAssistant, entry: ConfigEntry, twilio_live_call: None):
    """Initialize component."""
    _LOGGER.info("async_init")
    await asyncio.sleep(5)  # wait for all area devices to be initialized
    # await auto_area.async_initialize()
    # await hass.config_entries.async_forward_entry_setup() .async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("🔄 Reloading entry %s", entry)

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.info("async_unload_entry")
    twilio_config = hass.data[DOMAIN].get(entry.entry_id, None)
    if twilio_config is not None and hasattr(twilio_config, "cleanup"):
        twilio_config.cleanup()

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.warning("Unloaded successfully %s", entry.entry_id)
    else:
        _LOGGER.error("Couldn't unload config entry %s", entry.entry_id)

    return unloaded
