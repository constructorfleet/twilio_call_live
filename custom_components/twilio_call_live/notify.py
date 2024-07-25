"""Support for twilio_call_live notify."""

import voluptuous as vol
from typing import Any, override
import logging

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from urllib import parse as parse_url

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.notify.legacy import BaseNotificationService
from homeassistant.components.notify import NotifyEntity
from homeassistant.components.twilio.const import DOMAIN as TWILIO_DOMAIN
from homeassistant.components.webhook import async_generate_url
from homeassistant.helpers import entity_platform, service
from homeassistant.helpers.selector import (
    BooleanSelector,
    BooleanSelectorConfig,
    DurationSelector,
    DurationSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import _TypedDictT

from .twilio_call import TwilioCall

from .const import (
    ATTR_HANGUP_AFTER,
    ATTR_PROCESS_LIVE,
    CONF_FROM_NUMBER,
    CONF_PHRASE_EVENTS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Initiate Twilio Live Call"
SERVICE_INITIATE_CALL = "initiate_call"


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> "TwilioCallLiveNotificationService":
    """Legacy setup."""
    return hass.data[DOMAIN]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Get teh twilio_call_live notification service."""
    client: Client = hass.data[TWILIO_DOMAIN]
    service = TwilioCallLiveNotificationService(
        hass,
        client,
        entry,
    )
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN] = service
    async_add_entities([service])
    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_INITIATE_CALL,
        {
            vol.Required("to_number"): TextSelector(
                TextSelectorConfig(
                    multiline=False, type=TextSelectorType.TEL, autocomplete="tel"
                )
            ),
            vol.Required("message"): TextSelector(
                TextSelectorConfig(
                    multiline=False, type=TextSelectorType.URL, autocomplete="url"
                )
            ),
            vol.Optional("process_live", default=True): BooleanSelector(
                BooleanSelectorConfig()
            ),
            vol.Optional("hangup_after"): DurationSelector(
                DurationSelectorConfig(enable_day=False, allow_negative=False)
            ),
        },
        "send_message",
    )


class TwilioCallLiveNotificationService(NotifyEntity, BaseNotificationService):
    """Notification service for twilio live call."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Client,
        config: ConfigEntry,
    ) -> None:
        """Initialize notify service."""
        self._attr_name = DEFAULT_NAME
        self._hass = hass
        self._client = client
        self._calls: dict[str, TwilioCall] = {}
        self._config = config

    def call_complete(self, call: TwilioCall) -> None:
        """Call complete callback."""
        if call.call_instance is None or call.call_instance.sid is None:
            return
        self._calls.pop(call.call_instance.sid, None)

    @override
    async def async_will_remove_from_hass(self) -> None:
        for call in self._calls.values():
            await call.hangup()
        return await super().async_will_remove_from_hass()

    async def async_send_message(
        self,
        message: str,
        data: dict[str, Any] | None = None,
        targets: list[str] | str | None = None,
        **kwargs: Any,
    ) -> None:
        from_number = self._config.options.get(CONF_FROM_NUMBER)
        if not from_number:
            _LOGGER.warn("Twilio must be configured with a `from` number")
            return
        configs = self.hass.config_entries.async_entries(TWILIO_DOMAIN)
        if not configs:
            webhook_id = None
        else:
            webhook_id = configs[0].data.get(CONF_WEBHOOK_ID, None)

        webhook_url: str | None = None
        if webhook_id is not None:
            webhook_url = async_generate_url(
                self.hass, webhook_id=webhook_id, allow_external=True
            )
        targets = targets or kwargs.get("to_number", None)
        if not targets:
            _LOGGER.info("At least 1 target is required")
            return

        if message.startswith(("http://", "https://")):
            twimlet_url = message
        else:
            twimlet_url = "http://twimlets.com/message?Message="
            twimlet_url += parse_url.quote(message, safe="")

        process_live = (
            data or {ATTR_PROCESS_LIVE: kwargs.get(ATTR_PROCESS_LIVE, None)}
        ).get(ATTR_PROCESS_LIVE, True)
        hangup_after = (
            data or {ATTR_HANGUP_AFTER: kwargs.get(ATTR_HANGUP_AFTER, None)}
        ).get(ATTR_HANGUP_AFTER, None)
        for target in targets if isinstance(targets, list) else [targets]:
            try:
                call = call = TwilioCall(
                    self.hass,
                    self.call_complete,
                    self._config.options.get(CONF_PHRASE_EVENTS, []),
                    self._client,
                    process_live=process_live,
                    hangup_after=hangup_after,
                )

                sid = await call.initiate_call(
                    from_number=from_number,
                    to_number=target,
                    url=twimlet_url,
                    webhook_url=webhook_url,
                )

                if sid is None:
                    continue

                self._calls[sid] = call

            except TwilioRestException as exc:
                _LOGGER.error(exc)
