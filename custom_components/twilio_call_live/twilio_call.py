from .config import EventPhrasesList
from .const import DOMAIN
from .transcription_utils import (
    PhraseMatcher,
    TranscriptionMerger,
)

from homeassistant.components.twilio import RECEIVED_DATA
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time, _TypedDictT
from pytz import UTC
from twilio.rest import Client
from twilio.rest.api.v2010.account.call import CallInstance

import logging
import json
from datetime import UTC, datetime, timedelta
from inspect import isfunction
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)


class TwilioCall:
    """Class for interacting with a Twilio call resource."""

    def __init__(
        self,
        hass: HomeAssistant,
        complete_callback: Callable[["TwilioCall"], None],
        event_phrases: list[dict[str, Any]],
        client: Client,
        process_live: bool = False,
        hangup_after: timedelta | None = None,
    ) -> None:
        self.hass = hass
        self.client = client
        self.complete_callback = complete_callback
        self.call_instance: CallInstance
        self.process_live = process_live
        self.hangup_after = hangup_after
        self.transcription_resource = None
        self.transcription = None
        self.merger = TranscriptionMerger(self._process_transcript)
        self.matcher = PhraseMatcher(EventPhrasesList(event_phrases))
        self.unsubscribe: dict[str, Any] = {}

    async def initiate_call(
        self, from_number: str, to_number: str, url: str, webhook_url: str | None = None
    ) -> str | None:
        """Initiate the call with Twilio."""
        self.call_instance = await self.client.calls.create_async(
            from_=from_number, to=to_number, url=url, status_callback=webhook_url
        )
        _LOGGER.info("Intiated call %s", self.call_instance.sid)
        if self.process_live:
            self.transcription = ""
            self.unsubscribe["data"] = self.hass.bus.listen(
                RECEIVED_DATA, self.on_twilio_data_received
            )

            await self.call_instance.transcriptions.create_async(
                # name=
                track="inbound",
                status_callback_url="",
                status_callback_method="",
                partial_results=True,
                language_code="en-US",
                speech_model="telephony",
                transcription_engine="google",
                enable_automatic_punctuation=False,
            )
        if self.hangup_after is not None:
            self.unsubscribe["hangup"] = async_track_point_in_utc_time(
                self.hass, self.hangup, datetime.now(UTC) + self.hangup_after
            )
        return self.call_instance.sid

    async def on_twilio_data_received(self, event: Event[_TypedDictT]) -> None:
        """Handle twilio data received event."""
        if not self.process_live:
            return
        if event.data.get("CallSid", None) != self.call_instance:
            return
        if event.data.get("CallStatus", None) == "completed":
            self._on_call_complete()
        transcription_data = event.data.get("TranscriptionData", None)
        transcription_text = event.data.get("TranscriptionText", None)
        if transcription_data is not None:
            transcription = json.loads(transcription_data)
            self._on_transcription_data(
                transcription.get("transcript", None),
                transcription.get("confidence", None),
            )
        if transcription_text is not None:
            self._on_transcription_text(transcription_text)

    async def _on_call_complete(self) -> None:
        """Handle when the call is completed."""
        await self.hangup()
        self.complete_callback(self)

    def _on_transcription_data(
        self, transcript: str | None, confidence: float | None
    ) -> None:
        """Handle transcription data received."""
        if transcript is None:
            return
        _LOGGER.info("_on_transcription_data: %s", transcript)
        self.merger.add_segment(transcript)

    def _on_transcription_text(self, transcript: str) -> None:
        """Handle transcription text received."""
        pass

    def _process_transcript(self, transcript: str) -> None:
        """Process transcript."""
        event = self.matcher.phrase_match_event(transcript)
        if event is None:
            return
        _LOGGER.info(
            "._process_transcript: Found event %s, phrases: %s, transcript: %s",
            event.event,
            event.phrases_string,
            transcript,
        )
        self.matcher.event_phrases.remove(event)
        self.hass.bus.fire(event.event, {"transcript": transcript})
        self.hass.bus.fire(DOMAIN, {"transcript": transcript})

    async def hangup(self, time_date: datetime | None = None) -> None:
        """Hangup the call."""
        try:
            _LOGGER.info("Hanging up call.")
            unsub = self.unsubscribe.pop("hangup", None)
            if unsub is not None and isfunction(unsub):
                unsub()

            await self.call_instance.update_async(method="POST", status="completed")
        except Exception as exc:
            _LOGGER.error("Error hanging up call %s", exc, exc_info=exc)

    async def cancel_subscriptions(self) -> None:
        """Unsubscribe from listeners."""
        await self.hangup()
        for key in ["data", "hangup", "transcript"]:
            unsub = self.unsubscribe.get(key, None)
            if not isfunction(unsub):
                continue
            unsub()
