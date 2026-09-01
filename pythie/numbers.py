"""Reading the figures a debate actually contains.

Two stages need this and neither owns it: the agreement layer must decide
whether two transcriptions heard the SAME figure, and verification must measure
the gap between a stated value and a published one. Both questions reduce to
turning what was said into a number.

French, spoken, and transcribed by machines -- so all of these are the same
figure and must read as one:

    "3 460 milliards"   "3460 milliards"   "trois mille quatre cent soixante
                                            milliards"

The scale word is part of the quantity: "600" is a number, "600 millions" is an
amount, and treating the first as the second is how a verdict goes wrong on a
statement that was true.

Percentages are marked as such because they are not compared like other
quantities. An error of 1,7 point of GDP is a relative gap of 3,4 % -- under
the 5 % bar, therefore "exact", therefore roughly 50 billion euros called
correct (D-039). A percentage is compared in points, and the program can only
know that if the reader tells it which quantities are percentages.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple


# --- reading numbers a debate actually contains ----------------------------

SCALES = {
    "mille": 1e3, "milles": 1e3,
    "million": 1e6, "millions": 1e6,
    "milliard": 1e9, "milliards": 1e9,
    "billion": 1e12, "billions": 1e12,
}

UNITS = {
    "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11,
    "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16,
    "vingt": 20, "vingts": 20, "trente": 30, "quarante": 40, "cinquante": 50,
    "soixante": 60, "cent": 100, "cents": 100,
}

PERCENT_WORDS = ("%", "pour cent", "pourcent", "points de pib", "point de pib")

YEAR = re.compile(r"\b(19|20)\d{2}\b")

# "3 460", "45,3", "1 234,5" -- French writes thousands with a space (often
# non-breaking) and decimals with a comma.
DIGITS = re.compile(r"\d[\d\s  .]*(?:,\d+)?")


class Kind(str, Enum):
    PERCENT = "percent"
    MAGNITUDE = "magnitude"     # a plain number, possibly scaled
    YEAR = "year"


@dataclass(frozen=True)
class Quantity:
    """A figure as the program understands it, with the words that carried it."""

    kind: Kind
    value: float
    raw: str
    position: int               # word index in the normalised token list

    def matches(self, other: "Quantity") -> bool:
        if self.kind != other.kind:
            return False
        if self.value == other.value:
            return True
        # Two transcriptions writing the same figure differently -- "3 460
        # milliards" and "3460 milliards" -- normalise to the same float, so
        # anything left is a genuine difference. A hair of tolerance covers
        # float noise only, never a rounding difference: 57 and 57,3 are two
        # different things heard, which is exactly what we abstain on.
        return abs(self.value - other.value) <= 1e-9 * max(abs(self.value), 1.0)


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalise(text: str) -> str:
    """Lowercase, unaccented, punctuation to spaces -- except % and comma,
    which carry meaning inside a figure."""
    text = strip_accents(text.lower())
    text = text.replace(" ", " ").replace(" ", " ")
    text = re.sub(r"[^\w%,.\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _to_float(raw: str) -> Optional[float]:
    cleaned = raw.replace(" ", "").replace(" ", "").replace(" ", "")
    # A dot in French text is a thousands separator or a sentence end, never a
    # decimal point. The comma is the decimal separator.
    cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".")
    cleaned = cleaned.rstrip(".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _spelled_number(tokens: Sequence[str], index: int) -> Tuple[Optional[float], int]:
    """Read a French number written in words, starting at `index`.

    Handles what a debate actually says -- "quarante milliards", "quatre-vingts
    pour cent", "deux cent cinquante" -- and stops at the first word that is
    not part of a number. Returns (value, index after the number).
    """
    total = 0.0
    current = 0.0
    seen = False
    i = index

    while i < len(tokens):
        token = tokens[i]
        if token in UNITS:
            value = UNITS[token]
            if value == 100:
                current = (current or 1) * 100
            else:
                current += value
            seen = True
            i += 1
        elif token == "et" and seen and i + 1 < len(tokens) and tokens[i + 1] in UNITS:
            i += 1                       # "soixante et un"
        elif token in ("mille", "milles") and seen:
            total += (current or 1) * 1000
            current = 0.0
            i += 1
        else:
            break

    if not seen:
        return None, index
    return total + current, i


def quantities(text: str) -> List[Quantity]:
    """Every figure in a span, canonicalised.

    A figure is read together with what follows it, because the scale word is
    what makes it a quantity: "600" alone is a number, "600 millions" is an
    amount, and confusing the two is how a verdict goes wrong.
    """
    # `normalise` keeps dots and commas because they live inside figures. On a
    # WORD they are always punctuation -- and a scale word that keeps its full
    # stop is not found: "150 milliards." read as the bare number 150, off by a
    # factor of a billion. Digit tokens strip their own trailing punctuation
    # further down, where the difference between a decimal comma and a final
    # one still matters.
    tokens = [t if t[:1].isdigit() else t.rstrip(".,")
              for t in normalise(text).split()]
    found: List[Quantity] = []
    index = 0

    while index < len(tokens):
        token = tokens[index]
        value: Optional[float] = None
        consumed = index + 1

        digits = ""
        if re.match(r"^\d", token):
            match = DIGITS.match(token)
            # The comma and the dot are kept by `normalise` because they live
            # inside figures; when they END a token they are punctuation.
            # Without this strip, "en 2024," and "jusqu'a 2028." read as the
            # quantities 2024 and 2028 rather than as years, and the agreement
            # layer then demands that a witness repeat them.
            digits = match.group(0).rstrip(",. ") if match else ""
            value = _to_float(digits) if digits else None
            # "3 460 milliards" tokenises as three words: rejoin the digit runs
            # that a French thousands space split apart.
            while (value is not None and consumed < len(tokens)
                   and re.fullmatch(r"\d{3}", tokens[consumed])):
                value = float(f"{int(value)}{tokens[consumed]}")
                consumed += 1
        elif token in UNITS:
            value, consumed = _spelled_number(tokens, index)

        if value is None:
            index += 1
            continue

        raw_end = consumed
        kind = Kind.MAGNITUDE

        # scale word
        if consumed < len(tokens) and tokens[consumed] in SCALES:
            value *= SCALES[tokens[consumed]]
            raw_end = consumed + 1

        tail = " ".join(tokens[raw_end:raw_end + 3])
        scaled = raw_end > consumed
        if token.endswith("%"):
            kind = Kind.PERCENT
        elif tail.startswith(PERCENT_WORDS):
            kind = Kind.PERCENT
            # Keep the marker in `raw`: the figure is displayed back to a
            # reader, and "vingt" reads differently from "vingt pour cent".
            raw_end += 1 if tokens[raw_end] == "%" else 2
        elif 1900 <= value <= 2100 and re.fullmatch(r"(19|20)\d{2}", digits):
            kind = Kind.YEAR

        # A number written in WORDS only counts when a scale or a percent
        # follows it. Otherwise "un" the article becomes the figure 1, "et
        # une autre chose" becomes a quantity to corroborate, and the layer
        # spends its abstentions on French grammar. "quarante milliards" and
        # "vingt pour cent" are kept; a bare "deux" is not.
        if not re.match(r"^\d", token) and kind is Kind.MAGNITUDE and not scaled:
            index = max(raw_end, index + 1)
            continue

        found.append(
            Quantity(kind=kind, value=value,
                     raw=" ".join(tokens[index:raw_end]), position=index)
        )
        index = max(raw_end, index + 1)

    return found
