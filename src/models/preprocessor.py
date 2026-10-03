"""Text preprocessing and multilingual normalization for support tickets."""

import unicodedata
from typing import Optional


class TicketPreprocessor:
    """Preprocesses and formats incoming tickets for model feature extraction.

    Preserves UTF-8 Unicode combining characters (essential for Sinhala and Tamil),
    cleans whitespace, and merges channel and subject context with body text.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize Unicode to NFC form to preserve Sinhala/Tamil combining characters

        while standardizing representations.
        """
        if not text:
            return ""
        # Unicode NFC normalization preserves Sinhala (U+0D80..U+0DFF) and Tamil (U+0B80..U+0BFF)
        normalized = unicodedata.normalize("NFC", text)
        return normalized.strip()

    @classmethod
    def format_ticket_input(
        cls,
        channel: str,
        subject: Optional[str],
        text: str
    ) -> str:
        """Combine channel, subject, and text into a structured input string.

        Format:
        Channel: <channel> | Subject: <subject> | Text: <normalized_text>
        """
        norm_channel = channel.strip().lower() if channel else "chat"
        norm_subject = cls.normalize_text(subject) if subject else ""
        norm_text = cls.normalize_text(text)

        parts = [f"channel: {norm_channel}"]
        if norm_subject:
            parts.append(f"subject: {norm_subject}")
        parts.append(f"text: {norm_text}")

        return " | ".join(parts)
