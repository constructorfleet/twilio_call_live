"""Defines a structure mapping phrases to an event."""
from dataclasses import dataclass, field
import re
from typing import Any, TypedDict
from homeassistant.const import CONF_EVENT
from custom_components.twilio_call_live.const import CONF_PHRASES, SYS_EVENT_INDEX, SYS_PHRASE
from custom_components.twilio_call_live.const import SYS_EVENT

TEXT_REPLACE_PATTERN = re.compile(r"[^a-zA-Z0-9 -]")


@dataclass()
class EventPhrases():
    """Maps phrases to an event."""

    event: str
    phrases: list[re.Pattern]

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "EventPhrases":
        """Create an EventPhrases from the config dict."""
        return cls(
            event=config["event"],
            phrases=[re.compile(phrase, re.IGNORECASE) for phrase in config["phrases"]],
        )

    def is_match(self, text: str) -> bool:
        """Determine if any of the phrases match the text."""
        clean_text = re.sub(TEXT_REPLACE_PATTERN, "", text)
        for phrase in self.phrases:
            if phrase.search(clean_text):
                return True
        return False

    def add_phrase(self, phrase: str) -> "EventPhrases":
        """Add a phrase to the event."""
        self.phrases.append(re.compile(phrase, re.IGNORECASE))
        return self

    def set_phrase(self, idx: int, phrase: str) -> "EventPhrases":
        """Set a phrase."""
        self.phrases[idx] = re.compile(phrase, re.IGNORECASE)
        return self

    def remove_phrase(self, phrase_or_index: int | str) -> "EventPhrases":
        """Reomve a phrase from the event."""
        if isinstance(phrase_or_index, int):
            self.phrases.remove(self.phrases[phrase_or_index])
        else:
            self.phrases = [
                phrase for phrase in self.phrases
                if phrase.pattern != phrase_or_index
            ]
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return dict of this structure."""
        return {
            CONF_EVENT: self.event,
            CONF_PHRASES: [phrase.pattern if isinstance(phrase, re.Pattern) else phrase for phrase in self.phrases]
        }



class EventPhrasesList(list[EventPhrases]):
    """Stores EventPhrases elements.."""

    def __init__(self, event_phrases: list[EventPhrases | dict[str, Any]]) -> None:
        """Initialize a new instance."""
        super().__init__([
            EventPhrases.from_config(event_phrase)
            if isinstance(event_phrase, dict)
            else event_phrase
            for event_phrase in event_phrases
        ])

    def get(self, text: str) -> str | None:
        """Returns the event for the given text."""
        for event_phrase in self:
            if event_phrase.is_match(text):
                return event_phrase.event
        return None


@dataclass
class SystemValues:
    event: str | None = field(default=None)
    event_index: int | None = field(default=None)
    phrase: str | None = field(default=None)
    phrase_index: int | None = field(default=None)
    user_input: dict[str, Any] | None = field(default=None)

    def to_dict(self) -> dict[str, Any] | None:
        """Convert to dictionary."""
        if self.event is None and self.event_index is None and self.phrase is None and self.phrase_index is None and self.user_input is None:
            return None
        return {
            SYS_EVENT: self.event,
            SYS_EVENT_INDEX: self.event_index,
            SYS_PHRASE: self.phrase,
            SYS_EVENT_INDEX: self.phrase_index,
            **(self.user_input or {})
        }