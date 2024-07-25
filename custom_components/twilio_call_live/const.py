"""Constants for the twilio_call_live integration."""

import re

DOMAIN = "twilio_call_live"

ATTR_PROCESS_LIVE = "process_live"
ATTR_HANGUP_AFTER = "hangup_after"

CONF_FROM_NUMBER = "from_number"
CONF_PHRASE_EVENTS = "phrase_events"
CONF_PHRASE = "phrase"
CONF_PHRASES = "phrases"
CONF_ACTION = "action"

FROM_NUMBER_REPLACER_REGEX = r"[^0-9\+]"
FROM_NUMBER_REPLACER = re.compile(FROM_NUMBER_REPLACER_REGEX)
FROM_NUMBER_REGEX = r"^\+?[1-9]\d{1,14}$"
FROM_NUMBER_PATTERN = re.compile(FROM_NUMBER_REGEX)

SYS_EVENT = "sys_event"
SYS_EVENT_INDEX = "sys_event_index"
SYS_PHRASE = "sys_phrase"
SYS_PHRASE_INDEX = "sys_phrase_index"

ISSUE_TYPE_YAML_DETECTED = "issue_yaml_detected"
