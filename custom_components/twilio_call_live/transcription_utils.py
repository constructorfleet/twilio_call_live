"""Transcription merging tool."""

from datetime import datetime, UTC, timedelta
import re
from typing import Callable
import jellyfish

from .config import EventPhrases, EventPhrasesList


class TranscriptionMerger:
    """Tool for merging partial transcriptions."""

    def __init__(
        self,
        callback: Callable[[str], None],
        flush_interval: timedelta = timedelta(seconds=1),
        threshold: float = 0.5,
    ):
        """Initialize transcription merger."""
        self.segments: list[str] = []
        self.last_time = datetime.now(UTC)
        self.flush_interval = flush_interval
        self.callback = callback
        self.threshold = threshold

    def add_segment(self, segment: str) -> None:
        """Add segment to the list."""
        current_time = datetime.now(UTC)
        self.segments.append(segment)

        # Flush buffer if flush_interval has passed
        if current_time - self.last_time < self.flush_interval:
            return

        self.flush_buffer()

    def flush_buffer(self) -> None:
        """Flush buffer."""
        self.last_time = datetime.now(UTC)
        if not self.segments:
            return
        segments = self.segments
        self.segments = []
        merged_segments = self.merge_segments(segments)
        self.callback(merged_segments)

    def merge_segments(self, segments: list[str]) -> str:
        """Merge a list of transcript segments."""
        if not segments:
            return ""

        merged_text = segments[0]
        for segment in segments[1:]:
            merged_text = self.merge_two_segments(merged_text, segment)
        return merged_text

    def merge_two_segments(self, seg1: str, seg2: str) -> str:
        """Merge two transcript segments based on similarity."""
        similarity = jellyfish.jaro_winkler_similarity(seg1, seg2)
        if similarity > self.threshold:
            overlap_index = seg2.find(seg1.split()[-1])
            if overlap_index != -1:
                return seg1 + seg2[overlap_index + len(seg1.split()[-1]) :]
        return seg1 + " " + seg2


class PhraseMatcher:
    """Tool for matching phrases."""

    def __init__(self, event_phrases: EventPhrasesList, threshold: float = 0.8) -> None:
        self.event_phrases = event_phrases
        self.threshold = threshold

    def phrase_match_event(self, transcript: str) -> EventPhrases | None:
        """Get the event to fire if phrase and transcript match."""
        for event in self.event_phrases:
            for phrase in event.phrases:
                if self.are_similar(transcript, phrase):
                    return event
        return None

    def are_similar(self, transcript: str, phrase: str | re.Pattern) -> bool:
        """Check if two strings are similar."""
        if isinstance(phrase, re.Pattern):
            return phrase.search(transcript) is not None

        similarity = jellyfish.jaro_winkler_similarity(transcript, phrase)
        return similarity > self.threshold
