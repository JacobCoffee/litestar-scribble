"""Content moderation for CanvasClash - blocks hate speech while allowing curse words.

This module provides hate speech detection for chat messages and custom word submissions.
It blocks racist, homophobic, and other discriminatory terms while allowing general profanity.

The blocklist includes:
- Racial slurs and ethnic hate terms
- Homophobic and transphobic slurs
- Religious hate terms
- Ableist slurs used as hate speech
- Common l33t speak and character substitution variations
"""

from __future__ import annotations

import re

# Character substitutions for l33t speak detection
CHAR_SUBSTITUTIONS: dict[str, list[str]] = {
    "a": ["a", "4", "@", "^"],
    "b": ["b", "8", "6"],
    "c": ["c", "(", "<", "{"],
    "e": ["e", "3"],
    "g": ["g", "9", "6"],
    "h": ["h", "#"],
    "i": ["i", "1", "!", "|", "l"],
    "k": ["k", "|<"],
    "l": ["l", "1", "|", "i"],
    "o": ["o", "0"],
    "s": ["s", "5", "$"],
    "t": ["t", "7", "+"],
    "u": ["u", "v"],
    "x": ["x", "><"],
    "z": ["z", "2"],
}

# Hate speech terms - these are blocked
# Note: This list contains offensive terms for the purpose of filtering them.
# The terms are stored as patterns to match various spellings.
_HATE_TERMS: list[str] = [
    # Racial slurs (abbreviated/partial to avoid raw slurs in code)
    "n[i1!|l]gg[e3]r",
    "n[i1!|l]gg[a4@]",
    "n[i1!|l]g+[e3]r",
    "n[i1!|l]g+[a4@]",
    "ch[i1!|l]nk",
    "sp[i1!|l]c",
    "sp[i1!|l]ck",
    "w[e3]tb[a4@]ck",
    "b[e3][a4@]n[e3]r",
    "g[o0][o0]k",
    "k[i1!|l]k[e3]",
    "j[a4@]p",
    "r[a4@]gh[e3][a4@]d",
    "t[o0]w[e3]lh[e3][a4@]d",
    "c[a4@]m[e3]lj[o0]ck[e3]y",
    "p[a4@]k[i1!|l]",
    "c[o0][o0]n",
    "d[a4@]rk[i1!|l][e3]",
    "p[o0]rch\\s*m[o0]nk[e3]y",
    "j[i1!|l]g[a4@]b[o0][o0]",
    "cr[a4@]ck[e3]r",  # context-dependent but often hate speech
    # Homophobic slurs
    "f[a4@]gg?[o0]t",
    "f[a4@]g",
    "d[y]k[e3]",
    "h[o0]m[o0]",
    "qu[e3][e3]r",  # can be reclaimed, but block in gaming context
    "tr[a4@]nny",
    "tr[a4@]nn[i1!|l][e3]",
    "sh[e3]m[a4@]l[e3]",
    "h[e3]-?sh[e3]",
    "l[e3]sb[o0]",
    # Transphobic terms
    "tr[o0][o0]n",
    # Religious hate
    "k[a4@]ff[i1!|l]r",
    # Ableist slurs (when used as hate)
    "r[e3]t[a4@]rd",
    "t[a4@]rd",
    "sp[a4@]z",
    "sp[a4@]st[i1!|l]c",
    "m[o0]ng[o0]l[o0][i1!|l]d",
    "m[o0]ng",
    # Nazi/white supremacist terms
    "s[i1!|l][e3]g\\s*h[e3][i1!|l]l",
    "h[e3][i1!|l]l\\s*h[i1!|l]tl[e3]r",
    "wh[i1!|l]t[e3]\\s*p[o0]w[e3]r",
    "1488",
    "14\\s*88",
    "88",  # Nazi code - careful, can be false positive
]

# Compile regex patterns for efficiency
_HATE_PATTERNS: list[re.Pattern[str]] = [re.compile(pattern, re.IGNORECASE) for pattern in _HATE_TERMS]


def normalize_text(text: str) -> str:
    """Normalize text by removing spaces and special characters between letters.

    This helps catch attempts to evade filters by adding spaces or characters
    between letters (e.g., "n i g g e r" or "n.i.g.g.e.r").

    Args:
        text: The text to normalize.

    Returns:
        Normalized text with internal spaces/punctuation removed.
    """
    # Remove spaces, dots, dashes, underscores between characters
    normalized = re.sub(r"[\s._\-]+", "", text)
    return normalized.lower()


def contains_hate_speech(text: str) -> bool:
    """Check if text contains hate speech.

    Checks both the original text and a normalized version to catch
    evasion attempts like adding spaces or using l33t speak.

    Args:
        text: The text to check.

    Returns:
        True if hate speech is detected, False otherwise.
    """
    if not text:
        return False

    # Check original text
    text_lower = text.lower()
    if any(pattern.search(text_lower) for pattern in _HATE_PATTERNS):
        return True

    # Check normalized text (removes spaces/punctuation)
    normalized = normalize_text(text)
    return any(pattern.search(normalized) for pattern in _HATE_PATTERNS)


def filter_message(text: str) -> tuple[str, bool]:
    """Filter a chat message for hate speech.

    If hate speech is detected, replaces the message with a placeholder.
    Curse words are allowed and not filtered.

    Args:
        text: The message text to filter.

    Returns:
        Tuple of (filtered_text, was_blocked).
        If blocked, filtered_text will be a placeholder message.
    """
    if contains_hate_speech(text):
        return "[Message blocked - hate speech not allowed]", True
    return text, False


def validate_custom_word(word: str) -> tuple[bool, str | None]:
    """Validate a custom word submission.

    Checks if the word contains hate speech. Curse words are allowed.

    Args:
        word: The custom word to validate.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.
    """
    if not word or not word.strip():
        return False, "Word cannot be empty"

    if contains_hate_speech(word):
        return False, "Word contains prohibited content"

    return True, None


def validate_custom_words(words: list[str]) -> tuple[list[str], list[str]]:
    """Validate a list of custom words.

    Filters out words containing hate speech and returns both
    the valid words and any that were rejected.

    Args:
        words: List of custom words to validate.

    Returns:
        Tuple of (valid_words, rejected_words).
    """
    valid: list[str] = []
    rejected: list[str] = []

    for word in words:
        is_valid, _ = validate_custom_word(word)
        if is_valid:
            valid.append(word)
        else:
            rejected.append(word)

    return valid, rejected
