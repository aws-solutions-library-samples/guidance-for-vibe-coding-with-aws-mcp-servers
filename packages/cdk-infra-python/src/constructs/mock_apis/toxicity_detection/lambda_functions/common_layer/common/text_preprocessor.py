"""
Text preprocessing utilities for the Toxicity Detection Service.
Handles whitelisting of words that should be filtered out before toxicity analysis.
"""

import re


# Whitelist of words/phrases that should be excluded from toxicity checks
# Hotel/accommodation related terms that might trigger false positives
WHITELIST_WORDS = [
    # Multi-word phrases first (order matters for proper replacement)
    "double queen",
    "double king",
    "deluxe suite",
    "I want to",
    # Single words
    "room",
    "rooms",
    "bed",
    "beds",
    "guest",
    "guests",
]


def preprocess_text_for_toxicity(text: str) -> str:
    """
    Replace whitelisted words/phrases with [FILTERED] placeholder.

    This function processes text before sending to Amazon Comprehend for toxicity
    analysis, removing hospitality-related terms that might cause false positives.

    Args:
        text: The original text to process

    Returns:
        Text with whitelisted words replaced by [FILTERED] placeholder

    Example:
        Input: "I need a double queen bed room with view"
        Output: "I need a [FILTERED] [FILTERED] [FILTERED] with view"
    """
    if not text or not isinstance(text, str):
        return text

    processed_text = text

    # Process whitelist words/phrases (longer phrases first to avoid partial matches)
    for word_phrase in WHITELIST_WORDS:
        # Create regex pattern for case-insensitive whole word/phrase matching
        pattern = r"\b" + re.escape(word_phrase) + r"\b"

        # Replace with [FILTERED] placeholder (case-insensitive)
        processed_text = re.sub(pattern, "[FILTERED]", processed_text, flags=re.IGNORECASE)

    return processed_text


def get_whitelist_words() -> list[str]:
    """
    Get the current list of whitelisted words/phrases.

    Returns:
        List of whitelisted words and phrases
    """
    return WHITELIST_WORDS.copy()


def add_whitelist_word(word: str) -> None:
    """
    Add a new word/phrase to the whitelist.

    Note: This modifies the runtime whitelist but doesn't persist changes.
    For permanent changes, modify the WHITELIST_WORDS constant directly.

    Args:
        word: Word or phrase to add to the whitelist
    """
    if word and word.lower() not in [w.lower() for w in WHITELIST_WORDS]:
        WHITELIST_WORDS.append(word.lower())
        # Re-sort to ensure longer phrases come first
        WHITELIST_WORDS.sort(key=len, reverse=True)
