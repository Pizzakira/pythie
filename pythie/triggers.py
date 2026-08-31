"""Stage 0 -- deterministic triggers.

No model call. Zero cost, zero latency, and auditable: a regex can be checked,
a model's judgement cannot.

Purpose: mark candidate spans and give each a type. This is what lets degree 1
display a marker instantly, before any verdict exists.

Accepted limitation: triggers catch figures, not qualitative claims. "I voted
against that law" contains no number. Hence the split between the two degrees
of rendering:
  - DEGREE 1 -- driven by triggers: fast, numeric, necessarily partial
  - DEGREE 2 -- full semantic sweep: slow, exhaustive, more precise

Patterns are written unaccented and matched against a length-preserving
unaccented copy of the text: automatic subtitles and ASR routinely mangle
French accents, and index preservation lets us return the original span.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List

from .schema import Trigger, TriggerType

_ACCENTS = str.maketrans(
    "àáâäãåÀÁÂÄÃÅèéêëÈÉÊËìíîïÌÍÎÏòóôöõÒÓÔÖÕùúûüÙÚÛÜçÇñÑÿŸ",
    "aaaaaaAAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUcCnNyY",
)


def flatten(text: str) -> str:
    """Strip accents WITHOUT changing length, so indices stay valid."""
    return unicodedata.normalize("NFC", text).translate(_ACCENTS)


# Order is priority: the first pattern to match a span wins.
# "3 %" is a PERCENTAGE, not a NUMBER.
PATTERNS: List[tuple[TriggerType, re.Pattern[str]]] = [
    (
        TriggerType.PERCENTAGE,
        # No \b after the alternation: "%" is already a non-word character, so
        # a trailing \b fails at end of sentence ("... de 2,3 %.").
        re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:%|pour\s?cent|points?\s+de\s+pourcentage)", re.I),
    ),
    (
        TriggerType.AMOUNT,
        re.compile(
            r"\b\d+(?:[.,\s ]\d+)*\s*"
            r"(?:milliards?|millions?|milliers?|Md|M€|K€)?\s*"
            r"(?:d'euros|euros|€|dollars|\$)\b",
            re.I,
        ),
    ),
    (
        TriggerType.DATE_OR_PERIOD,
        re.compile(
            r"\b(?:depuis|en|des|avant|apres|entre)\s+(?:19|20)\d{2}\b"
            r"|\b(?:19|20)\d{2}\b"
            r"|\b(?:ces|les|en)\s+\w+\s+(?:dernieres?|derniers?)\s+(?:annees?|mois)\b"
            r"|\bdepuis\s+\w+\s+(?:ans?|annees?|mois)\b",
            re.I,
        ),
    ),
    (
        TriggerType.SUPERLATIVE,
        re.compile(
            r"\b(?:le|la|les)\s+(?:plus|moins)\s+\w+"
            r"|\bjamais\s+(?:vu|atteint|connu)\b"
            r"|\brecord\b|\bhistorique(?:ment)?\b|\bau\s+plus\s+(?:bas|haut)\b"
            r"|\b(?:premier|premiere|dernier|derniere)\s+(?:pays|region|au\s+monde|d'Europe)\b",
            re.I,
        ),
    ),
    (
        TriggerType.COMPARATIVE,
        re.compile(
            r"\b(?:deux|trois|quatre|cinq|dix)\s+fois\s+(?:plus|moins)\b"
            r"|\b(?:plus|moins)\s+(?:eleve|faible|important|nombreux)\w*\s+qu"
            r"|\bpar\s+rapport\s+a\b|\bcontre\s+seulement\b|\ben\s+comparaison\b",
            re.I,
        ),
    ),
    (
        TriggerType.VAGUE_QUANTIFIER,
        re.compile(
            r"\b(?:la\s+(?:plupart|majorite)|une\s+minorite|des\s+milliers|"
            r"des\s+millions|enormement|la\s+quasi-totalite|l'immense\s+majorite|"
            r"beaucoup\s+(?:plus|moins)|explose|effondre|massivement)\b",
            re.I,
        ),
    ),
    (
        TriggerType.CAUSALITY,
        re.compile(
            r"\b(?:grace\s+a|a\s+cause\s+de|en\s+raison\s+de|c'est\s+pourquoi|"
            r"cela\s+a\s+(?:permis|provoque|entraine)|responsable\s+de|"
            r"a\s+conduit\s+a|du\s+fait\s+de)\b",
            re.I,
        ),
    ),
    (
        TriggerType.PLEDGE,
        re.compile(
            r"\b(?:je\s+(?:ferai|creerai|supprimerai|augmenterai|baisserai|"
            r"mettrai|proposerai|vais)|nous\s+(?:allons|ferons|creerons)|"
            r"mon\s+(?:projet|programme|objectif)|je\s+m'engage|"
            r"des\s+(?:mon|le\s+premier)\s+\w+)\b",
            re.I,
        ),
    ),
    (
        TriggerType.ATTRIBUTION,
        re.compile(
            r"\b(?:vous\s+avez\s+(?:dit|vote|promis|declare)|"
            r"il\s+a\s+(?:dit|vote|promis)|selon\s+(?:vous|lui|elle)|"
            r"votre\s+(?:bilan|gouvernement|majorite))\b",
            re.I,
        ),
    ),
    (
        TriggerType.NUMBER,
        re.compile(
            r"\b\d+(?:[.,\s ]\d+)*\s*"
            r"(?:milliards?|millions?|milliers?|places?|emplois?|logements?|"
            r"postes?|lits?|classes?|policiers?|infirmiers?|personnes?|habitants?)\b",
            re.I,
        ),
    ),
]


def detect(text: str) -> List[Trigger]:
    """Find every trigger in a text, without overlap."""
    found: List[Trigger] = []
    taken: List[tuple[int, int]] = []
    flat = flatten(text)  # same length, so indices apply to both

    for trigger_type, pattern in PATTERNS:
        for m in pattern.finditer(flat):
            start, end = m.span()
            if any(start < t_end and end > t_start for t_start, t_end in taken):
                continue
            taken.append((start, end))
            found.append(
                Trigger(
                    type=trigger_type,
                    text=text[start:end].strip(),  # original, accented span
                    start=start,
                    end=end,
                )
            )

    return sorted(found, key=lambda t: t.start)


# Types that, on their own, do NOT justify an expensive verification.
# A PLEDGE leaves the truth scale by construction: it is routed to the coherence
# axis instead. A VAGUE_QUANTIFIER almost always resolves to TOO_VAGUE.
NO_VERIFICATION = {TriggerType.PLEDGE, TriggerType.VAGUE_QUANTIFIER}


def deserves_verification(triggers: List[Trigger]) -> bool:
    """Cheap filter before stage 1, avoiding a model call when the trigger type
    is already decisive."""
    if not triggers:
        return False
    return bool({t.type for t in triggers} - NO_VERIFICATION)


def density(text: str, duration_minutes: float) -> Dict:
    """Operational metric: triggers per minute.

    First number to look at on a proof of concept -- it tells you whether the
    format has anything checkable at all. A manifesto debate is saturated with
    PLEDGE; a record-based debate is dense in NUMBER and DATE_OR_PERIOD.
    """
    found = detect(text)
    by_type: Dict[str, int] = {}
    for t in found:
        by_type[t.type.value] = by_type.get(t.type.value, 0) + 1
    return {
        "total": len(found),
        "per_minute": round(len(found) / duration_minutes, 2) if duration_minutes else 0.0,
        "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
    }
