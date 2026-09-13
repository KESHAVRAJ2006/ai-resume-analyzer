"""Normalise raw resume text for matching.

The hard part is that resume vocabulary is full of punctuation that carries
meaning: c++, c#, .net, node.js, ci/cd. A naive "strip all punctuation" turns
c++ into c and .net into net, which destroys the very skills we want to find.

Strategy: find those tokens FIRST, swap each one for an alphanumeric
placeholder that punctuation stripping cannot damage, strip everything else,
then swap the real tokens back in.

PRIVACY: emails, phone numbers and profile URLs are redacted here, before any
analysis runs, so identity details never reach the matching layer.
"""

import re
import unicodedata

# Placeholders must be pure letters+digits so the punctuation stripper leaves
# them alone. "zqx" is a trigram that does not occur in English or tech words.
_PLACEHOLDER_PREFIX = "zqx"
_PLACEHOLDER_SUFFIX = "zqx"

# Ordered most-specific-first; the alternation below tries them left to right.
# The lookarounds stop "c++" matching inside "abc++" and ".js" inside ".jsx".
_PRESERVED_PATTERNS: tuple[str, ...] = (
    r"(?<![a-z0-9])c\+\+",                 # c++
    r"(?<![a-z0-9])c#",                    # c#
    r"(?<![a-z0-9])f#",                    # f#
    r"(?<![a-z0-9])ci\s*/\s*cd",           # ci/cd, ci / cd
    r"[a-z0-9]*\.net(?![a-z0-9])",         # .net, asp.net, vb.net
    r"[a-z0-9]*\.js(?![a-z0-9])",          # node.js, vue.js, next.js
)
_PRESERVED_RE = re.compile("|".join(f"(?:{p})" for p in _PRESERVED_PATTERNS))

# Characters PDF exporters emit that mean nothing to us; mapped to plain ASCII.
_SYMBOL_MAP = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-",   # en dash, em dash, minus
    " ": " ", "​": " ", "﻿": " ",   # nbsp, zero-width, BOM
    "•": " ", "●": " ", "▪": " ",   # bullet glyphs
    "◦": " ", "·": " ", "‣": " ",
}

_EMAIL_RE = re.compile(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", re.IGNORECASE)
_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_PROFILE_RE = re.compile(r"\b(?:linkedin|github|gitlab|behance)\.com/\S*", re.IGNORECASE)
# Candidate phone runs; the callback below only redacts those with >= 10 digits,
# so a date range like "2021 - 2023" is never mistaken for a phone number.
_PHONE_CANDIDATE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
_MIN_PHONE_DIGITS = 10


def clean_text(raw: str) -> str:
    """Take raw resume text, return lowercase single-spaced text for matching.

    Preserves c++, c#, .net, node.js and ci/cd; redacts contact details.
    Line breaks are removed, so run section_splitter BEFORE this function.
    """
    if not raw or not raw.strip():
        return ""

    text = unicodedata.normalize("NFKC", raw)  # folds ligatures like "ﬁ" -> "fi"
    text = _replace_symbols(text)
    text = _join_hyphenated_linebreaks(text)
    text = redact_contact_info(text)
    text = text.lower()

    text, restore_map = _protect_tokens(text)
    text = _strip_punctuation(text)
    text = _restore_tokens(text, restore_map)

    return _collapse_whitespace(text)


def clean_preserving_lines(raw: str) -> str:
    """Take raw text, return it lightly normalised but WITH line breaks intact.

    Used by section_splitter, which needs lines to spot headings.
    """
    if not raw:
        return ""
    text = unicodedata.normalize("NFKC", raw)
    text = _replace_symbols(text)
    text = _join_hyphenated_linebreaks(text)
    # Trim each line and drop runs of blank lines, but keep the line structure.
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines)


def redact_contact_info(text: str) -> str:
    """Take text, return it with emails, URLs and phone numbers replaced by a space."""
    text = _EMAIL_RE.sub(" ", text)
    text = _PROFILE_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)

    def _maybe_phone(match: re.Match[str]) -> str:
        digits = sum(character.isdigit() for character in match.group())
        return " " if digits >= _MIN_PHONE_DIGITS else match.group()

    return _PHONE_CANDIDATE_RE.sub(_maybe_phone, text)


def _replace_symbols(text: str) -> str:
    """Take text, return it with typographic symbols folded to plain ASCII."""
    for source, target in _SYMBOL_MAP.items():
        text = text.replace(source, target)
    return text


def _join_hyphenated_linebreaks(text: str) -> str:
    """Take text, return it with words split across lines rejoined.

    PDF exporters break "experience" as "experi-\nence"; without this the word
    is never matched.
    """
    return re.sub(r"(\w)-[ \t]*\n[ \t]*(\w)", r"\1\2", text)


def _protect_tokens(text: str) -> tuple[str, dict[str, str]]:
    """Take lowercased text, return it with punctuated skills swapped for
    placeholders, plus the map needed to restore them."""
    restore_map: dict[str, str] = {}
    token_to_placeholder: dict[str, str] = {}

    def _swap(match: re.Match[str]) -> str:
        token = match.group()
        # Normalise "ci / cd" to "ci/cd" so both spellings restore identically.
        normalised = re.sub(r"\s+", "", token) if "/" in token else token
        if normalised not in token_to_placeholder:
            placeholder = f"{_PLACEHOLDER_PREFIX}{len(token_to_placeholder)}{_PLACEHOLDER_SUFFIX}"
            token_to_placeholder[normalised] = placeholder
            restore_map[placeholder] = normalised
        return token_to_placeholder[normalised]

    return _PRESERVED_RE.sub(_swap, text), restore_map


def _strip_punctuation(text: str) -> str:
    """Take text, return it with every non-alphanumeric run turned into one space."""
    return re.sub(r"[^a-z0-9]+", " ", text)


def _restore_tokens(text: str, restore_map: dict[str, str]) -> str:
    """Take placeholder text and the restore map, return the real tokens back."""
    for placeholder, token in restore_map.items():
        text = text.replace(placeholder, token)
    return text


def _collapse_whitespace(text: str) -> str:
    """Take text, return it with runs of whitespace collapsed and ends trimmed."""
    return re.sub(r"\s+", " ", text).strip()
