"""Constants for the twilio_call_live integration."""
import re

DOMAIN = "twilio_call_live"

CONF_FROM_NUMBER = "from_number"
CONF_PHRASE_EVENTS = "phrase_events"
CONF_PHRASE = "phrase"
CONF_PHRASES = "phrases"
CONF_ACTION = "action"

FROM_NUMBER_REPLACER = re.compile(r"[^0-9\+]")
FROM_NUMBER_PATTERN = re.compile(r"^\+?[1-9]\d{1,14}$")
SYS_EVENT = "sys_event"
SYS_EVENT_INDEX = "sys_event_index"
SYS_PHRASE = "sys_phrase"
SYS_PHRASE_INDEX = "sys_phrase_index"