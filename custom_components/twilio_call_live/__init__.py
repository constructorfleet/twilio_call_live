"""The twilio_call_live component."""
import voluptuous as vol
import asyncio
import logging
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.twilio.const import DOMAIN as TWILIO_DOMAIN
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from .const import (
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Initialize the twilio_call_live configuration entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    twilio_domain = hass.data.get(TWILIO_DOMAIN)
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
            EVENT_HOMEASSISTANT_STARTED,
            lambda params: init(hass, entry, None)
        )
    return True

async def async_init(hass: HomeAssistant, entry: ConfigEntry, twilio_live_call: None):
    """Initialize component."""
    await asyncio.sleep(5)  # wait for all area devices to be initialized
    # await auto_area.async_initialize()
    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("🔄 Reloading entry %s", entry)

    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    # unsubscribe from changes:
    twilio_config = hass.data[DOMAIN].get(entry.entry_id, None)
    if twilio_config is not None:
        twilio_config.cleanup()

    # unload platforms:
    # unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if True:  # unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.warning("Unloaded successfully %s", entry.entry_id)
    else:
        _LOGGER.error("Couldn't unload config entry %s", entry.entry_id)

    return True  # unloaded


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Check for YAML-config."""

    if config.get("auto_areas") is not None:
        _LOGGER.warning(
            "Detected an existing YAML configuration. "
            + "This is not supported anymore, please remove it."
        )
        # issue_registry.async_create_issue(
        #     hass,
        #     DOMAIN,
        #     ISSUE_TYPE_YAML_DETECTED,
        #     is_fixable=False,
        #     is_persistent=False,
        #     severity=issue_registry.IssueSeverity.WARNING,
        #     translation_key=ISSUE_TYPE_YAML_DETECTED,
        # )

    return True