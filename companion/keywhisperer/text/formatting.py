"""Rule-based text formatting (port of frontend/src/utils/smartFormatting.ts).

Pure functions, stdlib only. Differences from the TS version, on purpose:
- Single digits ("one".."nine") stay words unless part of a larger number, so
  "one of the" and "I have two cats" are not mangled. "ten".."nineteen",
  tens, compounds ("twenty five") and hundreds are converted.
- The very first letter of an utterance is NOT capitalized here; `join` does
  that, because it knows what was typed before.
"""

from __future__ import annotations

import re

_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_DIGIT_WORDS = "one|two|three|four|five|six|seven|eight|nine"
_TENS_WORDS = "|".join(_TENS)
_TEEN_WORDS = (
    "ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen"
)

# "two hundred [and] [twenty [five] | fifteen | five]"
_HUNDREDS_RE = re.compile(
    rf"\b({_DIGIT_WORDS})\s+hundred"
    rf"(?:\s+(?:and\s+)?(?:({_TENS_WORDS})(?:[-\s]+({_DIGIT_WORDS}))?|({_TEEN_WORDS}|{_DIGIT_WORDS})))?\b",
    re.IGNORECASE,
)
# "twenty five" / "twenty-five"
_COMPOUND_RE = re.compile(rf"\b({_TENS_WORDS})[-\s]+({_DIGIT_WORDS})\b", re.IGNORECASE)
_TENS_RE = re.compile(rf"\b({_TENS_WORDS})\b", re.IGNORECASE)
_TEENS_RE = re.compile(rf"\b({_TEEN_WORDS})\b", re.IGNORECASE)


def _hundreds(m: re.Match[str]) -> str:
    total = _ONES[m.group(1).lower()] * 100
    if m.group(2):
        total += _TENS[m.group(2).lower()]
        if m.group(3):
            total += _ONES[m.group(3).lower()]
    elif m.group(4):
        total += _ONES[m.group(4).lower()]
    return str(total)


def convert_spoken_numbers(text: str) -> str:
    """'twenty five' -> '25', 'two hundred and five' -> '205', 'fifteen' -> '15'."""
    text = _HUNDREDS_RE.sub(_hundreds, text)
    text = _COMPOUND_RE.sub(
        lambda m: str(_TENS[m.group(1).lower()] + _ONES[m.group(2).lower()]), text
    )
    text = _TENS_RE.sub(lambda m: str(_TENS[m.group(1).lower()]), text)
    text = _TEENS_RE.sub(lambda m: str(_ONES[m.group(1).lower()]), text)
    return text


def capitalize_sentences(text: str) -> str:
    """Capitalize the first letter after '. ', '! ' or '? ' (not the first char)."""
    return re.sub(
        r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text
    )


def apply_smart_quotes(text: str) -> str:
    """Straight quotes -> curly. Single quotes only when they wrap a phrase,
    so apostrophes in "don't" are left alone."""
    text = re.sub(r'"([^"]*)"', "“\\1”", text)
    text = re.sub(r"(?<!\w)'([^']+?)'(?!\w)", "‘\\1’", text)
    return text


_FILLER_RE = re.compile(
    r"(?<![\w'-])(?:um+|uh+|erm+|uhm+)(?![\w'-])[,]?\s*", re.IGNORECASE
)


def remove_fillers(text: str) -> str:
    """Drop standalone um/uh/erm (with their trailing comma). 'uh-huh' is kept."""
    out = _FILLER_RE.sub("", text)
    out = re.sub(r"\s+([.,!?;:])", r"\1", out)  # "yes um." -> "yes."
    out = re.sub(r"^[,;\s]+", "", out)  # "Um, hello" -> "hello"
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def format_text(
    text: str,
    *,
    auto_capitalize: bool = True,
    number_formatting: bool = True,
    smart_quotes: bool = False,
    remove_fillers_: bool = True,
) -> str:
    """Apply the enabled rules to one utterance (no joining)."""
    result = text.strip()
    if remove_fillers_:
        result = remove_fillers(result)
    if number_formatting:
        result = convert_spoken_numbers(result)
    if auto_capitalize:
        result = capitalize_sentences(result)
    if smart_quotes:
        result = apply_smart_quotes(result)
    return result


def join(previous_text: str, new_text: str, capitalize: bool = True) -> str:
    """Prepare `new_text` to be typed after `previous_text`.

    Adds a leading space when needed, and capitalizes the first letter when
    starting fresh or after . ! ? or a newline. Never lowercases.
    """
    new_text = new_text.strip()
    if not new_text:
        return ""
    starts_sentence = not previous_text or previous_text.rstrip(" \t").endswith(
        (".", "!", "?", "\n")
    )
    if capitalize and starts_sentence:
        new_text = new_text[0].upper() + new_text[1:]
    if previous_text and not previous_text[-1].isspace():
        new_text = " " + new_text
    return new_text
